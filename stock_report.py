import os
import time
import requests
from datetime import datetime
import pytz

# ──────────────────────────────────────────
# 설정
# ──────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

INDICES = {
    "S&P 500":  "^GSPC",
    "NASDAQ":   "^IXIC",
    "다우존스":  "^DJI",
}

STOCKS = {
    "VOO":                "VOO",
    "테슬라 (TSLA)":       "TSLA",
    "SCHD":               "SCHD",
    "QQQM":               "QQQM",
    "JEPQ":               "JEPQ",
    "애플 (AAPL)":         "AAPL",
    "알파벳A (GOOGL)":     "GOOGL",
    "메타 (META)":         "META",
    "마이크론 (MU)":       "MU",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


# ──────────────────────────────────────────
# 데이터 수집
# ──────────────────────────────────────────
def get_quote(ticker: str) -> dict | None:
    """Yahoo Finance API로 종목/지수의 종가와 등락률을 반환합니다."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval": "1d", "range": "5d"}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        if len(closes) < 2:
            print(f"[경고] {ticker}: 데이터 부족")
            return None
        last_close = closes[-1]
        prev_close = closes[-2]
        change_pct = (last_close - prev_close) / prev_close * 100
        return {"price": last_close, "change_pct": change_pct}
    except Exception as e:
        print(f"[오류] {ticker}: {e}")
        return None


def get_usd_krw() -> float | None:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/KRW=X"
    params = {"interval": "1d", "range": "5d"}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        closes = resp.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        return closes[-1] if closes else None
    except Exception as e:
        print(f"[오류] KRW=X: {e}")
        return None


def get_fear_greed() -> dict | None:
    try:
        resp = requests.get("https://api.alternative.me/fng/", timeout=10)
        data = resp.json()["data"][0]
        return {"value": data["value"], "label": data["value_classification"]}
    except Exception as e:
        print(f"[오류] Fear&Greed: {e}")
        return None


# ──────────────────────────────────────────
# 메시지 생성
# ──────────────────────────────────────────
def arrow(change_pct: float) -> str:
    return "▲" if change_pct >= 0 else "▼"


def fmt_change(change_pct: float) -> str:
    sign = "+" if change_pct >= 0 else ""
    return f"{sign}{change_pct:.2f}%"


def build_message() -> str:
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst).strftime("%Y-%m-%d %H:%M KST")

    lines = ["📊 *미국 증시 마감 현황*", f"_{now}_", ""]

    # 주요 지수
    lines.append("📈 *주요 지수*")
    for name, ticker in INDICES.items():
        q = get_quote(ticker)
        if q:
            lines.append(f"• {name}: {q['price']:,.2f}  {arrow(q['change_pct'])} {fmt_change(q['change_pct'])}")
        else:
            lines.append(f"• {name}: 데이터 없음")
        time.sleep(0.5)

    lines.append("")

    # 주요 종목
    lines.append("💰 *주요 종목*")
    for name, ticker in STOCKS.items():
        q = get_quote(ticker)
        if q:
            lines.append(f"• {name}: ${q['price']:,.2f}  {arrow(q['change_pct'])} {fmt_change(q['change_pct'])}")
        else:
            lines.append(f"• {name}: 데이터 없음")
        time.sleep(0.5)

    lines.append("")

    # 공포탐욕지수
    lines.append("😱 *공포탐욕지수*")
    fg = get_fear_greed()
    if fg:
        lines.append(f"• Fear & Greed: {fg['value']} ({fg['label']})")
    else:
        lines.append("• 데이터 없음")

    lines.append("")

    # 환율
    lines.append("💱 *환율*")
    krw = get_usd_krw()
    if krw:
        lines.append(f"• USD/KRW: {krw:,.2f}원")
    else:
        lines.append("• 데이터 없음")

    return "\n".join(lines)


# ──────────────────────────────────────────
# 텔레그램 전송
# ──────────────────────────────────────────
def send_telegram(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    print("전송 완료!")


# ──────────────────────────────────────────
# 실행
# ──────────────────────────────────────────
if __name__ == "__main__":
    msg = build_message()
    print(msg)
    send_telegram(msg)
