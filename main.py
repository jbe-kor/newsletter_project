import html

import json

import os

import smtplib

from datetime import date, datetime, timedelta

from email.mime.multipart import MIMEMultipart

from email.mime.text import MIMEText

from zoneinfo import ZoneInfo



import feedparser

from dotenv import load_dotenv

from google import genai



from database import get_cached_newsletter as get_newsletter, cache_newsletter as save_newsletter


KST = ZoneInfo("Asia/Seoul")

BRAND_NAME = "Today's Transistor news"

PREVIEW_COUNT = 5



load_dotenv()



GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SENDER_EMAIL = os.getenv("SENDER_EMAIL")

SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000").rstrip("/")





def _yesterday_kst() -> date:

    return (datetime.now(KST) - timedelta(days=1)).date()





def _entry_published_date(entry) -> date | None:

    for key in ("published_parsed", "updated_parsed"):

        parsed = entry.get(key)

        if parsed:

            dt_utc = datetime(*parsed[:6], tzinfo=ZoneInfo("UTC"))

            return dt_utc.astimezone(KST).date()

    return None





def fetch_semiconductor_news() -> list[dict]:

    """구글 뉴스 RSS에서 전날(KST) 게시된 반도체 뉴스만 수집"""

    target_date = _yesterday_kst()

    print(f"[INFO] {target_date} 게시 반도체 뉴스를 수집하는 중...")

    rss_url = "https://news.google.com/rss/search?q=반도체+공정+OR+TSMC+OR+HBM&hl=ko&gl=KR&ceid=KR:ko"

    feed = feedparser.parse(rss_url)



    news_list = []

    seen_links: set[str] = set()

    for entry in feed.entries:

        published_date = _entry_published_date(entry)

        if published_date != target_date:

            continue



        link = entry.get("link", "").strip()

        title = entry.get("title", "").strip()

        if not link or not title or link in seen_links:

            continue



        seen_links.add(link)

        news_list.append({"title": title, "link": link, "published": str(published_date)})

        if len(news_list) >= 10:
            break



    print(f"  → {len(news_list)}건 수집")

    return news_list





def _parse_json_response(text: str) -> list[dict]:

    cleaned = text.strip()

    if cleaned.startswith("```"):

        cleaned = cleaned.split("\n", 1)[1]

        cleaned = cleaned.rsplit("```", 1)[0].strip()

    return json.loads(cleaned)





def summarize_with_gemini(news_entries: list[dict]) -> list[dict]:

    """Gemini API를 사용하여 뉴스 요약 및 인사이트 래핑"""

    print("[INFO] Gemini AI가 반도체 전문 엔지니어 관점으로 요약 중...")

    client = genai.Client(api_key=GEMINI_API_KEY)



    news_content = "\n\n".join(

        f"제목: {entry['title']}\n링크: {entry['link']}" for entry in news_entries

    )



    prompt = f"""
    너는 세계 최고의 반도체 소자 및 공정 엔지니어이자 직무 멘토야.
    아래 입력된 최신 뉴스 데이터들을 보고, 다른 엔지니어가 출근길에 가볍고 명확하게 읽을 수 있도록 요약해줘.

    [출력 형식]
    반드시 JSON 배열만 출력하세요. 마크다운이나 설명 문구 없이 JSON만:
    [
      {{
        "headline": "뉴스 헤드라인 (짧고 임팩트 있게)",
        "fact": "팩트: 무슨 일이 있었는지 객관적 사실 1줄",
        "background": "배경: 이 기술/이슈가 등장한 맥락과 배경 1줄",
        "impact": "시사점: 이 사건이 산업·기술·시장에 미치는 의미와 향후 전망 1줄"
      }}
    ]

    * 주의: 전문 기술 용어가 나오면 아주 짧은 주석을 달아줄 것.
    * 입력된 뉴스 개수만큼 JSON 객체를 만들 것.
    * 절대 마크다운 코드 블록(```json ```)으로 감싸지 마세요!
    * 문자열 안에 따옴표(")가 있으면 역슬래시로 이스케이프 처리해 주세요! (예: \")
    * JSON만 반환하고, 아무 다른 텍스트도 넣지 마세요!

    [뉴스 데이터]
    {news_content}
    """



    response = client.models.generate_content(

        model="gemini-2.5-flash",

        contents=prompt,

    )

    summaries = _parse_json_response(response.text)



    for summary, entry in zip(summaries, news_entries):

        summary["link"] = entry["link"]



    return summaries





def build_newsletter() -> dict | None:

    """뉴스를 수집·요약하고 DB에 저장합니다."""

    news_date = str(_yesterday_kst())

    cached = get_newsletter(news_date)
    if cached:
        summaries_json = cached.summaries_json
        summaries = json.loads(summaries_json)
        return {"date": news_date, "summaries": summaries}



    news_data = fetch_semiconductor_news()

    if not news_data:

        return None



    summaries = summarize_with_gemini(news_data)

    save_newsletter(news_date, json.dumps(summaries))

    return {"date": news_date, "summaries": summaries}





def _build_item_html(item: dict) -> str:

    headline = html.escape(item["headline"])

    link = html.escape(item["link"], quote=True)

    fact = html.escape(item["fact"])

    background = html.escape(item["background"])

    impact = html.escape(item["impact"])



    return f"""

    <div style="margin-bottom: 28px;">

      <a href="{link}" style="text-decoration: none; display: block;">

        <div style="border: 2px solid #EA002C; border-radius: 10px; padding: 18px 20px; background: #fff0f0;">

          <p style="margin: 0; font-size: 22px; font-weight: 700; color: #EA002C; line-height: 1.45;">

            {headline}

          </p>

        </div>

      </a>

      <ul style="margin: 14px 0 0 0; padding: 0; list-style: none; font-size: 15px; line-height: 1.75; color: #334155;">
        <li style="margin-bottom: 10px;">&#8226; <strong>팩트</strong> &mdash; {fact}</li>
        <li style="margin-bottom: 10px;">&#8226; <strong>배경</strong> &mdash; {background}</li>
        <li style="margin-bottom: 0;">&#8226; <strong>시사점</strong> &mdash; {impact}</li>
      </ul>

    </div>

    """





def build_html_report(

    summaries: list[dict],

    news_date: str,

    unsubscribe_url: str | None = None,

    view_all_url: str | None = None,

) -> str:

    today = datetime.now(KST).strftime("%Y-%m-%d")

    preview = summaries[:PREVIEW_COUNT]

    total = len(summaries)

    items_html = [_build_item_html(item) for item in preview]



    view_all_section = ""

    if total > PREVIEW_COUNT and view_all_url:

        safe_url = html.escape(view_all_url, quote=True)

        view_all_section = f"""

        <div style="text-align: center; margin: 8px 0 24px;">

          <a href="{safe_url}"

             style="display: inline-block; padding: 14px 28px; background: linear-gradient(90deg, #EA002C 0%, #F47725 100%); color: #ffffff;

                    text-decoration: none; border-radius: 10px; font-weight: 700; font-size: 15px;">

            전체 보기 ({total}건)

          </a>

        </div>

        """



    unsubscribe_section = ""

    if unsubscribe_url:

        safe_unsub = html.escape(unsubscribe_url, quote=True)

        unsubscribe_section = f"""

        <p style="margin: 20px 0 0; text-align: center; font-size: 13px; color: #64748b;">

          <a href="{safe_unsub}"

             style="display: inline-block; padding: 10px 18px; border: 1px solid #cbd5e1;

                    border-radius: 8px; color: #64748b; text-decoration: none;">

            구독 취소

          </a>

        </p>

        """



    return f"""

    <html>

      <body style="margin: 0; padding: 24px; background: linear-gradient(160deg, #fff0f0 0%, #fff5eb 45%, #fffaf0 100%); font-family: 'Malgun Gothic', Arial, sans-serif;">

        <div style="max-width: 640px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 36px; box-shadow: 0 2px 8px rgba(234, 0, 44, 0.12); border: 2px solid #fff0f0;">

          <div style="border-left: 5px solid #EA002C; padding-left: 14px; margin-bottom: 28px;">

            <p style="margin: 0; font-size: 13px; color: #64748b; letter-spacing: 0.5px;">{BRAND_NAME} · {today}</p>

            <h1 style="margin: 6px 0 0 0; font-size: 26px; color: #EA002C;">{BRAND_NAME}</h1>

            <p style="margin: 8px 0 0 0; font-size: 14px; color: #64748b;">{news_date} 게시 기사 기준 · {min(PREVIEW_COUNT, total)} / {total}건 미리보기</p>

          </div>

          {''.join(items_html)}

          {view_all_section}

          <p style="margin: 0; padding-top: 16px; border-top: 1px solid #fff0f0; font-size: 12px; color: #94a3b8; text-align: center;">

            &#9656; {BRAND_NAME} 자동 리포트

          </p>

          {unsubscribe_section}

        </div>

      </body>

    </html>

    """





def build_plain_report(

    summaries: list[dict],

    news_date: str,

    unsubscribe_url: str | None = None,

    view_all_url: str | None = None,

) -> str:

    preview = summaries[:PREVIEW_COUNT]

    lines = [

        f"[{BRAND_NAME}]",

        f"({news_date} 게시 기사 기준)",

        "",

    ]

    for item in preview:

        lines.extend(
            [
                f"■ {item['headline']}",
                f"  링크: {item['link']}",
                f"  • 팩트 — {item['fact']}",
                f"  • 배경 — {item['background']}",
                f"  • 시사점 — {item['impact']}",
                "",
            ]
        )



    if len(summaries) > PREVIEW_COUNT and view_all_url:

        lines.append(f"전체 {len(summaries)}건 보기: {view_all_url}")

        lines.append("")



    if unsubscribe_url:

        lines.append(f"구독 취소: {unsubscribe_url}")



    return "\n".join(lines)





def send_newsletter_email(
    summaries: list[dict],
    recipient_email: str,
    unsubscribe_token: str | None = None,
    news_date: str | None = None,
) -> None:
    """요약된 리포트를 HTML 이메일로 발송"""
    import os
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, HtmlContent, PlainTextContent

    news_date = news_date or str(_yesterday_kst())
    unsubscribe_url = (
        f"{BASE_URL}/unsubscribe/{unsubscribe_token}" if unsubscribe_token else None
    )
    view_all_url = f"{BASE_URL}/newsletter/{news_date}"

    print(f"[INFO] {recipient_email} 로 {BRAND_NAME} 발송 중...")
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

    message = Mail(
        from_email=SENDER_EMAIL,
        to_emails=recipient_email,
        subject=f"{BRAND_NAME}",
        plain_text_content=PlainTextContent(build_plain_report(summaries, news_date, unsubscribe_url, view_all_url)),
        html_content=HtmlContent(build_html_report(summaries, news_date, unsubscribe_url, view_all_url))
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"[SUCCESS] 이메일 발송 성공! Status code: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] 이메일 발송 실패: {str(e)}")
        raise





def subscribe_and_send_welcome(email: str, token: str) -> dict:

    """구독 등록 후 첫 뉴스레터를 발송합니다."""

    newsletter = build_newsletter()

    if not newsletter:

        return {

            "success": True,

            "subscribed": True,

            "sent": False,

            "message": (

                f"구독이 완료되었습니다. "

                f"{_yesterday_kst()} 게시 뉴스가 없어 오늘은 발송하지 않았으며, "

                f"내일부터 매일 {BRAND_NAME}를 받게 됩니다."

            ),

        }



    send_newsletter_email(

        newsletter["summaries"],

        email,

        token,

        newsletter["date"],

    )

    return {

        "success": True,

        "subscribed": True,

        "sent": True,

        "message": (

            f"구독 완료! {email} 로 오늘자 {BRAND_NAME} {len(newsletter['summaries'])}건을 발송했으며, "

            f"앞으로 매일 아침 뉴스레터를 받게 됩니다."

        ),

        "count": len(newsletter["summaries"]),

        "date": newsletter["date"],

    }





def run_newsletter(recipient_email: str, unsubscribe_token: str | None = None) -> dict:

    """뉴스 수집 → 요약 → 이메일 발송 파이프라인 (단건 발송용)"""

    newsletter = build_newsletter()

    if not newsletter:

        return {

            "success": False,

            "message": f"{_yesterday_kst()} 게시된 뉴스가 없습니다.",

        }



    send_newsletter_email(

        newsletter["summaries"],

        recipient_email,

        unsubscribe_token,

        newsletter["date"],

    )

    return {

        "success": True,

        "message": f"{recipient_email} 로 뉴스레터 {len(newsletter['summaries'])}건을 발송했습니다.",

        "count": len(newsletter["summaries"]),

        "date": newsletter["date"],

    }





if __name__ == "__main__":

    result = run_newsletter(RECEIVER_EMAIL)

    if not result["success"]:

        print(f"[ERROR] {result['message']}")


