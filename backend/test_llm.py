
import json
import urllib.request
import urllib.error
import socket
from app.core.config import load_settings

s = load_settings()
url = s.llm_base_url.rstrip("/") + "/chat/completions"

payload = {
    "model": s.llm_model,
    "messages": [
        {"role": "user", "content": "Reply only: OK"}
    ],
    "max_tokens": 10,
    "reasoning_effort": "low"
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": "Bearer " + s.llm_api_key,
        "Content-Type": "application/json",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read())
    print("SUCCESS:", data["choices"][0]["message"]["content"])
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)
    print(e.read().decode("utf-8", errors="replace")[:2000])
except (TimeoutError, socket.timeout):
    print("TIMEOUT: Chat generation did not respond within 30 seconds.")
except Exception as e:
    print(type(e).__name__ + ":", str(e))

