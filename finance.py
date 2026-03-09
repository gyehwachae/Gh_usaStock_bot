import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_quote(ticker: str) -> dict | None:
    """현재가, 등락률 반환 (5일 범위)"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval": "1d", "range": "5d"}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
        meta = result["meta"]
        quotes = result["indicators"]["quote"][0]

        closes = [c for c in quotes["close"] if c is not None]
        if len(closes) < 2:
            return None

        last_close = closes[-1]
        prev_close = closes[-2]
        change_pct = (last_close - prev_close) / prev_close * 100
        change_abs = last_close - prev_close

        return {
            "price": last_close,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "change_abs": change_abs,
            "currency": meta.get("currency", "USD"),
        }
    except Exception as e:
        print(f"[오류] {ticker}: {e}")
        return None


def get_stock_detail(ticker: str) -> dict | None:
    """52주 고저, 거래량 포함 상세 정보 반환 (1년 범위)"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval": "1d", "range": "1y"}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
        meta = result["meta"]
        quotes = result["indicators"]["quote"][0]

        closes = [c for c in quotes["close"] if c is not None]
        highs = [h for h in quotes.get("high", []) if h is not None]
        lows = [l for l in quotes.get("low", []) if l is not None]
        volumes = [v for v in quotes.get("volume", []) if v is not None]

        if len(closes) < 2:
            return None

        last_close = closes[-1]
        prev_close = closes[-2]
        change_pct = (last_close - prev_close) / prev_close * 100
        change_abs = last_close - prev_close

        return {
            "symbol": meta.get("symbol", ticker),
            "price": last_close,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "change_abs": change_abs,
            "week52_high": max(highs) if highs else None,
            "week52_low": min(lows) if lows else None,
            "volume": volumes[-1] if volumes else None,
            "currency": meta.get("currency", "USD"),
        }
    except Exception as e:
        print(f"[오류] {ticker}: {e}")
        return None


def get_usd_krw() -> float | None:
    """USD/KRW 환율 반환"""
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
