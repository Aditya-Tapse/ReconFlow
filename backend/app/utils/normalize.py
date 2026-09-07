import re

NOISE_WORDS = {"private", "limited", "pvt", "ltd", "llc", "inc", "co", "company"}


def normalize_vendor_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", name.lower())
    tokens = [t for t in cleaned.split() if t not in NOISE_WORDS]
    return " ".join(tokens).strip()
