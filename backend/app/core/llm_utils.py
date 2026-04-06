def content_to_text(content: object) -> str:
    """Parse LangChain response content (str or list of str/dict) into a plain string."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return " ".join(part.strip() for part in parts if part and part.strip()).strip()
    return ""


def chunk_to_text(content: object) -> str:
    """Extract raw text from an AIMessageChunk's content without stripping whitespace."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "".join(parts)
    return ""
