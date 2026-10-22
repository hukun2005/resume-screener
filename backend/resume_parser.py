"""简历文件文本提取（A3：支持 PDF / Word）"""
import io
import re

# 中国大陆手机号与邮箱正则（用于结构化抽取）
_PHONE_RE = re.compile(r"1[3-9]\d{9}")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


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


def extract_contact(text: str) -> dict:
    """从简历文本中抽取手机号与邮箱；姓名歧义较大，建议仍由人工填写。

    返回 {"phone": str, "email": str}，未命中则为空字符串。
    """
    if not text:
        return {"phone": "", "email": ""}
    phone_m = _PHONE_RE.search(text)
    email_m = _EMAIL_RE.search(text)
    return {
        "phone": phone_m.group(0) if phone_m else "",
        "email": email_m.group(0) if email_m else "",
    }