"""
Word文档转Markdown
功能：使用 MarkItDown 将Word文档（含表格）转换为Markdown格式
"""

from pathlib import Path
from markitdown import MarkItDown
import time

# ============================================
# region 配置区域
# 输出目录
OUTPUT_DIR = Path("./output")
OUTPUT_DIR.mkdir(exist_ok=True)
# endregion
# ============================================

# ============================================
# region Word转Markdown主函数
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
    test_file = "template/采购文件.docx"
    docx_to_markdown(test_file)
