import requests

# 테스트할 URL
url = "http://192.168.2.2:8000/api/environment/status"

try:
    response = requests.get(url)
    print(f"상태 코드: {response.status_code}")
    print(f"응답 내용: {response.text}")
except Exception as e:
    print(f"오류 발생: {e}")