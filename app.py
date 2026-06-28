import re
import os

from flask import Flask, jsonify, render_template, request

from database import add_subscriber, get_newsletter, init_db, unsubscribe
from main import BRAND_NAME, PREVIEW_COUNT, subscribe_and_send_welcome

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port, use_reloader=False)

