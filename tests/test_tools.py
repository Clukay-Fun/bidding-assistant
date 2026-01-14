"""
工具系统测试脚本
验证 @tool 装饰器和注册中心是否正常工作
"""

import sys
from pathlib import Path

# 添加 backend 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# ============================================
# region 测试工具注册
# ============================================

def test_tool_registration():
    """测试工具注册功能"""
    print("\n" + "=" * 50)
    print("🧪 测试 1: 工具注册")
    print("=" * 50)
    
    # 导入注册中心
    from app.tools import tool_registry
    
    # 先清空（确保测试环境干净）
    tool_registry.clear()
    
    # 导入数据库工具（这会自动注册）
    from app.tools import database  # noqa: F401
    
    # 检查注册的工具
    tool_names = tool_registry.list_names()
    print(f"\n📋 已注册的工具: {tool_names}")
    
    assert len(tool_names) > 0, "应该至少有一个工具被注册"
    assert "search_performances" in tool_names, "search_performances 应该被注册"
    
    print("✅ 工具注册测试通过!")

# endregion
# ============================================


# ============================================
# region 测试工具信息
# ============================================

def test_tool_info():
    """测试工具信息获取"""
    print("\n" + "=" * 50)
    print("🧪 测试 2: 工具信息")
    print("=" * 50)
    
    from app.tools import tool_registry
    
    # 获取单个工具
    tool = tool_registry.get("search_performances")
    
    assert tool is not None, "应该能获取到 search_performances 工具"
    
    print(f"\n📦 工具名称: {tool.name}")
    print(f"📝 工具描述: {tool.description}")
    print(f"📂 工具分类: {tool.definition.category}")
    print(f"📋 参数列表:")
    for param in tool.definition.parameters:
        req_mark = " (必填)" if param.required else ""
        print(f"   - {param.name}: {param.type}{req_mark} - {param.description}")
    
    print("\n✅ 工具信息测试通过!")

# endregion
# ============================================


# ============================================
# region 测试工具提示词生成
# ============================================

def test_tools_prompt():
    """测试工具提示词生成"""
    print("\n" + "=" * 50)
    print("🧪 测试 3: 工具提示词生成")
    print("=" * 50)
    
    from app.tools import tool_registry
    
    prompt = tool_registry.get_tools_prompt()
    
    print(f"\n📄 生成的提示词:\n")
    print(prompt)
    
    assert "search_performances" in prompt, "提示词应包含 search_performances"
    assert "database" in prompt, "提示词应包含 database 分类"
    
    print("\n✅ 工具提示词测试通过!")

# endregion
# ============================================


# ============================================
# region 测试工具调用
# ============================================

def test_tool_call():
    """测试工具调用"""
    print("\n" + "=" * 50)
    print("🧪 测试 4: 工具调用")
    print("=" * 50)
    
    from app.tools import tool_registry
    
    # 调用 search_performances（无参数，应该返回所有业绩）
    print("\n🔍 调用 search_performances()...")
    result = tool_registry.call("search_performances")
    
    print(f"   成功: {result.success}")
    
    if result.success:
        print(f"   找到 {result.result['count']} 条业绩")
        
        # 显示前 2 条
        for i, perf in enumerate(result.result['performances'][:2], 1):
            print(f"\n   [{i}] {perf.get('file_name', 'N/A')}")
            print(f"       甲方: {perf.get('party_a', 'N/A')}")
            print(f"       金额: {perf.get('amount', 'N/A')} 万元")
    else:
        print(f"   错误: {result.error}")
    
    assert result.success, "工具调用应该成功"
    
    print("\n✅ 工具调用测试通过!")

# endregion
# ============================================


# ============================================
# region 测试带参数的工具调用
# ============================================

def test_tool_call_with_params():
    """测试带参数的工具调用"""
    print("\n" + "=" * 50)
    print("🧪 测试 5: 带参数的工具调用")
    print("=" * 50)
    
    from app.tools import tool_registry
    
    # 调用 search_performances（带关键词）
    print("\n🔍 调用 search_performances(keyword='能源')...")
    result = tool_registry.call("search_performances", keyword="能源")
    
    print(f"   成功: {result.success}")
    
    if result.success:
        print(f"   找到 {result.result['count']} 条匹配业绩")
    else:
        print(f"   错误: {result.error}")
    
    print("\n✅ 带参数工具调用测试通过!")

# endregion
# ============================================


# ============================================
# region 测试不存在的工具
# ============================================

def test_nonexistent_tool():
    """测试调用不存在的工具"""
    print("\n" + "=" * 50)
    print("🧪 测试 6: 调用不存在的工具")
    print("=" * 50)
    
    from app.tools import tool_registry
    
    result = tool_registry.call("nonexistent_tool")
    
    print(f"\n   成功: {result.success}")
    print(f"   错误信息: {result.error}")
    
    assert not result.success, "调用不存在的工具应该失败"
    assert "不存在" in result.error, "错误信息应该提示工具不存在"
    
    print("\n✅ 不存在工具测试通过!")

# endregion
# ============================================


# ============================================
# region 测试工具 JSON 导出
# ============================================

def test_tools_json():
    """测试工具 JSON 导出"""
    print("\n" + "=" * 50)
    print("🧪 测试 7: 工具 JSON 导出")
    print("=" * 50)
    
    from app.tools import tool_registry
    import json
    
    tools_json = tool_registry.get_tools_json()
    
    print(f"\n📄 JSON 格式工具列表:\n")
    print(json.dumps(tools_json[:2], indent=2, ensure_ascii=False))  # 只显示前2个
    
    assert len(tools_json) > 0, "应该有工具导出"
    
    print("\n✅ 工具 JSON 导出测试通过!")

# endregion
# ============================================


# ============================================
# region 主函数
# ============================================

def main():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("🚀 工具系统测试")
    print("=" * 50)
    
    try:
        test_tool_registration()
        test_tool_info()
        test_tools_prompt()
        test_tool_call()
        test_tool_call_with_params()
        test_nonexistent_tool()
        test_tools_json()
        
        print("\n" + "=" * 50)
        print("🎉 所有测试通过!")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

# endregion
# ============================================