import json
import os
import time
from collections import defaultdict
from datetime import datetime

import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from finance import get_quote, get_stock_detail, get_usd_krw

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

with open("portfolio.json", encoding="utf-8") as f:
    PORTFOLIO_LOTS = json.load(f)

# 한국어 이름 → Yahoo Finance 티커 매핑
ALIASES: dict[str, str] = {
    "삼성전자":   "005930.KS",
    "삼성전자우":  "005935.KS",
    "현대차2우b": "005387.KS",
    "현대차2우B": "005387.KS",
    "현대차":     "005380.KS",
    "우리금융":   "316140.KS",
    "우리금융지주": "316140.KS",
    "애플":   "AAPL",
    "알파벳":  "GOOGL",
    "구글":    "GOOGL",
    "메타":   "META",
    "페이스북": "META",
    "마이크론": "MU",
    "엔비디아": "NVDA",
    "테슬라":  "TSLA",
    "아마존":  "AMZN",
    "마이크로소프트": "MSFT",
}


# ── 헬퍼 ──────────────────────────────────────────────────
def arrow(pct: float) -> str:
    return "▲" if pct >= 0 else "▼"


def fmt_pct(pct: float) -> str:
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"


def now_kst() -> str:
    kst = pytz.timezone("Asia/Seoul")
    return datetime.now(kst).strftime("%Y-%m-%d %H:%M KST")


# ── 명령어 핸들러 ─────────────────────────────────────────
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📊 *주식 포트폴리오 봇*\n\n"
        "*명령어*\n"
        "/portfolio \\- 포트폴리오 전체 현황\n"
        "/stock \\[티커\\] \\- 종목 분석\n\n"
        "*예시*\n"
        "/stock TSLA\n"
        "/stock 삼성전자\n"
        "/stock AAPL"
    )
    await update.message.reply_text(text, parse_mode="MarkdownV2")


async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ 포트폴리오 데이터 조회 중...")

    usd_krw = get_usd_krw() or 1450.0

    # 종목별 lot 합산
    agg: dict[str, dict] = defaultdict(lambda: {
        "name": "", "ticker": "", "currency": "", "qty": 0.0, "investment_krw": 0.0
    })
    for lot in PORTFOLIO_LOTS:
        key = lot["ticker"]
        agg[key]["name"] = lot["name"]
        agg[key]["ticker"] = lot["ticker"]
        agg[key]["currency"] = lot["currency"]
        agg[key]["qty"] += lot["quantity"]
        agg[key]["investment_krw"] += lot["investment_krw"]

    kr_lines, us_lines = [], []
    total_investment = 0.0
    total_evaluation = 0.0

    for ticker, item in agg.items():
        q = get_quote(ticker)
        time.sleep(0.3)
        if not q:
            continue

        qty = item["qty"]
        investment = item["investment_krw"]
        total_investment += investment

        if item["currency"] == "KRW":
            price_krw = q["price"]
            price_str = f"{price_krw:,.0f}원"
        else:
            price_krw = q["price"] * usd_krw
            price_str = f"${q['price']:,.2f}"

        evaluation = price_krw * qty
        total_evaluation += evaluation

        pnl = evaluation - investment
        pnl_pct = pnl / investment * 100 if investment else 0.0
        sign = "+" if pnl >= 0 else ""
        ar = arrow(q["change_pct"])

        line = (
            f"• {item['name']} {qty:g}주\n"
            f"  {price_str} {ar}{fmt_pct(q['change_pct'])} | 손익 {sign}{pnl_pct:.2f}%"
        )

        if item["currency"] == "KRW":
            kr_lines.append(line)
        else:
            us_lines.append(line)

    total_pnl = total_evaluation - total_investment
    total_pnl_pct = total_pnl / total_investment * 100 if total_investment else 0.0
    total_sign = "+" if total_pnl >= 0 else ""

    lines = [
        f"📊 *포트폴리오 현황*",
        f"_{now_kst()}_",
        f"💱 환율: {usd_krw:,.2f}원/USD",
        "",
        f"💰 총 투자: {total_investment:,.0f}원",
        f"📈 총 평가: {total_evaluation:,.0f}원",
        f"{arrow(total_pnl_pct)} 총 손익: {total_sign}{total_pnl:,.0f}원 ({total_sign}{total_pnl_pct:.2f}%)",
        "",
        "━━━ 🇰🇷 한국주식 ━━━",
        *kr_lines,
        "",
        "━━━ 🇺🇸 미국주식 ━━━",
        *us_lines,
    ]

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "사용법: /stock [티커]\n예) /stock TSLA, /stock 삼성전자"
        )
        return

    query = " ".join(context.args)
    ticker = ALIASES.get(query) or ALIASES.get(query.lower()) or query.upper()

    await update.message.reply_text(f"⏳ {ticker} 분석 중...")

    d = get_stock_detail(ticker)
    if not d:
        await update.message.reply_text(f"❌ {ticker} 데이터를 가져올 수 없습니다.\n티커 심볼을 확인해 주세요.")
        return

    ar = arrow(d["change_pct"])
    is_krw = d["currency"] == "KRW"

    if is_krw:
        price_str   = f"{d['price']:,.0f}원"
        change_str  = f"{'+' if d['change_abs'] >= 0 else ''}{d['change_abs']:,.0f}원 ({fmt_pct(d['change_pct'])})"
        prev_str    = f"{d['prev_close']:,.0f}원"
        high52_str  = f"{d['week52_high']:,.0f}원" if d["week52_high"] else "N/A"
        low52_str   = f"{d['week52_low']:,.0f}원"  if d["week52_low"]  else "N/A"
    else:
        price_str   = f"${d['price']:,.2f}"
        change_str  = f"{'+' if d['change_abs'] >= 0 else ''}${d['change_abs']:,.2f} ({fmt_pct(d['change_pct'])})"
        prev_str    = f"${d['prev_close']:,.2f}"
        high52_str  = f"${d['week52_high']:,.2f}" if d["week52_high"] else "N/A"
        low52_str   = f"${d['week52_low']:,.2f}"  if d["week52_low"]  else "N/A"

    vol_str = f"{d['volume']:,}" if d["volume"] else "N/A"

    lines = [
        f"📈 *{d['symbol']}*",
        f"_{now_kst()}_",
        "",
        f"현재가: *{price_str}*  {ar} {change_str}",
        f"전일 종가: {prev_str}",
        "",
        f"📊 52주 최고: {high52_str}",
        f"📊 52주 최저: {low52_str}",
        f"📊 거래량: {vol_str}",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── 봇 실행 ───────────────────────────────────────────────
if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",     cmd_help))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("portfolio", cmd_portfolio))
    app.add_handler(CommandHandler("stock",     cmd_stock))

    print("봇 시작됨. Ctrl+C로 종료.")
    app.run_polling()
