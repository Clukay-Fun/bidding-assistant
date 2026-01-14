"""
Agent 测试脚本
验证 Agent 自主循环是否正常工作
"""

import sys
from pathlib import Path

# 添加 backend 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# ============================================
# region 初始化工具
# ============================================

def init_tools():
    """初始化工具（必须在导入 Agent 前执行）"""
    from app.tools import tool_registry
    tool_registry.clear()
    from app.tools import database  # noqa: F401
    print(f"✅ 已注册 {len(tool_registry.list_names())} 个工具")

# endregion
# ============================================


# ============================================
# region 测试基础运行
# ============================================

def test_agent_basic():
    """测试 Agent 基础运行"""
    print("\n" + "=" * 50)
    print("🧪 测试 1: Agent 基础运行")
    print("=" * 50)
    
    from app.agent import Agent
    
    agent = Agent(max_steps=5)
    
    # 简单问题测试
    result = agent.run("你好，请介绍一下你自己")
    
    print(f"\n📋 执行轨迹:")
    print(result.get_trace())
    
    assert result.final_answer is not None, "应该有最终答案"
    print("\n✅ Agent 基础运行测试通过!")

# endregion
# ============================================


# ============================================
# region 测试工具调用
# ============================================

def test_agent_tool_call():
    """测试 Agent 工具调用"""
    print("\n" + "=" * 50)
    print("🧪 测试 2: Agent 工具调用")
    print("=" * 50)
    
    from app.agent import Agent
    
    agent = Agent(max_steps=5)
    
    # 需要调用工具的问题
    result = agent.run("查询所有业绩合同")
    
    print(f"\n📋 执行轨迹:")
    print(result.get_trace())
    
    # 检查是否调用了工具
    tool_calls = [s for s in result.steps if s.tool_name is not None]
    print(f"\n🔧 工具调用次数: {len(tool_calls)}")
    
    assert result.final_answer is not None, "应该有最终答案"
    print("\n✅ Agent 工具调用测试通过!")

# endregion
# ============================================


# ============================================
# region 测试复杂查询
# ============================================

def test_agent_complex_query():
    """测试 Agent 复杂查询"""
    print("\n" + "=" * 50)
    print("🧪 测试 3: Agent 复杂查询")
    print("=" * 50)
    
    from app.agent import Agent
    
    agent = Agent(max_steps=8)
    
    # 复杂业务问题
    result = agent.run("帮我查找包含'能源'关键词的业绩")
    
    print(f"\n📋 执行轨迹:")
    print(result.get_trace())
    
    print(f"\n📝 最终答案:")
    print(result.final_answer)
    
    assert result.final_answer is not None, "应该有最终答案"
    print("\n✅ Agent 复杂查询测试通过!")

# endregion
# ============================================


# ============================================
# region 测试流式输出
# ============================================

def test_agent_stream():
    """测试 Agent 流式输出"""
    print("\n" + "=" * 50)
    print("🧪 测试 4: Agent 流式输出")
    print("=" * 50)
    
    from app.agent import Agent
    
    agent = Agent(max_steps=5)
    
    print("\n📡 流式事件:")
    for event in agent.run_stream("查询所有律师"):
        event_type = event.get("event")
        event_data = event.get("data")
        print(f"   [{event_type}] {event_data}")
    
    print("\n✅ Agent 流式输出测试通过!")

# endregion
# ============================================


# ============================================
# region 主函数
# ============================================

def main():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("🚀 Agent 系统测试")
    print("=" * 50)
    
    try:
        # 初始化工具
        init_tools()
        
        # 运行测试
        test_agent_basic()
        test_agent_tool_call()
        test_agent_complex_query()
        test_agent_stream()
        
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