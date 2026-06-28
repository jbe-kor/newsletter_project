import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import Settings


def send_summary_email(subject: str, body: str, settings: Settings) -> None:
    """요약 텍스트를 Gmail SMTP로 발송합니다."""
    msg = MIMEMultipart()
    msg["From"] = settings.smtp_email
    msg["To"] = settings.recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(settings.smtp_email, settings.smtp_password)
        server.sendmail(settings.smtp_email, settings.recipient_email, msg.as_string())


def build_email_subject() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return f"[반도체 브리프] {today} 뉴스 요약"
