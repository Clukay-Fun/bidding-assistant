"""
Agent 提示词管理
加载和格式化提示词模板
"""

from pathlib import Path
from typing import List

from app.tools import tool_registry
from app.agent.state import AgentStep


# ============================================
# region 路径配置
# ============================================

# 提示词目录（项目根目录下的 prompts 文件夹）
PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts"

# endregion
# ============================================


# ============================================
# region 提示词加载
# ============================================

def load_prompt(name: str) -> str:
    """
    加载提示词模板
    
    参数:
        name: 提示词文件名（不含 .md 扩展名）
    返回:
        提示词内容
    """
    prompt_path = PROMPTS_DIR / f"{name}.md"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"提示词文件不存在: {prompt_path}")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

# endregion
# ============================================


# ============================================
# region 历史记录格式化
# ============================================

def format_history(steps: List[AgentStep]) -> str:
    """
    格式化执行历史，供 Agent 参考
    
    参数:
        steps: 执行步骤列表
    返回:
        格式化的历史字符串
    """
    if not steps:
        return ""
    
    lines = ["## 执行历史\n"]
    
    for step in steps:
        lines.append(f"### 第 {step.step_number} 步\n")
        
        if step.thought:
            lines.append(f"**思考**：{step.thought}\n")
        
        if step.tool_name:
            lines.append(f"**调用工具**：{step.tool_name}")
            if step.tool_params:
                lines.append(f"**参数**：{step.tool_params}")
        
        if step.tool_result is not None:
            # 限制结果长度，避免 token 过多
            result_str = str(step.tool_result)
            if len(result_str) > 500:
                result_str = result_str[:500] + "...(结果已截断)"
            lines.append(f"**结果**：{result_str}\n")
        
        if step.error:
            lines.append(f"**错误**：{step.error}\n")
    
    return "\n".join(lines)

# endregion
# ============================================


# ============================================
# region 系统提示词生成
# ============================================

def build_system_prompt(task: str, steps: List[AgentStep] = None) -> str:
    """
    构建完整的系统提示词
    
    参数:
        task: 用户任务
        steps: 已执行的步骤（可选）
    返回:
        完整的提示词
    """
    # 加载模板
    template = load_prompt("agent_system")
    
    # 获取工具列表
    tools_prompt = tool_registry.get_tools_prompt()
    
    # 格式化历史
    history = format_history(steps or [])
    
    # 填充模板
    prompt = template.format(
        tools=tools_prompt,
        task=task,
        history=history,
    )
    
    return prompt

# endregion
# ============================================