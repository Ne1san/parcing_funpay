"""Fetch public FunPay offers and save them as a static file for GitHub Pages."""

from __future__ import annotations

import json
import html
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_DIR = Path(__file__).resolve().parents[1]
LOTS_URL = "https://funpay.com/lots/1906/"


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", value))).strip()


def extract(pattern: str, value: str) -> str:
    match = re.search(pattern, value, re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else ""


def get_lots() -> list[dict[str, str]]:
    request = Request(LOTS_URL, headers={
        "User-Agent": "Mozilla/5.0 (compatible; FunPaySkinMonitor/1.0; +github-actions)",
        "Accept-Language": "ru-RU,ru;q=0.9",
    })
    try:
        with urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f"FunPay вернул HTTP {response.status}")
            page = response.read().decode("utf-8", errors="replace")
    except HTTPError as error:
        raise RuntimeError(f"FunPay вернул HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError("Не удалось подключиться к FunPay") from error

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
    if not lots:
        raise RuntimeError("FunPay не вернул карточки лотов")
    return lots


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_DIR / "public" / "lots.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "lots": get_lots(),
        "fetchedAt": datetime.now(UTC).isoformat(),
        "source": LOTS_URL,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Saved {len(payload['lots'])} lots to {output}")


if __name__ == "__main__":
    main()
