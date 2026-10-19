"""简历文件文本提取（A3：支持 PDF / Word）"""
import io


def extract_resume_text(content: bytes, filename: str) -> str:
    """从上传的 PDF / DOCX 中提取纯文本，失败或无法识别返回空字符串"""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError:
            return ""
        reader = PdfReader(io.BytesIO(content))
        parts = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(p for p in parts if p).strip()
    if name.endswith(".docx"):
        try:
            import docx
        except ImportError:
            return ""
        doc = docx.Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text).strip()
    # 纯文本兜底（.txt 等）
    try:
        return content.decode("utf-8").strip()
    except Exception:
        return ""