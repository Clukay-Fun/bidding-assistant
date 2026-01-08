"""
招投标助手 - 文档解析主入口
功能：自动识别文件类型，统一输出Markdown
"""

from pathlib import Path
import sys

# ============================================
# region 文件类型处理
# ============================================

def process_file(file_path: str) -> str:
    """
    自动识别文件类型并处理
    
    支持格式:
        .docx → MarkItDown
        .pdf  → PaddleOCR
    
    返回:
        输出的Markdown文件路径
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    suffix = file_path.suffix.lower()
    
    print("\n" + "="*50)
    print("🚀 招投标文档解析")
    print("="*50)
    print(f"📁 输入文件: {file_path}")
    print(f"📋 文件类型: {suffix}")
    
    if suffix == '.docx':
        from docx_to_markdown import docx_to_markdown
        return docx_to_markdown(str(file_path))
    
    elif suffix == '.pdf':
        from ocr_parser import pdf_to_markdown
        return pdf_to_markdown(str(file_path))
    
    else:
        raise ValueError(f"不支持的文件格式: {suffix}，仅支持 .docx 和 .pdf")

# endregion
# ============================================


# ============================================
# region 批量处理
# ============================================

def process_folder(folder_path: str) -> list:
    """
    批量处理文件夹中的所有文档
    
    返回:
        输出文件路径列表
    """
    folder = Path(folder_path)
    
    if not folder.is_dir():
        raise NotADirectoryError(f"不是有效的文件夹: {folder}")
    
    # 支持的文件格式
    supported = ['.docx', '.pdf']
    files = [f for f in folder.iterdir() if f.suffix.lower() in supported]
    
    print(f"\n📂 发现 {len(files)} 个待处理文件")
    
    results = []
    for i, file in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] 处理中...")
        try:
            output = process_file(str(file))
            results.append({"file": str(file), "output": output, "status": "success"})
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            results.append({"file": str(file), "error": str(e), "status": "failed"})
    
    # 统计结果
    success = len([r for r in results if r["status"] == "success"])
    failed = len([r for r in results if r["status"] == "failed"])
    
    print("\n" + "="*50)
    print(f"📊 处理完成: 成功 {success} 个，失败 {failed} 个")
    print("="*50)
    
    return results

# endregion
# ============================================


if __name__ == "__main__":
    # 示例：处理单个文件
    # process_file("template/采购文件.docx")
    # process_file("街道服务业绩20260106.pdf")
    
    # 示例：批量处理文件夹
    # process_folder("./documents")
    
    # 命令行模式
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if Path(path).is_dir():
            process_folder(path)
        else:
            process_file(path)
    else:
        print("用法:")
        print("  python main.py <文件路径>      # 处理单个文件")
        print("  python main.py <文件夹路径>    # 批量处理")