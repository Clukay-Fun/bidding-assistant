"""
Chat API 测试脚本
"""

import httpx
import json

# 直连本地，不走代理
CLIENT = httpx.Client(
    timeout=120,
    trust_env=False,  # 禁用环境变量中的代理设置
)


def test_chat_sync():
    """测试同步对话接口"""
    print("\n" + "=" * 50)
    print("🧪 测试同步对话接口")
    print("=" * 50)
    
    response = CLIENT.post(
        "http://localhost:8000/api/v1/chat/",
        json={
            "message": "查询包含能源关键词的业绩",
            "max_steps": 5,  # 给足够的步骤
        },
    )
    
    print(f"状态码: {response.status_code}")
    print(f"响应:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_chat_stream():
    """测试流式对话接口"""
    print("\n" + "=" * 50)
    print("🧪 测试流式对话接口 (SSE)")
    print("=" * 50)
    
    # 使用独立的 Client 进行流式请求
    with httpx.Client(timeout=120, trust_env=False) as client:
        with client.stream(
            "POST",
            "http://localhost:8000/api/v1/chat/stream",
            json={
                "message": "查询所有律师",
                "max_steps": 5,
            },
        ) as response:
            print(f"状态码: {response.status_code}")
            print("事件流:")
            
            for line in response.iter_lines():
                if line.startswith("event:"):
                    event_type = line[7:].strip()
                    print(f"\n  📡 [{event_type}]", end="")
                elif line.startswith("data:"):
                    data = line[5:].strip()
                    print(f" {data}")

def test_tools_list():
    """测试工具列表接口"""
    print("\n" + "=" * 50)
    print("🧪 测试工具列表接口")
    print("=" * 50)
    
    response = CLIENT.get("http://localhost:8000/api/v1/chat/tools")
    
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"工具数量: {result['count']}")
    for tool in result['tools']:
        print(f"  - {tool['name']}: {tool['description']}")


if __name__ == "__main__":
    test_tools_list()
    test_chat_sync()
    test_chat_stream()
    
    CLIENT.close()
    
    print("\n" + "=" * 50)
    print("🎉 API 测试完成!")
    print("=" * 50)