"""
Agent 核心循环
实现 Think → Act → Observe 的自主循环

类比：图书馆的智能管理员
- 接收用户请求
- 思考如何处理
- 调用各种技能（工具）
- 观察结果并决定下一步
- 最终给出答案
"""

import json
import re
from typing import Optional, Generator
from openai import OpenAI

from app.config import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    REASONING_MODEL,
    AGENT_MAX_STEPS,
)
from app.agent.state import AgentState, AgentContext
from app.agent.prompts import build_system_prompt
from app.tools import tool_registry


# ============================================
# region LLM 客户端
# ============================================

def get_llm_client() -> OpenAI:
    """获取 LLM 客户端"""
    return OpenAI(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL,
    )

# endregion
# ============================================


# ============================================
# region 响应解析
# ============================================

def parse_agent_response(response_text: str) -> dict:
    """
    解析 Agent 的 JSON 响应
    
    参数:
        response_text: LLM 返回的文本
    返回:
        解析后的字典
    """
    clean_text = response_text.strip()
    
    # 移除 <think>...</think> 标签（某些模型会输出）
    think_match = re.search(r'<think>.*?</think>', clean_text, re.DOTALL)
    if think_match:
        clean_text = clean_text[think_match.end():].strip()
    
    # 尝试提取 JSON 块（```json ... ```）
    json_match = re.search(r'```json\s*(.*?)\s*```', clean_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # 尝试提取 ``` ... ```
        code_match = re.search(r'```\s*(.*?)\s*```', clean_text, re.DOTALL)
        if code_match:
            json_str = code_match.group(1).strip()
        else:
            # 尝试直接查找完整的 JSON 对象 {...}
            # 找到第一个 { 和最后一个 }
            start_idx = clean_text.find('{')
            end_idx = clean_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = clean_text[start_idx:end_idx + 1]
            else:
                # 无法找到 JSON
                return {
                    "thought": clean_text[:500] if clean_text else "无法解析响应",
                    "action": None,
                    "answer": None,
                }
    
    # 直接解析 JSON（不要替换换行符，json.loads 可以处理）
    try:
        result = json.loads(json_str)
        return {
            "thought": result.get("thought", ""),
            "action": result.get("action"),
            "answer": result.get("answer"),
        }
    except json.JSONDecodeError as e:
        print(f"   ⚠️ JSON 解析失败: {e}")
        print(f"   ⚠️ 尝试解析的内容: {json_str[:200]}...")
        
        # 返回原文作为思考内容
        return {
            "thought": clean_text[:500],
            "action": None,
            "answer": None,
        }

# endregion
# ============================================


# ============================================
# region Agent 类
# ============================================

class Agent:
    """
    招投标助手 Agent
    
    使用方法:
        agent = Agent()
        result = agent.run("查找近3年的能源类业绩")
        print(result.final_answer)
    """
    
    def __init__(self, max_steps: int = None):
        """
        初始化 Agent
        
        参数:
            max_steps: 最大执行步骤数
        """
        self.client = get_llm_client()
        self.max_steps = max_steps or AGENT_MAX_STEPS
    
    def _call_llm(self, prompt: str) -> str:
        """
        调用 LLM - 调试版本
        """
        print(f"🔍 === LLM 调用开始 ===")
        print(f"🔍 使用模型: {REASONING_MODEL}")
        print(f"🔍 === LLM 调用分割线 ===")
        
        try:
            response = self.client.chat.completions.create(
                model=REASONING_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000,
            )
            
            content = response.choices[0].message.content
            return content
            
        except Exception as e:
            print(f"❌ LLM 调用失败: {e}")
            print(f"❌ 错误类型: {type(e)}")
            raise
    
    def _think(self, context: AgentContext) -> dict:
        """
        思考阶段：分析任务，决定下一步行动
        
        参数:
            context: Agent 上下文
        返回:
            解析后的行动决策
        """
        try:
            # 构建提示词
            prompt = build_system_prompt(
                task=context.task,
                steps=context.steps,
            )
        except Exception as e:
            print(f"   ❌ 构建提示词失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        try:
            # 调用 LLM
            response_text = self._call_llm(prompt)
            print(f"   📨 LLM 响应长度: {len(response_text)} 字符")
        except Exception as e:
            print(f"   ❌ LLM 调用失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        try:
            # 解析响应
            decision = parse_agent_response(response_text)
            return decision
        except Exception as e:
            print(f"   ❌ 解析响应失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _execute_tool(self, tool_name: str, tool_params: dict) -> dict:
        """
        执行工具
        
        参数:
            tool_name: 工具名称
            tool_params: 工具参数
        返回:
            工具执行结果
        """
        result = tool_registry.call(tool_name, **(tool_params or {}))
        
        if result.success:
            return {"success": True, "data": result.result}
        else:
            return {"success": False, "error": result.error}
    
    def run(self, task: str) -> AgentContext:
        """
        运行 Agent 完成任务
        
        参数:
            task: 用户任务/问题
        返回:
            AgentContext 包含完整执行过程和结果
        """
        # 初始化上下文
        context = AgentContext(
            task=task,
            max_steps=self.max_steps,
        )
        
        print(f"\n{'='*50}")
        print(f"🚀 Agent 开始执行任务")
        print(f"📋 任务: {task}")
        print(f"{'='*50}")
        
        # 主循环
        while not context.is_finished() and not context.is_over_limit():
            # 1. 思考阶段
            context.current_state = AgentState.THINKING
            print(f"\n🤔 [Step {context.current_step + 1}] 思考中...")
            
            try:
                decision = self._think(context)
            except Exception as e:
                context.add_step(
                    state=AgentState.ERROR,
                    error=f"思考阶段出错: {str(e)}",
                )
                break
            
            thought = decision.get("thought", "")
            action = decision.get("action")
            answer = decision.get("answer")
            
            print(f"   💭 思考: {thought[:100]}..." if len(thought) > 100 else f"   💭 思考: {thought}")
            
            # 2. 检查是否有最终答案
            if answer:
                context.add_step(
                    state=AgentState.DONE,
                    thought=thought,
                )
                context.final_answer = answer
                context.current_state = AgentState.DONE
                print(f"   ✅ 得出答案")
                break
            
            # 3. 执行工具
            if action and action.get("tool"):
                tool_name = action["tool"]
                tool_params = action.get("params", {})
                
                context.current_state = AgentState.EXECUTING
                print(f"   🔧 调用工具: {tool_name}")
                print(f"   📥 参数: {tool_params}")
                
                try:
                    tool_result = self._execute_tool(tool_name, tool_params)
                except Exception as e:
                    tool_result = {"success": False, "error": str(e)}
                
                # 4. 观察结果
                context.current_state = AgentState.OBSERVING
                
                if tool_result.get("success"):
                    result_data = tool_result.get("data", {})
                    print(f"   📤 结果: 成功")
                    
                    context.add_step(
                        state=AgentState.OBSERVING,
                        thought=thought,
                        tool_name=tool_name,
                        tool_params=tool_params,
                        tool_result=result_data,
                    )
                else:
                    error_msg = tool_result.get("error", "未知错误")
                    print(f"   ❌ 结果: 失败 - {error_msg}")
                    
                    context.add_step(
                        state=AgentState.OBSERVING,
                        thought=thought,
                        tool_name=tool_name,
                        tool_params=tool_params,
                        error=error_msg,
                    )
            else:
                # 没有工具调用也没有答案，记录思考步骤
                context.add_step(
                    state=AgentState.THINKING,
                    thought=thought,
                )
        
        # 检查是否超过步骤限制
        if context.is_over_limit() and not context.final_answer:
            context.current_state = AgentState.ERROR
            context.final_answer = "抱歉，我尝试了多次但未能完成任务。请尝试简化问题或提供更多信息。"
            print(f"\n⚠️ 超过最大步骤限制 ({self.max_steps})")
        
        print(f"\n{'='*50}")
        print(f"🏁 Agent 执行完成")
        print(f"📊 总步骤: {context.current_step}")
        print(f"{'='*50}")
        
        return context
    
    def run_stream(self, task: str) -> Generator[dict, None, None]:
        """
        流式运行 Agent（用于 SSE 推送）
        
        参数:
            task: 用户任务/问题
        生成:
            执行过程中的事件
        """
        # 初始化上下文
        context = AgentContext(
            task=task,
            max_steps=self.max_steps,
        )
        
        yield {"event": "start", "data": {"task": task}}
        
        # 主循环
        while not context.is_finished() and not context.is_over_limit():
            # 1. 思考阶段
            context.current_state = AgentState.THINKING
            yield {"event": "status", "data": {"state": "thinking", "step": context.current_step + 1}}
            
            try:
                decision = self._think(context)
            except Exception as e:
                context.add_step(state=AgentState.ERROR, error=str(e))
                yield {"event": "error", "data": {"error": str(e)}}
                break
            
            thought = decision.get("thought", "")
            action = decision.get("action")
            answer = decision.get("answer")
            
            yield {"event": "thinking", "data": {"thought": thought}}
            
            # 2. 检查是否有最终答案
            if answer:
                context.add_step(state=AgentState.DONE, thought=thought)
                context.final_answer = answer
                context.current_state = AgentState.DONE
                yield {"event": "answer", "data": {"answer": answer}}
                break
            
            # 3. 执行工具
            if action and action.get("tool"):
                tool_name = action["tool"]
                tool_params = action.get("params", {})
                
                context.current_state = AgentState.EXECUTING
                yield {
                    "event": "tool_call",
                    "data": {"tool": tool_name, "params": tool_params}
                }
                
                try:
                    tool_result = self._execute_tool(tool_name, tool_params)
                except Exception as e:
                    tool_result = {"success": False, "error": str(e)}
                
                # 4. 观察结果
                context.current_state = AgentState.OBSERVING
                
                if tool_result.get("success"):
                    result_data = tool_result.get("data", {})
                    context.add_step(
                        state=AgentState.OBSERVING,
                        thought=thought,
                        tool_name=tool_name,
                        tool_params=tool_params,
                        tool_result=result_data,
                    )
                    yield {
                        "event": "tool_result",
                        "data": {"tool": tool_name, "success": True, "result": result_data}
                    }
                else:
                    error_msg = tool_result.get("error", "未知错误")
                    context.add_step(
                        state=AgentState.OBSERVING,
                        thought=thought,
                        tool_name=tool_name,
                        tool_params=tool_params,
                        error=error_msg,
                    )
                    yield {
                        "event": "tool_result",
                        "data": {"tool": tool_name, "success": False, "error": error_msg}
                    }
            else:
                context.add_step(state=AgentState.THINKING, thought=thought)
        
        # 检查是否超过步骤限制
        if context.is_over_limit() and not context.final_answer:
            context.current_state = AgentState.ERROR
            context.final_answer = "抱歉，我尝试了多次但未能完成任务。"
            yield {"event": "error", "data": {"error": "超过最大步骤限制"}}
        
        yield {"event": "done", "data": {"total_steps": context.current_step}}

# endregion
# ============================================