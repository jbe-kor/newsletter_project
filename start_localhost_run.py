import subprocess
import sys

# SSH로 localhost.run에 연결
cmd = [
    "ssh",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-R", "80:localhost:5000",
    "nokey@localhost.run"
]

print("\n" + "="*60)
print("localhost.run으로 터널을 연결하는 중...")
print("="*60 + "\n")
print("잠시 후 외부 접속 URL이 표시됩니다!")
print("서버를 종료하려면 Ctrl+C를 누르세요.\n")

try:
    # SSH 프로세스 실행
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # 출력 실시간으로 읽기
    for line in process.stdout:
        print(line, end='')
        
except KeyboardInterrupt:
    print("\n\n터널을 종료합니다...")
    process.terminate()
    sys.exit(0)
