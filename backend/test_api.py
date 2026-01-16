"""API 测试脚本"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"


def check_server():
    """检查服务是否运行"""
    try:
        resp = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health", timeout=3)
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def test_chat(message: str):
    """测试对话接口"""
    print(f"\n=== 测试对话: {message} ===")
    try:
        resp = requests.post(
            f"{BASE_URL}/chat/",
            json={"message": message},
            timeout=60
        )

        # 检查响应状态
        if resp.status_code != 200:
            print(f"错误: HTTP {resp.status_code}")
            print(f"响应: {resp.text[:500]}")
            return

        # 尝试解析 JSON
        try:
            data = resp.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(f"响应不是有效 JSON: {resp.text[:500]}")

    except requests.exceptions.ConnectionError:
        print("错误: 无法连接服务器，请确保后端已启动")
        print("启动命令: cd backend && uvicorn app.main:app --reload")
    except requests.exceptions.Timeout:
        print("错误: 请求超时")

def test_chat_stream(message: str):
    """测试流式对话"""
    print(f"\n=== 测试流式对话: {message} ===")
    resp = requests.post(
        f"{BASE_URL}/chat/stream",
        json={"message": message},
        stream=True
    )
    for line in resp.iter_lines():
        if line:
            print(line.decode('utf-8'))

def test_upload(pdf_path: str, use_markitdown: bool = True):
    """测试上传接口"""
    print(f"\n=== 测试上传: {pdf_path} ===")
    with open(pdf_path, 'rb') as f:
        resp = requests.post(
            f"{BASE_URL}/upload/contract/stream",
            files={"file": f},
            data={
                "use_markitdown": str(use_markitdown).lower(),
                "save_to_db": "false"
            },
            stream=True
        )
        for line in resp.iter_lines():
            if line:
                print(line.decode('utf-8'))

if __name__ == "__main__":
    # 先检查服务是否运行
    print("检查服务状态...")
    if not check_server():
        print("\n❌ 服务未启动！请先运行：")
        print("   cd backend")
        print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        exit(1)

    print("✅ 服务已启动\n")

    # 测试对话
    test_chat("查询所有业绩")
    test_chat("有哪些律师")

    # 测试流式对话
    test_chat_stream("帮我分析一下业绩数据")

    # 测试上传（替换为你的 PDF 路径）
    #test_upload("D:/test/contract.pdf", use_markitdown=True)
