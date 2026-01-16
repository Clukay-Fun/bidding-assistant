"""
工具注册中心（单例模式）
管理所有可用工具的注册、查询和调用

类比：图书馆的"技能管理办公室"
- 所有管理员的技能都在这里登记
- Agent 来这里查询有哪些技能可用
- Agent 通过这里调用具体技能
"""

from typing import Dict, List, Optional, Any
import json

from app.tools.base import Tool, ToolResult


# ============================================
# region 注册中心类
# ============================================

class ToolRegistry:
    """
    工具注册中心（单例）
    
    使用方法：
        registry = ToolRegistry()
        registry.register(tool)
        result = registry.call("tool_name", param1="value1")
    """
    
    _instance: Optional["ToolRegistry"] = None
    _tools: Dict[str, Tool] = {}
    
    def __new__(cls) -> "ToolRegistry":
        """单例模式：确保全局只有一个注册中心"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._tools = {}
        return cls._instance
    
    def register(self, tool: Tool) -> None:
        """
        注册工具
        
        参数:
            tool: 工具实例
        """
        if tool.name in self._tools:
            print(f"⚠️ 工具 '{tool.name}' 已存在，将被覆盖")
        
        self._tools[tool.name] = tool
        print(f"✅ 工具已注册: {tool.name}")
    
    def unregister(self, name: str) -> bool:
        """
        注销工具
        
        参数:
            name: 工具名称
        返回:
            是否成功注销
        """
        if name in self._tools:
            del self._tools[name]
            print(f"🗑️ 工具已注销: {name}")
            return True
        return False
    
    def get(self, name: str) -> Optional[Tool]:
        """
        获取工具
        
        参数:
            name: 工具名称
        返回:
            工具实例，不存在则返回 None
        """
        return self._tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> List[Tool]:
        """
        列出所有工具
        
        参数:
            category: 可选，按分类筛选
        返回:
            工具列表
        """
        tools = list(self._tools.values())
        
        if category:
            tools = [t for t in tools if t.definition.category == category]
        
        return tools
    
    def list_names(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())
    
    def call(self, name: str, params: dict = None, **kwargs) -> ToolResult:
        """
        调用工具
        
        参数:
            name: 工具名称
            params: 工具参数（字典形式）
            **kwargs: 工具参数（关键字形式）
        返回:
            ToolResult 标准化结果
        """
        tool = self.get(name)
        
        if not tool:
            return ToolResult.fail(
                tool_name=name,
                error=f"工具 '{name}' 不存在"
            )
        
        # 合并参数：params 字典 + kwargs
        final_params = {}
        if params:
            final_params.update(params)
        final_params.update(kwargs)
        
        try:
            result = tool(**final_params)
            return ToolResult.ok(tool_name=name, result=result)
        except Exception as e:
            return ToolResult.fail(tool_name=name, error=str(e))

    
    def get_tools_prompt(self, category: Optional[str] = None) -> str:
        """
        生成工具列表的提示词
        供 Agent 了解可用工具
        
        参数:
            category: 可选，按分类筛选
        返回:
            格式化的工具说明文本
        """
        tools = self.list_tools(category)
        
        if not tools:
            return "当前没有可用的工具。"
        
        lines = ["## 可用工具\n"]
        
        # 按分类分组
        categories: Dict[str, List[Tool]] = {}
        for tool in tools:
            cat = tool.definition.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(tool)
        
        # 生成每个分类的工具说明
        for cat, cat_tools in categories.items():
            lines.append(f"### {cat}\n")
            for tool in cat_tools:
                lines.append(tool.definition.to_prompt_string())
            lines.append("")
        
        return "\n".join(lines)
    
    def get_tools_json(self) -> List[dict]:
        """
        获取工具列表的 JSON 格式
        用于 API 返回或前端展示
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.definition.category,
                "parameters": [p.model_dump() for p in tool.definition.parameters],
            }
            for tool in self._tools.values()
        ]
    
    def clear(self) -> None:
        """清空所有工具（测试用）"""
        self._tools.clear()
        print("🗑️ 所有工具已清空")

# endregion
# ============================================


# ============================================
# region 全局注册中心实例
# ============================================

# 全局单例，方便直接导入使用
tool_registry = ToolRegistry()

# endregion
# ============================================