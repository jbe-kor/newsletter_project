import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    smtp_email: str
    smtp_password: str
    recipient_email: str


def load_settings() -> Settings:
    required = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "SMTP_EMAIL": os.getenv("SMTP_EMAIL"),
        "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD"),
        "RECIPIENT_EMAIL": os.getenv("RECIPIENT_EMAIL"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f".env에 다음 값이 필요합니다: {', '.join(missing)}")

    return Settings(
        openai_api_key=required["OPENAI_API_KEY"],
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        smtp_email=required["SMTP_EMAIL"],
        smtp_password=required["SMTP_PASSWORD"],
        recipient_email=required["RECIPIENT_EMAIL"],
    )
