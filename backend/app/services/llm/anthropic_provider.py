import base64

import anthropic

from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from app.schemas.extraction import ExtractedInvoice
from app.services.llm.prompt import IMAGE_INSTRUCTION, SYSTEM_PROMPT, TEXT_INSTRUCTION

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


def _parse(content: list[dict]) -> ExtractedInvoice:
    if client is None:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    response = client.messages.parse(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
        output_format=ExtractedInvoice,
    )
    return response.parsed_output


def extract_from_text(text: str) -> ExtractedInvoice:
    return _parse([{"type": "text", "text": TEXT_INSTRUCTION.format(text=text)}])


def extract_from_images(images: list[bytes]) -> ExtractedInvoice:
    content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": base64.standard_b64encode(image).decode("utf-8"),
            },
        }
        for image in images
    ]
    content.append({"type": "text", "text": IMAGE_INSTRUCTION})
    return _parse(content)
