"""
业绩智能匹配模块
功能：根据招标要求，从数据库中筛选匹配的业绩合同
"""

from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, timedelta
import json
import os

from database import get_session, Contract

# 加载环境变量
load_dotenv()

# ============================================
# region 配置
# ============================================

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
REASONING_MODEL = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"

# endregion
# ============================================


# ============================================
# region 需求解析
# ============================================

PARSE_REQUIREMENT_PROMPT = """你是一个招投标专家。请分析以下业绩要求，提取筛选条件。

## 业绩要求原文
{requirement}

## 请提取以下筛选条件（JSON格式）

1. **time_range**: 时间范围（年数，如"近五年"填5，"近三年"填3）
2. **min_count**: 最少业绩数量（如"至少1项"填1）
3. **industry**: 行业要求（如"能源类"、"医疗"、"金融"等，无要求填null）
4. **project_type**: 项目类型要求（"常法"/"诉讼"/"专项"，无要求填null）
5. **min_amount**: 最低合同金额（万元，无要求填null）
6. **state_owned_required**: 是否要求国企业绩（true/false）
7. **keywords**: 其他关键词列表（用于模糊匹配）

## 输出JSON（不要```标记）
{{
  "time_range": 5,
  "min_count": 1,
  "industry": "能源",
  "project_type": null,
  "min_amount": null,
  "state_owned_required": false,
  "keywords": ["燃气", "光伏", "电力", "储能"]
}}
"""


def parse_requirement(requirement_text: str) -> dict:
    """解析业绩要求，提取筛选条件"""
    print("🤖 解析业绩要求...")
    
    client = OpenAI(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL
    )
    
    try:
        response = client.chat.completions.create(
            model=REASONING_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你是招投标专家，请严格按JSON格式输出筛选条件。"
                },
                {
                    "role": "user",
                    "content": PARSE_REQUIREMENT_PROMPT.format(requirement=requirement_text)
                }
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # 清理JSON
        if "```" in result_text:
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.split("```")[0]
        
        if "{" in result_text:
            start = result_text.find("{")
            end = result_text.rfind("}") + 1
            result_text = result_text[start:end]
        
        conditions = json.loads(result_text.strip())
        print(f"   ✅ 解析完成: {conditions}")
        return conditions
        
    except Exception as e:
        print(f"   ❌ 解析失败: {e}")
        return {}

# endregion
# ============================================

# ============================================
# region 同义词扩展
# ============================================

# 行业同义词映射
INDUSTRY_SYNONYMS = {
    "能源": ["能源", "燃气", "天然气", "光伏", "电力", "储能", "分布式能源", "新能源", "清洁能源", "石油", "煤炭"],
    "燃气": ["燃气", "天然气", "液化气", "煤气"],
    "光伏": ["光伏", "太阳能", "新能源"],
    "电力": ["电力", "供电", "发电", "输电", "配电"],
    "金融": ["金融", "银行", "证券", "保险", "基金", "投资"],
    "医疗": ["医疗", "医院", "医药", "卫生", "健康"],
    "房地产": ["房地产", "地产", "房产", "置业", "物业"],
}


def expand_keywords(keywords: list) -> list:
    """扩展关键词（添加同义词）"""
    expanded = set(keywords) if keywords else set()
    
    for kw in keywords or []:
        # 查找同义词
        for category, synonyms in INDUSTRY_SYNONYMS.items():
            if kw in synonyms or kw == category:
                expanded.update(synonyms)
    
    return list(expanded)

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
            
            # 扩展关键词（添加同义词）
            original_keywords = conditions.get("keywords", [])
            industry = conditions.get("industry", "")
            
            # 把行业也加入关键词
            if industry:
                original_keywords = [industry] + (original_keywords or [])
            
            # 扩展同义词
            expanded_keywords = expand_keywords(original_keywords)
            print(f"   🔍 扩展关键词: {expanded_keywords}")
            
            for c in contracts:
                # 构建搜索文本
                text_to_search = " ".join([
                    c.party_a or '',
                    c.party_a_industry or '',
                    c.project_detail or '',
                    c.contract_name or '',
                    c.summary or ''
                ]).lower()
                
                # 检查是否匹配任一关键词
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
        
        # 转换为字典列表（返回所有符合条件的，不限数量）
        results = [c.to_dict() for c in contracts]
        return results
        
    finally:
        session.close()

# endregion
# ============================================


# ============================================
# region AI评估匹配度
# ============================================

EVALUATE_PROMPT = """你是招投标专家。请评估以下业绩是否符合招标要求。

## 招标业绩要求
{requirement}

## 候选业绩
{contracts}

## 请对每条业绩进行评估

输出JSON格式（不要```标记）：
{{
  "matches": [
    {{
      "id": 1,
      "contract_name": "合同名称",
      "party_a": "甲方",
      "match_score": 95,
      "match_reason": "符合能源类企业要求，时间在近五年内",
      "risk_points": "无"
    }}
  ],
  "summary": "共找到X条符合要求的业绩，建议选用..."
}}

## 评分标准
- 90-100: 完全符合
- 70-89: 基本符合
- 50-69: 部分符合
- 0-49: 不符合
"""


def evaluate_matches(requirement: str, contracts: list) -> dict:
    """AI评估业绩匹配度"""
    print("🤖 AI评估匹配度...")
    
    if not contracts:
        return {"matches": [], "summary": "未找到符合条件的业绩"}
    
    # 准备合同摘要（不限制数量）
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
        response = client.chat.completions.create(
            model=REASONING_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你是招投标专家，请对所有业绩进行评估，给出匹配度评分。"
                },
                {
                    "role": "user",
                    "content": EVALUATE_PROMPT.format(
                        requirement=requirement,
                        contracts=contracts_text
                    )
                }
            ],
            temperature=0.1,
            max_tokens=4000  # 增加token限制
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # 清理JSON
        if "{" in result_text:
            start = result_text.find("{")
            end = result_text.rfind("}") + 1
            result_text = result_text[start:end]
        
        return json.loads(result_text.strip())
        
    except Exception as e:
        print(f"   ❌ 评估失败: {e}")
        # 返回基础结果（不经过AI评估）
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
    
    参数:
        requirement: 招标文件中的业绩要求文本
    
    返回:
        匹配结果
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
    # 方式1: 交互式匹配
    # interactive_match()
    
    # 方式2: 直接测试
    test_requirement = """
    近五年内（从采购公告发布之日起倒推）响应人至少拥有1项能源类企业
    （燃气、光伏、分布式能源、电力、储能等行业）法律服务的业绩。
    """
    
    match_contracts(test_requirement)