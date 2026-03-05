import os
import requests
import yfinance as yf
from datetime import datetime
import pytz

# ──────────────────────────────────────────
# 설정
# ──────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

INDICES = {
    "S&P 500":   "^GSPC",
    "NASDAQ":    "^IXIC",
    "다우존스":   "^DJI",
}

STOCKS = {
    "VOO":               "VOO",
    "테슬라 (TSLA)":      "TSLA",
    "SCHD":              "SCHD",
    "QQQM":              "QQQM",
    "JEPQ":              "JEPQ",
    "애플 (AAPL)":        "AAPL",
    "알파벳A (GOOGL)":    "GOOGL",
    "메타 (META)":        "META",
    "마이크론 (MU)":      "MU",
}


# ──────────────────────────────────────────
# 데이터 수집
# ──────────────────────────────────────────
def get_quote(ticker: str) -> dict | None:
    """종목/지수의 전일 종가와 등락률을 반환합니다."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if len(hist) < 2:
            print(f"[경고] {ticker}: 데이터 부족 ({len(hist)}행)")
            return None
        prev_close = hist["Close"].iloc[-2]
        last_close = hist["Close"].iloc[-1]
        change_pct = (last_close - prev_close) / prev_close * 100
        return {"price": last_close, "change_pct": change_pct}
    except Exception as e:
        print(f"[오류] {ticker}: {e}")
        return None


def get_usd_krw() -> float | None:
    try:
        t = yf.Ticker("KRW=X")
        hist = t.history(period="5d")
        if hist.empty:
            print("[경고] KRW=X: 데이터 없음")
            return None
        return hist["Close"].iloc[-1]
    except Exception as e:
        print(f"[오류] KRW=X: {e}")
        return None


def get_fear_greed() -> dict | None:
    try:
        resp = requests.get("https://api.alternative.me/fng/", timeout=10)
        data = resp.json()["data"][0]
        return {"value": data["value"], "label": data["value_classification"]}
    except Exception:
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

    lines = [f"📊 *미국 증시 마감 현황*", f"_{now}_", ""]

    # 주요 지수
    lines.append("📈 *주요 지수*")
    for name, ticker in INDICES.items():
        q = get_quote(ticker)
        if q:
            a = arrow(q["change_pct"])
            lines.append(f"• {name}: {q['price']:,.2f}  {a} {fmt_change(q['change_pct'])}")
        else:
            lines.append(f"• {name}: 데이터 없음")

    lines.append("")

    # 주요 종목
    lines.append("💰 *주요 종목*")
    for name, ticker in STOCKS.items():
        q = get_quote(ticker)
        if q:
            a = arrow(q["change_pct"])
            lines.append(f"• {name}: ${q['price']:,.2f}  {a} {fmt_change(q['change_pct'])}")
        else:
            lines.append(f"• {name}: 데이터 없음")

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
