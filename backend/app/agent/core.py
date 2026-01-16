"""
Agent 核心模块
实现 ReAct 模式的自主决策循环
"""

import json
import time
from typing import Optional, Generator
from openai import OpenAI

from app.config import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    CHAT_MODEL,
    REASONING_MODEL,
)
from app.tools import ToolRegistry
from app.agent.state import AgentStateManager, StateType
from app.agent.prompts import build_system_prompt


class Agent:
    """ReAct Agent 实现"""
    
    def __init__(self, tool_registry: ToolRegistry, max_steps: int = 5):
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.client = OpenAI(
            api_key=SILICONFLOW_API_KEY,
            base_url=SILICONFLOW_BASE_URL,
        )
        self.system_prompt = build_system_prompt(task="", steps=[])
        self.state = AgentStateManager()
        self.conversation_history = []
    
    # ============================================
    # region 主运行方法
    # ============================================
    def run(self, user_message: str) -> str:
        """运行 Agent"""
        start_time = time.time()
        
        # 正常 Agent 循环
        print(f"[Agent] 进入 Agent 循环")
        self.state.reset()
        self.conversation_history = [{"role": "user", "content": user_message}]
        
        for step in range(1, self.max_steps + 1):
            step_start = time.time()
            print(f"[Agent] Step {step}/{self.max_steps}")
            
            # Think（使用推理模型）
            self.state.transition(StateType.THINKING)
            response = self._call_reasoning()
            if not response:
                break
            
            thought, action = self._parse_response(response)
            
            # 完成
            if action is None:
                self.state.transition(StateType.FINISHED)
                elapsed = time.time() - start_time
                print(f"[Agent] 完成，总耗时: {elapsed:.2f}s")
                # 返回思考内容或生成最终回答
                if thought and len(thought) > 50:
                    return thought
                return self._generate_final_answer()
            
            # Act
            self.state.transition(StateType.ACTING)
            tool_name = action.get("tool")
            tool_params = action.get("params", {})
            print(f"[Agent] 调用工具: {tool_name}")
            
            result = self.tool_registry.call(tool_name, tool_params)
            
            # 更新对话历史
            self.conversation_history.append({"role": "assistant", "content": response})
            self.conversation_history.append({
                "role": "user",
                "content": f"工具结果:\n{json.dumps(result, ensure_ascii=False)}"
            })
            
            step_elapsed = time.time() - step_start
            print(f"[Agent] Step {step} 耗时: {step_elapsed:.2f}s")
        
        elapsed = time.time() - start_time
        print(f"[Agent] 循环结束，总耗时: {elapsed:.2f}s")
        return self._generate_final_answer()
    
    def run_stream(self, user_message: str) -> Generator[dict, None, None]:
        """流式运行"""
        start_time = time.time()
        
        # Agent 循环
        self.state.reset()
        self.conversation_history = [{"role": "user", "content": user_message}]
        
        for step in range(1, self.max_steps + 1):
            step_start = time.time()
            
            self.state.transition(StateType.THINKING)
            yield {"type": "thinking", "step": step}

            # 使用推理模型进行思考
            response = self._call_reasoning()
            if not response:
                break
            
            thought, action = self._parse_response(response)
            
            if thought:
                yield {"type": "thought", "step": step, "thought": thought}
            
            if action is None:
                break
            
            # 执行工具
            tool_name = action.get("tool")
            tool_params = action.get("params", {})
            
            yield {"type": "tool_call", "step": step, "tool": tool_name, "params": tool_params}
            
            result = self.tool_registry.call(tool_name, tool_params)
            step_elapsed = time.time() - step_start
            
            yield {
                "type": "tool_result",
                "step": step,
                "tool": tool_name,
                "success": result.success,
                "elapsed": f"{step_elapsed:.2f}s"
            }
            
            self.conversation_history.append({"role": "assistant", "content": response})
            self.conversation_history.append({
                "role": "user",
                "content": f"工具结果:\n{json.dumps(result, ensure_ascii=False)}"
            })
        
        # 最终回答
        answer = self._generate_final_answer()
        total_elapsed = time.time() - start_time
        yield {"type": "answer", "answer": answer, "elapsed": f"{total_elapsed:.2f}s"}
    # endregion
    # ============================================
    
    # ============================================
    # region LLM 调用
    # ============================================

    def _call_reasoning(self) -> Optional[str]:
        """调用推理模型（用于 Agent 规划和复杂判定）"""
        try:
            response = self.client.chat.completions.create(
                model=REASONING_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.conversation_history
                ],
                temperature=0.6,
                max_tokens=2000,
                stream=True
            )

            # 收集流式响应
            full_content = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_content += chunk.choices[0].delta.content

            return full_content if full_content else None

        except Exception as e:
            print(f"[Agent] 推理模型错误: {e}")
            return None

    def _call_chat(self) -> Optional[str]:
        """调用对话模型（用于最终回复）"""
        try:
            response = self.client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[
                    {"role": "system", "content": "你是招投标助手，请简洁回答。"},
                    *self.conversation_history
                ],
                temperature=0.7,
                max_tokens=1000,
                stream=True
            )

            # 收集流式响应
            full_content = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_content += chunk.choices[0].delta.content

            return full_content if full_content else None

        except Exception as e:
            print(f"[Agent] 对话模型错误: {e}")
            return None

    # endregion
    # ============================================

    
    def _parse_response(self, response: str) -> tuple:
        """解析响应"""
        thought = None
        action = None
        
        if "<think>" in response and "</think>" in response:
            thought = response.split("<think>")[1].split("</think>")[0].strip()
        
        if "<action>" in response and "</action>" in response:
            action_str = response.split("<action>")[1].split("</action>")[0].strip()
            try:
                action = json.loads(action_str)
            except:
                pass
        
        return thought, action
    
    # ============================================
    # region 最终回答生成
    # ============================================

    def _generate_final_answer(self) -> str:
        """生成最终回答（使用对话模型）"""
        try:
            self.conversation_history.append({
                "role": "user",
                "content": "请简洁回答用户问题，不要使用标签。"
            })

            # 使用对话模型生成最终回复
            result = self._call_chat()
            return result if result else "无法生成回答"

        except Exception as e:
            return f"生成回答出错: {e}"

    # endregion
    # ============================================