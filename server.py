from __future__ import annotations

import html
import json
import os
import re
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PORT = int(os.getenv("PORT", "3000"))
LOTS_URL = "https://funpay.com/lots/1906/"
PUBLIC_DIR = Path(__file__).parent / "public"


def clean(value: str) -> str:
    """Remove nested markup and normalise text from a FunPay card."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", value))).strip()


def extract(pattern: str, value: str) -> str:
    match = re.search(pattern, value, re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else ""


def parse_lots(page: str) -> list[dict[str, str]]:
    # Every offer is an <a class="tc-item ..."> card; it does not contain nested links.
    cards = re.findall(r'<a\b[^>]*\bclass="[^"]*\btc-item\b[^"]*"[^>]*>[\s\S]*?</a>', page, re.IGNORECASE)
    lots = []
    for card in cards[:30]:
        lot = {
            "description": clean(extract(r'<div\s+class="tc-desc-text">(.*?)</div>', card)),
            "seller": clean(extract(r'<div\s+class="media-user-name">\s*(.*?)\s*</div>', card)),
            "price": clean(extract(r'<div\s+class="tc-price"[^>]*>\s*<div>(.*?)</div>', card)),
            "url": extract(r'href="([^"]+)"', card),
        }
        if all(lot.values()):
            lots.append(lot)
    return lots


def get_lots() -> list[dict[str, str]]:
    request = Request(LOTS_URL, headers={
        "User-Agent": "Mozilla/5.0 (compatible; FunPaySkinMonitor/1.0; +local)",
        "Accept-Language": "ru-RU,ru;q=0.9",
    })
    try:
        with urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f"FunPay вернул HTTP {response.status}")
            lots = parse_lots(response.read().decode("utf-8", errors="replace"))
    except HTTPError as error:
        raise RuntimeError(f"FunPay вернул HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError("Не удалось подключиться к FunPay") from error

    if not lots:
        raise RuntimeError("Не удалось найти карточки лотов. Возможно, FunPay изменил разметку или запрос заблокирован.")
    return lots


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def do_GET(self):
        if self.path.split("?", 1)[0] != "/api/lots":
            return super().do_GET()
        try:
            self.send_json(HTTPStatus.OK, {"lots": get_lots(), "source": LOTS_URL})
        except RuntimeError as error:
            self.send_json(HTTPStatus.BAD_GATEWAY, {"error": str(error)})

    def send_json(self, status: HTTPStatus, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        print(f"{self.address_string()} — {format % args}")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), AppHandler)
    print(f"Skin Pulse запущен: http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
