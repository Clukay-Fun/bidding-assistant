"""
对话 API 路由
提供 Agent 对话接口，支持 SSE 流式推送
"""

import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from app.tools import tool_registry
from app.agent import Agent


# ============================================
# region 路由定义
# ============================================

router = APIRouter(prefix="/chat", tags=["对话"])

# endregion
# ============================================


# ============================================
# region 请求/响应模型
# ============================================

class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    max_steps: Optional[int] = Field(None, ge=1, le=20, description="最大执行步骤")


class ChatResponse(BaseModel):
    """对话响应（非流式）"""
    answer: str = Field(..., description="Agent 回答")
    steps: int = Field(..., description="执行步骤数")
    tool_calls: list = Field(default_factory=list, description="工具调用记录")

# endregion
# ============================================


# ============================================
# region 初始化工具
# ============================================

def ensure_tools_registered():
    """确保工具已注册"""
    if not tool_registry.list_names():
        from app.tools import database  # noqa: F401

# endregion
# ============================================


# ============================================
# region API 接口
# ============================================

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    同步对话接口
    等待 Agent 完成后返回结果
    """
    ensure_tools_registered()
    
    agent = Agent(tool_registry=tool_registry, max_steps=request.max_steps or 10)
    result = agent.run(request.message)
    
    return ChatResponse(
    answer=result or "抱歉，我无法完成这个任务。",
    steps=1,  # 简化返回
    tool_calls=[],  # 简化返回
)


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    流式对话接口（SSE）
    实时推送 Agent 执行过程
    """
    ensure_tools_registered()
    
    agent = Agent(
            tool_registry=tool_registry,
            max_steps=request.max_steps or 10
        )
    
    async def event_generator():
        """生成 SSE 事件流"""
        for event in agent.run_stream(request.message):
            event_type = event.get("type", "message")
            # 整个 event 就是数据
            yield f"event: {event_type}\n"
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


@router.get("/tools")
async def list_tools():
    """
    获取可用工具列表
    """
    ensure_tools_registered()
    
    return {
        "count": len(tool_registry.list_names()),
        "tools": tool_registry.get_tools_json(),
    }

# endregion
# ============================================