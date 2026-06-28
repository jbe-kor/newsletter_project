from pyngrok import ngrok

# 로컬 5000 포트를 ngrok으로 터널링
public_url = ngrok.connect(5000)
print(f"\n{'='*60}")
print(f"✅ 외부에서 접근 가능한 URL: {public_url.public_url}")
print(f"{'='*60}\n")
print("이 URL을 다른 사용자들에게 공유하세요!")
print("서버를 종료하려면 Ctrl+C를 누르세요.\n")

# 터널 유지
import time
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nngrok 터널을 종료합니다...")
    ngrok.disconnect(public_url.public_url)
