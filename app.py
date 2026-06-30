import re
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

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
@app.post("/send")
def subscribe():
    email = request.form.get("email", "").strip().lower()
    if not EMAIL_PATTERN.match(email):
        return jsonify({"success": False, "message": "올바른 이메일 주소를 입력해 주세요."}), 400

    try:
        subscriber = add_subscriber(email)
        result = subscribe_and_send_welcome(email, subscriber.unsubscribe_token)
        return jsonify(result), 200
    except Exception as exc:
        print("="*50)
        print("ERROR OCCURRED:")
        traceback.print_exc()
        print("="*50)
        
        error_msg = str(exc)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return jsonify({
                "success": False,
                "message": "현재 AI 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
            }), 429
        
        return jsonify({"success": False, "message": f"구독 처리 중 오류: {exc}"}), 500


@app.get("/newsletter/<date_str>")
def newsletter(date_str):
    cached = get_newsletter(date_str)
    if not cached:
        return "뉴스레터를 찾을 수 없습니다.", 404

    import json
    summaries = json.loads(cached.summaries_json)
    return render_template("newsletter.html", summaries=summaries, news_date=date_str, preview_count=PREVIEW_COUNT, brand_name=BRAND_NAME, base_url=BASE_URL)


@app.get("/unsubscribe/<token>")
def unsubscribe_page(token):
    from database import get_subscriber_by_token, unsubscribe
    subscriber = get_subscriber_by_token(token)
    if not subscriber:
        return "유효하지 않은 토큰입니다.", 404

    unsubscribed = unsubscribe(token)
    return render_template("unsubscribe.html", success=unsubscribed, brand_name=BRAND_NAME, email=subscriber.email)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))