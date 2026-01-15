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
    # 快速路径 - 简单查询直接执行，不调用 LLM
    # ============================================
    def _try_quick_path(self, message: str) -> Optional[str]:
        """快速路径：简单查询直接执行"""
        msg = message.lower().strip()
        print(f"[快速路径] 检查消息: {msg}")
        
        # 业绩查询
        if any(kw in msg for kw in ["所有业绩", "查询业绩", "业绩列表", "查看业绩", "有哪些业绩"]):
            print("[快速路径] 匹配: 业绩查询")
            return self._quick_search_performances({})
        
        if "常年" in msg and ("顾问" in msg or "合同" in msg):
            print("[快速路径] 匹配: 常年法律顾问")
            return self._quick_search_performances({"contract_type": "常年法律顾问合同"})
        
        # 律师查询
        if any(kw in msg for kw in ["所有律师", "查询律师", "律师列表", "查看律师", "有哪些律师", "参与的律师", "律师有哪些"]):
            print("[快速路径] 匹配: 律师查询")
            return self._quick_search_lawyers({})
        
        # 企业查询
        if any(kw in msg for kw in ["所有企业", "查询企业", "企业列表", "查看企业", "有哪些企业", "有哪些客户"]):
            print("[快速路径] 匹配: 企业查询")
            return self._quick_search_enterprises({})
        
        if "国企" in msg or "国有" in msg:
            print("[快速路径] 匹配: 国企查询")
            return self._quick_search_enterprises({"is_state_owned": True})
        
        # 统计查询
        if any(kw in msg for kw in ["业绩统计", "统计", "汇总"]):
            print("[快速路径] 匹配: 统计查询")
            return self._quick_get_stats()
        
        print("[快速路径] 未匹配，走 Agent 循环")
        return None
    
    def _quick_search_performances(self, params: dict) -> str:
        """快速查询业绩"""
        result = self.tool_registry.execute("search_performances", params)
        if not result.get("success"):
            return "查询业绩失败。"
        
        data = result.get("data", [])
        if not data:
            return "当前没有业绩记录。"
        
        response = f"查询到 **{len(data)}** 条业绩记录：\n\n"
        for i, p in enumerate(data[:10], 1):
            response += f"{i}. **{p.get('party_a', '未知')}** - {p.get('contract_type', '未知')}"
            if p.get('amount'):
                response += f" - {p['amount']}万元"
            if p.get('sign_date'):
                response += f" ({p['sign_date']})"
            if p.get('team_member'):
                response += f"\n   👤 律师: {p['team_member']}"
            response += "\n"
        return response
    
    def _quick_search_lawyers(self, params: dict) -> str:
        """快速查询律师"""
        result = self.tool_registry.execute("search_lawyers", params)
        if not result.get("success"):
            return "查询律师失败。"
        
        data = result.get("data", [])
        if not data:
            return "当前没有律师记录。"
        
        response = f"查询到 **{len(data)}** 位律师：\n\n"
        for i, l in enumerate(data, 1):
            response += f"{i}. **{l.get('name', '未知')}**"
            if l.get('license_no'):
                response += f" (执业证号: {l['license_no']})"
            response += "\n"
        return response
    
    def _quick_search_enterprises(self, params: dict) -> str:
        """快速查询企业"""
        result = self.tool_registry.execute("search_enterprises", params)
        if not result.get("success"):
            return "查询企业失败。"
        
        data = result.get("data", [])
        if not data:
            filter_text = "国企" if params.get("is_state_owned") else "企业"
            return f"当前没有{filter_text}记录。"
        
        response = f"查询到 **{len(data)}** 家企业：\n\n"
        for i, e in enumerate(data, 1):
            response += f"{i}. **{e.get('company_name', '未知')}**"
            if e.get('is_state_owned'):
                response += " [国企]"
            response += "\n"
        return response
    
    def _quick_get_stats(self) -> str:
        """快速获取统计"""
        result = self.tool_registry.execute("get_performance_stats", {})
        if not result.get("success"):
            return "获取统计失败。"
        
        data = result.get("data", {})
        return f"📊 业绩统计：共 {data.get('total_count', 0)} 条，总金额 {data.get('total_amount', 0):.2f} 万元"
    
    # ============================================
    # 主运行方法
    # ============================================
    def run(self, user_message: str) -> str:
        """运行 Agent"""
        start_time = time.time()
        
        # 优先尝试快速路径
        quick_result = self._try_quick_path(user_message)
        if quick_result:
            elapsed = time.time() - start_time
            print(f"[Agent] 快速路径完成，耗时: {elapsed:.2f}s")
            return quick_result
        
        # 正常 Agent 循环
        print(f"[Agent] 进入 Agent 循环")
        self.state.reset()
        self.conversation_history = [{"role": "user", "content": user_message}]
        
        for step in range(1, self.max_steps + 1):
            step_start = time.time()
            print(f"[Agent] Step {step}/{self.max_steps}")
            
            # Think
            self.state.transition(StateType.THINKING)
            response = self._call_llm()
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
            
            result = self.tool_registry.execute(tool_name, tool_params)
            
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
        
        # 快速路径
        quick_result = self._try_quick_path(user_message)
        if quick_result:
            elapsed = time.time() - start_time
            yield {"type": "answer", "answer": quick_result, "elapsed": f"{elapsed:.2f}s"}
            return
        
        # Agent 循环
        self.state.reset()
        self.conversation_history = [{"role": "user", "content": user_message}]
        
        for step in range(1, self.max_steps + 1):
            step_start = time.time()
            
            self.state.transition(StateType.THINKING)
            yield {"type": "thinking", "step": step}
            
            response = self._call_llm()
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
            
            result = self.tool_registry.execute(tool_name, tool_params)
            step_elapsed = time.time() - step_start
            
            yield {
                "type": "tool_result",
                "step": step,
                "tool": tool_name,
                "success": result.get("success", False),
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
    
    def _call_llm(self) -> Optional[str]:
        """调用 LLM"""
        try:
            response = self.client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.conversation_history
                ],
                temperature=0.7,
                max_tokens=1500,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[Agent] LLM 错误: {e}")
            return None
    
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
    
    def _generate_final_answer(self) -> str:
        """生成最终回答"""
        try:
            self.conversation_history.append({
                "role": "user",
                "content": "请简洁回答用户问题，不要使用标签。"
            })
            response = self.client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[
                    {"role": "system", "content": "你是招投标助手，请简洁回答。"},
                    *self.conversation_history
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"生成回答出错: {e}"