"""매일 구독자 전체에게 뉴스레터를 발송합니다. (작업 스케줄러 / cron용)"""

from database import get_active_subscribers, init_db
from main import build_newsletter, send_newsletter_email


def main() -> None:
    init_db()
    newsletter = build_newsletter()
    if not newsletter:
        print("발송할 뉴스가 없습니다.")
        return

    subscribers = get_active_subscribers()
    if not subscribers:
        print("활성 구독자가 없습니다.")
        return

    for subscriber in subscribers:
        send_newsletter_email(
            newsletter["summaries"],
            subscriber["email"],
            subscriber["token"],
            newsletter["date"],
        )

    print(f"{newsletter['date']} 뉴스레터 {len(subscribers)}명 발송 완료")


if __name__ == "__main__":
    main()
