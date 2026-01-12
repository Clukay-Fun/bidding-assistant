"""
招投标助手系统 - 主入口
功能：统一入口，支持多种运行模式
"""

import sys
import argparse
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import OUTPUT_DIR, DOCUMENTS_DIR


def parse_document(file_path: str):
    """
    解析文档（PDF/Word → Markdown）
    """
    from src.ocr_parser import pdf_to_markdown
    from src.docx_to_markdown import docx_to_markdown
    from src.utils import get_file_type
    
    file_type = get_file_type(file_path)
    
    if file_type == 'pdf':
        return pdf_to_markdown(file_path)
    elif file_type == 'docx':
        return docx_to_markdown(file_path)
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")


def build_index(markdown_path: str):
    """
    构建知识库索引
    """
    from src.node_parser import parse_markdown_to_nodes
    from src.indexer import init_settings, build_index, load_nodes_from_json
    
    # 1. 解析文档结构
    print("\n📋 Step 1: 解析文档结构")
    nodes = parse_markdown_to_nodes(markdown_path)
    
    # 2. 构建向量索引
    print("\n📋 Step 2: 构建向量索引")
    init_settings()
    
    nodes_file = OUTPUT_DIR / f"{Path(markdown_path).stem}_nodes.json"
    text_nodes = load_nodes_from_json(str(nodes_file))
    
    index = build_index(text_nodes)
    print("\n✅ 知识库构建完成！")
    
    return index


def rag_chat():
    """
    RAG问答模式
    """
    from src.rag_query import main as rag_main
    rag_main()


def extract_contract(file_path: str, use_vision: bool = True):
    """
    提取合同信息
    """
    from src.contract_extractor import process_contract_pdf
    return process_contract_pdf(file_path, use_vision=use_vision)


def batch_extract(folder_path: str, use_vision: bool = True):
    """
    批量提取合同
    """
    from src.contract_extractor import batch_process_contracts
    return batch_process_contracts(folder_path, use_vision=use_vision)


def match_performance(requirement: str = None):
    """
    业绩匹配
    """
    from src.contract_matcher import match_contracts, interactive_match
    
    if requirement:
        return match_contracts(requirement)
    else:
        interactive_match()


def init_database():
    """
    初始化数据库
    """
    from src.database import init_db
    init_db()


def show_menu():
    """显示交互菜单"""
    print("\n" + "="*50)
    print("🏗️ 招投标助手系统")
    print("="*50)
    print("""
请选择功能：

1. 📄 解析文档（PDF/Word → Markdown）
2. 📚 构建知识库（Markdown → 向量索引）
3. 💬 RAG问答（基于知识库问答）
4. 📝 提取合同信息（单个PDF）
5. 📂 批量提取合同（文件夹）
6. 🎯 业绩智能匹配
7. 🔧 初始化数据库
0. 退出

""")
    return input("请输入选项 [0-7]: ").strip()


def interactive_mode():
    """交互模式"""
    while True:
        choice = show_menu()
        
        if choice == "0":
            print("👋 再见！")
            break
        
        elif choice == "1":
            file_path = input("请输入文档路径: ").strip()
            if file_path:
                try:
                    result = parse_document(file_path)
                    print(f"✅ 解析完成: {result}")
                except Exception as e:
                    print(f"❌ 解析失败: {e}")
        
        elif choice == "2":
            md_path = input("请输入Markdown文件路径: ").strip()
            if md_path:
                try:
                    build_index(md_path)
                except Exception as e:
                    print(f"❌ 构建失败: {e}")
        
        elif choice == "3":
            rag_chat()
        
        elif choice == "4":
            file_path = input("请输入合同PDF路径: ").strip()
            use_vision = input("使用视觉模型？(y/n, 默认y): ").strip().lower() != 'n'
            if file_path:
                try:
                    info = extract_contract(file_path, use_vision=use_vision)
                    print("\n📋 提取结果:")
                    for k, v in info.items():
                        if k != "db_id":
                            print(f"   {k}: {v}")
                except Exception as e:
                    print(f"❌ 提取失败: {e}")
        
        elif choice == "5":
            folder_path = input("请输入文件夹路径 (默认 ./documents/业绩): ").strip()
            if not folder_path:
                folder_path = "./documents/业绩"
            use_vision = input("使用视觉模型？(y/n, 默认y): ").strip().lower() != 'n'
            try:
                batch_extract(folder_path, use_vision=use_vision)
            except Exception as e:
                print(f"❌ 批量提取失败: {e}")
        
        elif choice == "6":
            requirement = input("请输入业绩要求 (留空进入交互模式): ").strip()
            match_performance(requirement if requirement else None)
        
        elif choice == "7":
            init_database()
        
        else:
            print("❌ 无效选项，请重新选择")
        
        input("\n按回车键继续...")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="招投标助手系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py                           # 交互模式
  python main.py parse 招标文件.docx        # 解析文档
  python main.py extract 合同.pdf          # 提取合同信息
  python main.py batch ./documents/业绩    # 批量提取
  python main.py match "近五年能源类业绩"   # 业绩匹配
  python main.py chat                      # RAG问答
  python main.py init-db                   # 初始化数据库
        """
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        choices=["parse", "index", "chat", "extract", "batch", "match", "init-db"],
        help="运行命令"
    )
    
    parser.add_argument(
        "path",
        nargs="?",
        help="文件或文件夹路径 / 业绩要求文本"
    )
    
    parser.add_argument(
        "--no-vision",
        action="store_true",
        help="不使用视觉模型（仅文本提取）"
    )
    
    args = parser.parse_args()
    
    # 无参数则进入交互模式
    if not args.command:
        interactive_mode()
        return
    
    # 命令行模式
    try:
        if args.command == "parse":
            if not args.path:
                print("❌ 请提供文件路径")
                return
            result = parse_document(args.path)
            print(f"✅ 解析完成: {result}")
        
        elif args.command == "index":
            if not args.path:
                print("❌ 请提供Markdown文件路径")
                return
            build_index(args.path)
        
        elif args.command == "chat":
            rag_chat()
        
        elif args.command == "extract":
            if not args.path:
                print("❌ 请提供PDF文件路径")
                return
            info = extract_contract(args.path, use_vision=not args.no_vision)
            print("\n📋 提取结果:")
            for k, v in info.items():
                if k != "db_id":
                    print(f"   {k}: {v}")
        
        elif args.command == "batch":
            path = args.path or "./documents/业绩"
            batch_extract(path, use_vision=not args.no_vision)
        
        elif args.command == "match":
            if args.path:
                match_performance(args.path)
            else:
                match_performance()
        
        elif args.command == "init-db":
            init_database()
    
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        raise


if __name__ == "__main__":
    main()
