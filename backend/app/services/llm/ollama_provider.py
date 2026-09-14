import ollama

from app.config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_VISION_MODEL
from app.schemas.extraction import ExtractedInvoice
from app.services.llm.prompt import IMAGE_INSTRUCTION, SYSTEM_PROMPT, TEXT_INSTRUCTION

client = ollama.Client(host=OLLAMA_HOST)


def _parse(model: str, content: str, images: list[bytes] | None = None) -> ExtractedInvoice:
    message = {"role": "user", "content": content}
    if images:
        message["images"] = images

    response = client.chat(
        model=model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, message],
        format=ExtractedInvoice.model_json_schema(),
        options={"temperature": 0},
    )
    return ExtractedInvoice.model_validate_json(response["message"]["content"])


def extract_from_text(text: str) -> ExtractedInvoice:
    return _parse(OLLAMA_MODEL, TEXT_INSTRUCTION.format(text=text))


def extract_from_images(images: list[bytes]) -> ExtractedInvoice:
    return _parse(OLLAMA_VISION_MODEL, IMAGE_INSTRUCTION, images=images)
