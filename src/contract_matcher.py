"""
业绩智能匹配模块
功能：根据招标要求，从数据库中筛选匹配的业绩合同
"""

from datetime import datetime, timedelta
from openai import OpenAI
import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    REASONING_MODEL,
    expand_keywords
)
from src.database import get_session, Contract
from src.utils import load_prompt, clean_json_response


# ============================================
# region 需求解析
# ============================================

def parse_requirement(requirement_text: str) -> dict:
    """解析业绩要求，提取筛选条件"""
    print("🤖 解析业绩要求...")
    
    client = OpenAI(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL
    )
    
    try:
        prompt_template = load_prompt("requirement_parse")
        prompt = prompt_template.replace("{requirement}", requirement_text)
        
        response = client.chat.completions.create(
            model=REASONING_MODEL,
            messages=[
                {"role": "system", "content": "你是招投标专家，请严格按JSON格式输出筛选条件。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        result_text = response.choices[0].message.content.strip()
        result_text = clean_json_response(result_text)
        
        conditions = json.loads(result_text)
        print(f"   ✅ 解析完成: {conditions}")
        return conditions
        
    except Exception as e:
        print(f"   ❌ 解析失败: {e}")
        return {}

# endregion
# ============================================


# ============================================
# region 数据库筛选
# ============================================

def search_contracts_by_conditions(conditions: dict) -> list:
    """根据条件从数据库筛选合同"""
    print("🔍 数据库筛选中...")
    
    session = get_session()
    
    try:
        query = session.query(Contract)
        
        # 1. 时间范围筛选
        if conditions.get("time_range"):
            years = conditions["time_range"]
            cutoff_date = datetime.now() - timedelta(days=years*365)
            cutoff_str = cutoff_date.strftime("%Y-%m-%d")
            query = query.filter(Contract.sign_date >= cutoff_str)
        
        # 2. 项目类型筛选
        if conditions.get("project_type"):
            query = query.filter(Contract.project_type == conditions["project_type"])
        
        # 3. 国企要求
        if conditions.get("state_owned_required"):
            query = query.filter(Contract.is_state_owned == True)
        
        # 4. 最低金额
        if conditions.get("min_amount"):
            query = query.filter(Contract.amount >= conditions["min_amount"])
        
        # 获取初步结果
        contracts = query.all()
        print(f"   📊 初步筛选: {len(contracts)} 条")
        
        # 5. 行业和关键词模糊匹配
        if conditions.get("industry") or conditions.get("keywords"):
            filtered = []
            
            # 扩展关键词
            original_keywords = conditions.get("keywords", [])
            industry = conditions.get("industry", "")
            
            if industry:
                original_keywords = [industry] + (original_keywords or [])
            
            expanded_keywords = expand_keywords(original_keywords)
            print(f"   🔍 扩展关键词: {expanded_keywords}")
            
            for c in contracts:
                text_to_search = " ".join([
                    c.party_a or '',
                    c.party_a_industry or '',
                    c.project_detail or '',
                    c.contract_name or '',
                    c.summary or ''
                ]).lower()
                
                matched = False
                matched_keywords = []
                
                for kw in expanded_keywords:
                    if kw.lower() in text_to_search:
                        matched = True
                        matched_keywords.append(kw)
                
                if matched:
                    filtered.append(c)
                    print(f"   ✅ 匹配: {c.contract_name} (关键词: {matched_keywords})")
            
            contracts = filtered
            print(f"   📊 关键词筛选后: {len(contracts)} 条")
        
        results = [c.to_dict() for c in contracts]
        return results
        
    finally:
        session.close()

# endregion
# ============================================


# ============================================
# region AI评估匹配度
# ============================================

def evaluate_matches(requirement: str, contracts: list) -> dict:
    """AI评估业绩匹配度"""
    print("🤖 AI评估匹配度...")
    
    if not contracts:
        return {"matches": [], "summary": "未找到符合条件的业绩"}
    
    # 准备合同摘要
    contracts_text = ""
    for i, c in enumerate(contracts, 1):
        contracts_text += f"""
【业绩{i}】
- ID: {c['id']}
- 合同名称: {c['contract_name']}
- 甲方: {c['party_a']}
- 甲方行业: {c['party_a_industry']}
- 是否国企: {'是' if c['is_state_owned'] else '否'}
- 合同金额: {c['amount']}万元
- 签订日期: {c['sign_date']}
- 项目类型: {c['project_type']}
- 项目详情: {c['project_detail'][:200] if c['project_detail'] else '无'}
"""
    
    client = OpenAI(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL
    )
    
    try:
        prompt_template = load_prompt("match_evaluate")
        prompt = prompt_template.replace("{requirement}", requirement).replace("{contracts}", contracts_text)
        
        response = client.chat.completions.create(
            model=REASONING_MODEL,
            messages=[
                {"role": "system", "content": "你是招投标专家，请严格评估业绩是否符合要求。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        result_text = response.choices[0].message.content.strip()
        result_text = clean_json_response(result_text)
        
        return json.loads(result_text)
        
    except Exception as e:
        print(f"   ❌ 评估失败: {e}")
        return {
            "matches": [
                {
                    "id": c["id"],
                    "contract_name": c["contract_name"],
                    "party_a": c["party_a"],
                    "match_score": 80,
                    "match_reason": "符合筛选条件",
                    "risk_points": "无"
                }
                for c in contracts
            ],
            "summary": f"共找到 {len(contracts)} 条符合条件的业绩"
        }

# endregion
# ============================================


# ============================================
# region 主匹配函数
# ============================================

def match_contracts(requirement: str) -> dict:
    """
    业绩智能匹配主函数
    """
    print("\n" + "="*50)
    print("🎯 业绩智能匹配")
    print("="*50)
    print(f"📋 业绩要求: {requirement[:100]}...")
    
    # 1. 解析要求
    conditions = parse_requirement(requirement)
    
    if not conditions:
        return {"error": "无法解析业绩要求"}
    
    # 2. 数据库筛选
    contracts = search_contracts_by_conditions(conditions)
    
    # 3. AI评估
    result = evaluate_matches(requirement, contracts)
    
    # 4. 输出结果
    print("\n" + "="*50)
    print("📊 匹配结果")
    print("="*50)
    
    if result.get("matches"):
        for m in result["matches"]:
            score = m.get("match_score", 0)
            icon = "✅" if score >= 70 else "⚠️" if score >= 50 else "❌"
            print(f"\n{icon} [{m.get('id')}] {m.get('contract_name')}")
            print(f"   甲方: {m.get('party_a')}")
            print(f"   匹配度: {score}分")
            print(f"   理由: {m.get('match_reason')}")
            if m.get("risk_points") and m.get("risk_points") != "无":
                print(f"   ⚠️ 风险点: {m.get('risk_points')}")
    
    print(f"\n📝 总结: {result.get('summary', '无')}")
    
    return result

# endregion
# ============================================


# ============================================
# region 交互式匹配
# ============================================

def interactive_match():
    """交互式业绩匹配"""
    print("\n" + "="*50)
    print("🎯 业绩智能匹配系统")
    print("="*50)
    print("输入招标文件中的业绩要求，系统将自动匹配")
    print("输入 'quit' 或 'q' 退出\n")
    
    while True:
        print("-"*50)
        requirement = input("📋 请输入业绩要求: ").strip()
        
        if requirement.lower() in ['quit', 'q', '退出']:
            print("👋 再见！")
            break
        
        if not requirement:
            continue
        
        match_contracts(requirement)

# endregion
# ============================================


if __name__ == "__main__":
    if len(sys.argv) > 1:
        requirement = " ".join(sys.argv[1:])
        match_contracts(requirement)
    else:
        interactive_match()
