import base64

from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.schemas.extraction import ExtractedInvoice
from app.services.llm.prompt import IMAGE_INSTRUCTION, SYSTEM_PROMPT, TEXT_INSTRUCTION

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def _parse(content: list[dict]) -> ExtractedInvoice:
    if client is None:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    completion = client.chat.completions.parse(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        response_format=ExtractedInvoice,
        temperature=0,
    )
    return completion.choices[0].message.parsed


def extract_from_text(text: str) -> ExtractedInvoice:
    return _parse([{"type": "text", "text": TEXT_INSTRUCTION.format(text=text)}])


def extract_from_images(images: list[bytes]) -> ExtractedInvoice:
    content = [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{base64.standard_b64encode(image).decode('utf-8')}"
            },
        }
        for image in images
    ]
    content.append({"type": "text", "text": IMAGE_INSTRUCTION})
    return _parse(content)
