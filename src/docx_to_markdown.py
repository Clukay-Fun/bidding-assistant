"""
Word文档转Markdown
功能：使用 MarkItDown 将Word文档转换为Markdown格式
"""

from pathlib import Path
from markitdown import MarkItDown
import time
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import OUTPUT_DIR


# ============================================
# region Word转Markdown
# ============================================

def docx_to_markdown(docx_path: str, output_path: str = None) -> str:
    """
    将Word文档转换为Markdown

    参数:
        docx_path: Word文件路径
        output_path: 输出路径（可选，不传则自动生成）

    返回:
        Markdown文件路径
    """
    start_time = time.time()
    print(f"📄 正在转换: {docx_path}")

    # 初始化 MarkItDown 转换器
    md = MarkItDown()

    # 转换文档
    result = md.convert(docx_path)

    # 生成输出路径
    if output_path is None:
        source_name = Path(docx_path).stem
        output_path = OUTPUT_DIR / f"{source_name}.md"

    # 保存文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result.text_content)

    elapsed = time.time() - start_time
    print(f"✅ 转换完成: {output_path}")
    print(f"⏱️ 耗时: {elapsed:.2f} 秒")

    return str(output_path)

# endregion
# ============================================


if __name__ == "__main__":
    if len(sys.argv) > 1:
        docx_to_markdown(sys.argv[1])
    else:
        print("用法: python -m src.docx_to_markdown <Word文件路径>")
