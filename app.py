import re
import os

from flask import Flask, jsonify, render_template, request

from database import add_subscriber, get_newsletter, init_db, unsubscribe, get_active_subscribers
from main import BRAND_NAME, PREVIEW_COUNT, subscribe_and_send_welcome, build_newsletter, send_newsletter_email

app = Flask(__name__)

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

init_db()


@app.get("/")
def index():
    return render_template("index.html", brand_name=BRAND_NAME)


@app.post("/subscribe")
@app.post("/send")
def subscribe():
    email = request.form.get("email", "").strip().lower()
    if not EMAIL_PATTERN.match(email):
        return jsonify({"success": False, "message": "올바른 이메일 주소를 입력해 주세요."}), 400

    try:
        token, _is_new = add_subscriber(email)
        result = subscribe_and_send_welcome(email, token)
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"success": False, "message": f"구독 처리 중 오류: {exc}"}), 500


@app.get("/newsletter/<news_date>")
def newsletter_view(news_date: str):
    summaries = get_newsletter(news_date)
    if not summaries:
        return render_template(
            "newsletter.html",
            brand_name=BRAND_NAME,
            news_date=news_date,
            summaries=[],
            preview_count=PREVIEW_COUNT,
            not_found=True,
        ), 404

    return render_template(
        "newsletter.html",
        brand_name=BRAND_NAME,
        news_date=news_date,
        summaries=summaries,
        preview_count=PREVIEW_COUNT,
        not_found=False,
    )


@app.get("/unsubscribe/<token>")
def unsubscribe_view(token: str):
    email = unsubscribe(token)
    return render_template(
        "unsubscribe.html",
        brand_name=BRAND_NAME,
        success=email is not None,
        email=email,
    )


@app.post("/send-daily")
def send_daily():
    """매일 정해진 시간에 호출되어 모든 구독자에게 뉴스레터를 발송합니다."""
    # 간단한 인증 (환경변수로 비밀번호 설정 권장)
    auth_header = request.headers.get("Authorization")
    SECRET_KEY = os.environ.get("CRON_SECRET", "your-secret-key-change-this")
    
    if auth_header != f"Bearer {SECRET_KEY}":
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        newsletter = build_newsletter()
        if not newsletter:
            return jsonify({"success": True, "message": "발송할 뉴스가 없습니다."})
        
        subscribers = get_active_subscribers()
        if not subscribers:
            return jsonify({"success": True, "message": "활성 구독자가 없습니다."})
        
        for subscriber in subscribers:
            send_newsletter_email(
                newsletter["summaries"],
                subscriber["email"],
                subscriber["token"],
                newsletter["date"],
            )
        
        return jsonify({
            "success": True,
            "message": f"{newsletter['date']} 뉴스레터 {len(subscribers)}명 발송 완료"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port, use_reloader=False)

