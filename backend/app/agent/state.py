"""
Agent 状态机
定义 Agent 运行过程中的各种状态

类比：图书管理员的工作状态牌
- IDLE: 空闲，等待任务
- THINKING: 思考中，分析用户需求
- EXECUTING: 执行中，调用工具
- OBSERVING: 观察中，处理工具返回结果
- DONE: 完成，准备返回答案
- ERROR: 出错，需要处理异常
"""

from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# region 状态枚举
# ============================================

class AgentState(str, Enum):
    """Agent 状态枚举"""
    IDLE = "idle"           # 空闲
    THINKING = "thinking"   # 思考中
    EXECUTING = "executing" # 执行工具中
    OBSERVING = "observing" # 观察结果中
    DONE = "done"           # 完成
    ERROR = "error"         # 错误

# endregion
# ============================================


# ============================================
# region 执行步骤记录
# ============================================

class AgentStep(BaseModel):
    """
    Agent 单步执行记录
    记录每一步的思考、行动和结果
    """
    step_number: int = Field(..., description="步骤编号")
    state: AgentState = Field(..., description="当前状态")
    thought: Optional[str] = Field(None, description="思考内容")
    tool_name: Optional[str] = Field(None, description="调用的工具名称")
    tool_params: Optional[dict] = Field(None, description="工具参数")
    tool_result: Optional[Any] = Field(None, description="工具返回结果")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    
    def to_trace_string(self) -> str:
        """转换为可读的轨迹字符串"""
        lines = [f"[Step {self.step_number}] {self.state.value.upper()}"]
        
        if self.thought:
            lines.append(f"  💭 思考: {self.thought[:100]}...")
        
        if self.tool_name:
            lines.append(f"  🔧 工具: {self.tool_name}")
            if self.tool_params:
                lines.append(f"  📥 参数: {self.tool_params}")
        
        if self.tool_result is not None:
            result_str = str(self.tool_result)
            if len(result_str) > 100:
                result_str = result_str[:100] + "..."
            lines.append(f"  📤 结果: {result_str}")
        
        if self.error:
            lines.append(f"  ❌ 错误: {self.error}")
        
        return "\n".join(lines)

# endregion
# ============================================


# ============================================
# region Agent 上下文
# ============================================

class AgentContext(BaseModel):
    """
    Agent 运行上下文
    保存整个执行过程的状态和历史
    """
    # 任务信息
    task: str = Field(..., description="用户任务/问题")
    
    # 状态
    current_state: AgentState = Field(default=AgentState.IDLE, description="当前状态")
    current_step: int = Field(default=0, description="当前步骤")
    
    # 历史记录
    steps: List[AgentStep] = Field(default_factory=list, description="执行步骤历史")
    
    # 结果
    final_answer: Optional[str] = Field(None, description="最终答案")
    
    # 配置
    max_steps: int = Field(default=10, description="最大步骤数")
    
    def add_step(
        self,
        state: AgentState,
        thought: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_params: Optional[dict] = None,
        tool_result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> AgentStep:
        """添加执行步骤"""
        self.current_step += 1
        self.current_state = state
        
        step = AgentStep(
            step_number=self.current_step,
            state=state,
            thought=thought,
            tool_name=tool_name,
            tool_params=tool_params,
            tool_result=tool_result,
            error=error,
        )
        
        self.steps.append(step)
        return step
    
    def is_finished(self) -> bool:
        """检查是否已完成"""
        return self.current_state in (AgentState.DONE, AgentState.ERROR)
    
    def is_over_limit(self) -> bool:
        """检查是否超过步骤限制"""
        return self.current_step >= self.max_steps
    
    def get_trace(self) -> str:
        """获取完整执行轨迹"""
        lines = [
            "=" * 50,
            f"📋 任务: {self.task}",
            "=" * 50,
        ]
        
        for step in self.steps:
            lines.append(step.to_trace_string())
            lines.append("-" * 30)
        
        if self.final_answer:
            lines.append(f"✅ 最终答案: {self.final_answer}")
        
        return "\n".join(lines)

# endregion
# ============================================