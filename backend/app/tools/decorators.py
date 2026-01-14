"""
工具装饰器
使用 @tool 装饰器将普通函数注册为 Agent 可调用的工具

类比：给函数盖上"技能认证章"
- 普通函数 → 盖章后 → 成为 Agent 可调用的工具
"""

import inspect
from typing import Callable, Optional, get_type_hints

from app.tools.base import Tool, ToolParameter
from app.tools.registry import tool_registry


# ============================================
# region 类型映射
# ============================================

# Python 类型到字符串的映射
TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


def get_type_string(python_type) -> str:
    """将 Python 类型转换为字符串描述"""
    # 处理 Optional 类型
    origin = getattr(python_type, "__origin__", None)
    if origin is not None:
        # Optional[X] 实际上是 Union[X, None]
        args = getattr(python_type, "__args__", ())
        non_none_args = [a for a in args if a is not type(None)]
        if non_none_args:
            return get_type_string(non_none_args[0])
    
    return TYPE_MAP.get(python_type, "any")

# endregion
# ============================================


# ============================================
# region 参数解析
# ============================================

def extract_parameters(func: Callable) -> list[ToolParameter]:
    """
    从函数签名中提取参数信息
    
    参数:
        func: 要分析的函数
    返回:
        ToolParameter 列表
    """
    parameters = []
    
    # 获取函数签名
    sig = inspect.signature(func)
    
    # 尝试获取类型提示
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}
    
    # 解析文档字符串中的参数描述
    param_docs = {}
    if func.__doc__:
        lines = func.__doc__.split("\n")
        current_param = None
        for line in lines:
            line = line.strip()
            # 匹配 "参数名: 描述" 或 "参数名 (类型): 描述" 格式
            if ":" in line and not line.startswith(":"):
                parts = line.split(":", 1)
                param_name = parts[0].strip().split()[0]  # 取第一个词作为参数名
                param_desc = parts[1].strip() if len(parts) > 1 else ""
                param_docs[param_name] = param_desc
    
    # 遍历参数
    for param_name, param in sig.parameters.items():
        # 跳过 self, cls, db 等特殊参数
        if param_name in ("self", "cls", "db"):
            continue
        
        # 获取类型
        param_type = hints.get(param_name, str)
        type_str = get_type_string(param_type)
        
        # 判断是否必填
        required = param.default is inspect.Parameter.empty
        
        # 获取默认值
        default = None if param.default is inspect.Parameter.empty else param.default
        
        # 获取描述
        description = param_docs.get(param_name, "")
        
        parameters.append(ToolParameter(
            name=param_name,
            type=type_str,
            description=description,
            required=required,
            default=default,
        ))
    
    return parameters

# endregion
# ============================================


# ============================================
# region @tool 装饰器
# ============================================

def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "general",
):
    """
    工具装饰器
    将函数注册为 Agent 可调用的工具
    
    用法:
        @tool(
            name="search_performances",
            description="搜索业绩合同",
            category="database"
        )
        def search_performances(keyword: str, years: int = 5):
            '''
            搜索业绩
            
            keyword: 搜索关键词
            years: 近几年（默认5年）
            '''
            ...
    
    参数:
        name: 工具名称（默认使用函数名）
        description: 工具描述（默认使用函数文档字符串的第一行）
        category: 工具分类
    """
    def decorator(func: Callable) -> Callable:
        # 确定工具名称
        tool_name = name or func.__name__
        
        # 确定工具描述
        tool_description = description
        if not tool_description and func.__doc__:
            # 使用文档字符串的第一行
            tool_description = func.__doc__.strip().split("\n")[0]
        if not tool_description:
            tool_description = f"调用 {tool_name}"
        
        # 提取参数信息
        parameters = extract_parameters(func)
        
        # 创建工具实例
        tool_instance = Tool(
            func=func,
            name=tool_name,
            description=tool_description,
            category=category,
            parameters=parameters,
        )
        
        # 注册到全局注册中心
        tool_registry.register(tool_instance)
        
        # 在函数上附加工具信息（方便调试）
        func._tool = tool_instance
        
        return func
    
    return decorator

# endregion
# ============================================