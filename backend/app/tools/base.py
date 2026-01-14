"""
工具基类
定义工具的标准结构和接口
"""

from typing import Any, Callable, Optional
from pydantic import BaseModel, Field


# ============================================
# region 工具参数模型
# ============================================

class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str = Field(..., description="参数名称")
    type: str = Field(..., description="参数类型")
    description: str = Field("", description="参数描述")
    required: bool = Field(False, description="是否必填")
    default: Optional[Any] = Field(None, description="默认值")

# endregion
# ============================================


# ============================================
# region 工具定义模型
# ============================================

class ToolDefinition(BaseModel):
    """
    工具定义
    包含工具的元信息，供 Agent 理解和调用
    
    类比：图书馆的"技能说明卡"
    - name: 技能名称（如"查找图书"）
    - description: 技能说明（如"根据书名或作者查找图书位置"）
    - parameters: 需要的信息（如"书名"、"作者"）
    """
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述（供 Agent 理解用途）")
    category: str = Field("general", description="工具分类")
    parameters: list[ToolParameter] = Field(default_factory=list, description="参数列表")
    
    def to_prompt_string(self) -> str:
        """
        转换为提示词格式
        让 Agent 理解如何调用这个工具
        """
        params_str = ""
        if self.parameters:
            params_list = []
            for p in self.parameters:
                req_mark = "*" if p.required else ""
                params_list.append(f"    - {p.name}{req_mark} ({p.type}): {p.description}")
            params_str = "\n" + "\n".join(params_list)
        
        return f"""- **{self.name}**: {self.description}{params_str}"""

# endregion
# ============================================


# ============================================
# region 工具类
# ============================================

class Tool:
    """
    工具类
    封装可调用的函数及其元信息
    
    类比：图书管理员的一项具体技能
    - definition: 技能说明卡
    - func: 实际执行的动作
    """
    
    def __init__(
        self,
        func: Callable,
        name: str,
        description: str,
        category: str = "general",
        parameters: list[ToolParameter] = None,
    ):
        self.func = func
        self.definition = ToolDefinition(
            name=name,
            description=description,
            category=category,
            parameters=parameters or [],
        )
    
    @property
    def name(self) -> str:
        return self.definition.name
    
    @property
    def description(self) -> str:
        return self.definition.description
    
    def __call__(self, *args, **kwargs) -> Any:
        """调用工具"""
        return self.func(*args, **kwargs)
    
    def __repr__(self) -> str:
        return f"<Tool({self.name})>"

# endregion
# ============================================


# ============================================
# region 工具调用结果
# ============================================

class ToolResult(BaseModel):
    """
    工具调用结果
    标准化的返回格式
    """
    tool_name: str = Field(..., description="调用的工具名称")
    success: bool = Field(..., description="是否成功")
    result: Optional[Any] = Field(None, description="返回结果")
    error: Optional[str] = Field(None, description="错误信息")
    
    @classmethod
    def ok(cls, tool_name: str, result: Any) -> "ToolResult":
        """成功结果"""
        return cls(tool_name=tool_name, success=True, result=result)
    
    @classmethod
    def fail(cls, tool_name: str, error: str) -> "ToolResult":
        """失败结果"""
        return cls(tool_name=tool_name, success=False, error=error)

# endregion
# ============================================