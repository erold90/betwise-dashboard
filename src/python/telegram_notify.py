#!/usr/bin/env python3
"""
BetWise Telegram Notification Bot
Sends weekend predictions to Telegram
Updated for 4 Jackpot structure
"""

import json
import os
import urllib.request
import urllib.parse
from datetime import datetime


def send_telegram_message(bot_token: str, chat_id: str, message: str, parse_mode: str = "HTML") -> bool:
    """Send message via Telegram Bot API"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get("ok", False)
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False


def format_schedina(schedina: dict, nome: str, emoji: str) -> str:
    """Format a schedina for Telegram"""
    if not schedina or not schedina.get('selections'):
        return ""

    lines = [f"\n{emoji} <b>{nome}</b>"]
    lines.append(f"Quota: <b>{schedina['totalOdds']}</b> | Puntata: €{schedina['stake']}")
    lines.append("")

    for i, sel in enumerate(schedina['selections'], 1):
        lines.append(f"{i}. {sel['flag']} {sel['match']}")
        lines.append(f"   ➤ <b>{sel['selection']}</b> @{sel['odds']} ({sel['probability']}%)")

    vincita = float(schedina['totalOdds']) * schedina['stake']
    lines.append(f"\n💰 Vincita potenziale: <b>€{vincita:.2f}</b>")

    return "\n".join(lines)


def main():
    """Main execution"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("⚠️ Telegram credentials not configured")
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in GitHub Secrets")
        return

    # Load predictions
    try:
        with open("src/data/predictions.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ predictions.json not found")
        return

    # Format header message
    header = f"""🎯 <b>BETWISE - Previsioni Weekend</b>
📅 {data.get('weekend', 'N/A')}

📊 <b>Statistiche:</b>
• Partite analizzate: {data['stats']['total_matches']}
• Value bets trovate: {data['stats']['value_bets_found']}
• Leghe processate: {data['stats']['leagues_processed']}

🔗 Dashboard: https://erold90.github.io/betwise-dashboard/
"""

    # Send header
    if send_telegram_message(bot_token, chat_id, header):
        print("✅ Header sent")
    else:
        print("❌ Failed to send header")

    # Get schedine
    schedine = data.get("schedine", {})

    # New structure: media, jackpot1, jackpot2, jackpot3, jackpot4
    schedine_config = [
        ("media", "SCHEDINA MEDIA", "🟡"),
        ("jackpot1", "JACKPOT CLASSIC", "🔴"),
        ("jackpot2", "JACKPOT GOALS", "🔥"),
        ("jackpot3", "JACKPOT RESULTS", "💎"),
        ("jackpot4", "JACKPOT MEGA", "🚀"),
    ]

    for key, nome, emoji in schedine_config:
        if key in schedine and schedine[key].get("selections"):
            message = format_schedina(schedine[key], nome, emoji)
            if message and send_telegram_message(bot_token, chat_id, message):
                print(f"✅ {nome} sent")
            else:
                print(f"❌ Failed to send {nome}")

    # Send top value bets
    matches = data.get("matches", [])
    value_bets = []

    for match in matches:
        for vb in match.get("value_bets", [])[:2]:
            value_bets.append({
                "match": f"{match.get('home_team', match.get('homeTeam', 'N/A'))} vs {match.get('away_team', match.get('awayTeam', 'N/A'))}",
                "league": match.get("league_flag", match.get("leagueFlag", "")),
                "market": vb["market"],
                "odds": vb["odds"],
                "edge": vb["edge"]
            })

    # Sort by edge and take top 5
    value_bets = sorted(value_bets, key=lambda x: x["edge"], reverse=True)[:5]

    if value_bets:
        vb_message = "\n💎 <b>TOP VALUE BETS</b>\n\n"
        for i, vb in enumerate(value_bets, 1):
            vb_message += f"{i}. {vb['league']} {vb['match']}\n"
            vb_message += f"   ➤ <b>{vb['market']}</b> @{vb['odds']} (+{vb['edge']}% edge)\n\n"

        if send_telegram_message(bot_token, chat_id, vb_message):
            print("✅ Value bets sent")

    # Final message
    footer = """⚠️ <i>Gioca responsabilmente. Le previsioni sono basate su modelli statistici e non garantiscono vincite.</i>

🤖 Generato automaticamente da BetWise"""
    send_telegram_message(bot_token, chat_id, footer)

    print("\n✅ All notifications sent successfully!")


if __name__ == "__main__":
    main()
