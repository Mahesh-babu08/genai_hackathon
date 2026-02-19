import urllib.request
import json
import urllib.error

url = "http://127.0.0.1:8000/api/review"
data = {
    "code": "print('hello')",
    "language": "python",
    "focus_areas": ["bugs"],
    "calculate_score": True
}
headers = {'Content-Type': 'application/json'}

req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)

try:
    print(f"Sending request to {url}...")
    with urllib.request.urlopen(req) as response:
        print("Response code:", response.getcode())
        print("Response body:", response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}")
    print("Error body:", e.read().decode('utf-8'))
except Exception as e:
    print(f"Failed: {e}")
