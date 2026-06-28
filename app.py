import os
import traceback
from flask import Flask, render_template, request, jsonify

from database import add_subscriber, get_cached_newsletter as get_newsletter, init_db
from main import BRAND_NAME, PREVIEW_COUNT, subscribe_and_send_welcome

app = Flask(__name__)
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")

# 초기화
init_db()


@app.get("/")
def index():
    return render_template("index.html", brand_name=BRAND_NAME)


@app.post("/subscribe")
def subscribe():
    email = request.form.get("email")
    if not email:
        return render_template("index.html", error="이메일을 입력해주세요.", brand_name=BRAND_NAME)

    try:
        subscriber = add_subscriber(email)
        subscribe_and_send_welcome(email, subscriber.unsubscribe_token)
        return render_template("index.html", success="구독이 완료되었습니다! 메일을 확인해주세요.", brand_name=BRAND_NAME)
    except Exception as e:
        error_msg = f"구독 처리 중 오류: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return render_template("index.html", error=error_msg, brand_name=BRAND_NAME)


@app.get("/newsletter/<date_str>")
def newsletter(date_str):
    cached = get_newsletter(date_str)
    if not cached:
        return "뉴스레터를 찾을 수 없습니다.", 404

    import json
    summaries = json.loads(cached.summaries_json)
    return render_template("newsletter.html", summaries=summaries[:PREVIEW_COUNT], more_summaries=summaries[PREVIEW_COUNT:], date_str=date_str, brand_name=BRAND_NAME, base_url=BASE_URL)


@app.get("/unsubscribe/<token>")
def unsubscribe_page(token):
    from database import get_subscriber_by_token, unsubscribe
    subscriber = get_subscriber_by_token(token)
    if not subscriber:
        return "유효하지 않은 토큰입니다.", 404

    unsubscribed = unsubscribe(token)
    return render_template("unsubscribe.html", success=unsubscribed, brand_name=BRAND_NAME)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))