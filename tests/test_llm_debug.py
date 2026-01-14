"""
LLM 响应调试脚本
用于查看 LLM 实际返回的内容格式
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from openai import OpenAI
from app.config import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    REASONING_MODEL,
)


def test_llm_response():
    """测试 LLM 原始响应"""
    print("\n" + "=" * 50)
    print("🧪 LLM 响应调试")
    print("=" * 50)
    
    client = OpenAI(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL,
    )
    
    # 简单的测试提示词
    prompt = """
你是一个助手。请用以下 JSON 格式回复：
```json
{
    "thought": "你的思考",
    "action": null,
    "answer": "你的回答"
}
```

用户问题：你好，请介绍一下你自己

请输出 JSON：
"""
    
    print(f"\n📤 发送请求到: {REASONING_MODEL}")
    
    response = client.chat.completions.create(
        model=REASONING_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1000,
    )
    
    content = response.choices[0].message.content
    
    print(f"\n📨 原始响应 (repr):")
    print(repr(content))
    
    print(f"\n📨 原始响应 (显示):")
    print(content)
    
    print(f"\n📊 响应长度: {len(content)} 字符")


if __name__ == "__main__":
    test_llm_response()