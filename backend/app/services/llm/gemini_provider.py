from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.schemas.extraction import ExtractedInvoice
from app.services.llm.prompt import IMAGE_INSTRUCTION, SYSTEM_PROMPT, TEXT_INSTRUCTION

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


def _parse(contents: list) -> ExtractedInvoice:
    if client is None:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ExtractedInvoice,
            temperature=0,
        ),
    )
    return ExtractedInvoice.model_validate_json(response.text)


def extract_from_text(text: str) -> ExtractedInvoice:
    return _parse([TEXT_INSTRUCTION.format(text=text)])


def extract_from_images(images: list[bytes]) -> ExtractedInvoice:
    contents = [types.Part.from_bytes(data=image, mime_type="image/png") for image in images]
    contents.append(IMAGE_INSTRUCTION)
    return _parse(contents)
