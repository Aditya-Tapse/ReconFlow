import fitz


def extract_text(file_path: str) -> str:
    with fitz.open(file_path) as doc:
        return "\n".join(page.get_text() for page in doc)


def render_pages_as_png(file_path: str, max_pages: int) -> list[bytes]:
    images = []
    with fitz.open(file_path) as doc:
        for page in doc[:max_pages]:
            pixmap = page.get_pixmap(dpi=200)
            images.append(pixmap.tobytes("png"))
    return images
