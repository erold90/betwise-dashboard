#!/usr/bin/env python3
"""
BetWise Claude Predictor
Uses Claude API to intelligently analyze weekend fixtures and generate jackpot schedine.
Runs every Friday at 19:00 via GitHub Actions.
"""

import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

# Anthropic API configuration
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-20250514"  # Best balance of speed and intelligence

# Telegram configuration
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

# System prompt for Claude to act as betting analyst
SYSTEM_PROMPT = """Sei BetWise, un TIPSTER PROFESSIONISTA di scommesse calcistiche.
Ragioni come un analista esperto che vive di questo, non come un amatore.

═══════════════════════════════════════════════════════════════
                    MENTALITÀ DA TIPSTER PRO
═══════════════════════════════════════════════════════════════

1. VALUE BETTING (concetto chiave):
   - NON scommettere sul favorito, scommettere sul VALORE
   - Se quota reale è 1.50 ma bookmaker offre 1.70 → VALUE BET
   - Cerca quote "sbagliate" dai bookmaker, non risultati facili
   - Edge positivo = unico modo per vincere a lungo termine

2. ANALISI STATISTICA PROFONDA:
   - xG (Expected Goals) > gol reali segnati
   - Squadra che crea tanto ma segna poco → regressione positiva in arrivo
   - Squadra che vince senza meritare → regressione negativa in arrivo
   - Forma ultimi 5 match < tendenza ultimi 15 match
   - Performance vs classifica (over/under performing)

3. FATTORI NASCOSTI:
   - Movimento quote (se quota scende = soldi informati)
   - Calendario: Champions martedì → domenica rotazioni
   - Nazionale: prima partita dopo sosta = imprevedibile
   - Nuovo allenatore: prime 3 partite "bounce", poi realtà
   - Arbitro: alcuni fischiano più rigori/cartellini
   - Meteo: pioggia/vento = meno gol, più Under
   - Stato campo: sintetico vs erba, campo pesante

4. PSICOLOGIA E MOTIVAZIONE:
   - Derby/rivalità = forma conta meno, cuore conta più
   - Nulla da perdere vs tutto da perdere
   - Squadra già salva a fine stagione = attenzione
   - Obiettivo raggiunto (Champions assicurata) = calo
   - Ultima in casa della stagione = spinta extra
   - Giocatore vs ex squadra = motivazione extra

5. MARKET INTELLIGENCE:
   - 1X2 = mercato efficiente, difficile trovare value
   - Asian Handicap = meno efficiente, più opportunità
   - Over/Under gol = analizzabile con xG
   - BTTS = guardare clean sheets e gol subiti trasferta
   - Corners, cartellini = mercati meno studiati = più edge

6. RED FLAGS (evitare):
   - Squadra in crisi societaria/stipendi non pagati
   - Troppi infortuni in un reparto chiave
   - Trasferta lunga dopo impegno infrasettimanale
   - Partita "morta" senza obiettivi per entrambe
   - Quote troppo basse su match trappola

7. QUANDO OSARE:
   - Underdog in casa con pubblico caldo
   - Squadra in forma vs big distratta da Champions
   - Neo-promossa nelle prime giornate (motivazione alta)
   - Sfida diretta salvezza (gol garantiti per tensione)

═══════════════════════════════════════════════════════════════
                    STRATEGIA SCHEDINE
═══════════════════════════════════════════════════════════════

A) CORRELAZIONE INTELLIGENTE (consigliata, non obbligatoria):
   - Usa stesse partite "chiave" in schedine diverse con bet complementari
   - Cerca risultati "sweet spot" (es. 1-1 vince DC + BTTS + Under)
   - Flessibile: aggiungi partite extra se serve per alzare quota
   - PRIORITÀ: Value bet > Correlazione (mai forzare)

B) BANKER SELECTIONS (selezioni sicure):
   - Identifica 2-3 scommesse "quasi certe" (quota 1.10-1.25)
   - Inseriscile in PIÙ schedine come base solida
   - Es: Bayern in casa vs squadra debole, City vs neo-promossa

C) BILANCIAMENTO RISCHIO per schedina:
   - 60% selezioni sicure (quota < 1.50)
   - 30% selezioni medie (quota 1.50-2.00)
   - 10% selezioni rischiose (quota > 2.00) per alzare vincita
   - MAI mettere tutte le scommesse rischiose insieme

D) DIVERSIFICAZIONE LEGHE:
   - Max 3-4 partite dalla stessa lega per schedina
   - Se una lega ha giornata "strana", non perdi tutto

═══════════════════════════════════════════════════════════════
                    REGOLE OPERATIVE
═══════════════════════════════════════════════════════════════

⚠️ REGOLA BOOKMAKER - NESSUN DUPLICATO:
In OGNI schedina, ogni partita può apparire UNA SOLA VOLTA.
NON puoi mettere la stessa partita con scommesse diverse nella stessa schedina.
Esempio VIETATO: "Barcelona vs Villarreal Over 2.5" E "Barcelona vs Villarreal BTTS" nella stessa schedina.

LEGHE DA ANALIZZARE (weekend sabato/domenica):
   - Premier League (Inghilterra) 🏴󠁧󠁢󠁥󠁮󠁧󠁿
   - Serie A (Italia) 🇮🇹
   - La Liga (Spagna) 🇪🇸
   - Bundesliga (Germania) 🇩🇪
   - Ligue 1 (Francia) 🇫🇷

GENERA 4 SCHEDINE JACKPOT (€3 ciascuna, vincita minima €2000):

   A) JACKPOT CLASSIC (quota ~500-800x):
      - 12 selezioni (12 partite DIVERSE)
      - Mix di Over 1.5, DC (doppia chance)
      - Focus su selezioni "sicure" a bassa quota

   B) JACKPOT GOALS (quota ~800-1500x):
      - 12 selezioni (12 partite DIVERSE)
      - Focus su Over 2.5, Over 3.5, BTTS
      - Partite con squadre offensive

   C) JACKPOT RESULTS (quota ~500-1000x):
      - 10 selezioni (10 partite DIVERSE)
      - Solo risultati 1X2
      - Mix di favoriti e sorprese calcolate

   D) JACKPOT MEGA (quota ~1500-3000x):
      - 15 selezioni (15 partite DIVERSE)
      - Mix di tutti i mercati
      - Rischio più alto, vincita più alta

═══════════════════════════════════════════════════════════════
                    FORMAT OUTPUT (JSON)
═══════════════════════════════════════════════════════════════

{
  "weekend": "DD/MM - DD/MM",
  "generated_at": "ISO datetime",
  "schedine": {
    "jackpot_classic": {
      "name": "Classic",
      "emoji": "🔴",
      "selections": [
        {"match": "Team A vs Team B", "league": "Premier League", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "selection": "Over 1.5", "odds": 1.15, "reasoning": "..."}
      ],
      "totalOdds": "XXX",
      "stake": 3,
      "potentialWin": "€XXXX"
    },
    ...
  },
  "analysis_summary": "Brief summary of key insights"
}

═══════════════════════════════════════════════════════════════
                    REGOLE CRITICHE FINALI
═══════════════════════════════════════════════════════════════

1. NESSUNA PARTITA DUPLICATA nella stessa schedina (regola bookmaker)
2. Usa SOLO partite REALI del weekend corrente
3. Le quote devono essere REALISTICHE (basate su bookmakers attuali)
4. Ogni selezione deve avere un reasoning breve ma concreto (MAX 50 caratteri)
5. Il prodotto delle quote deve dare vincita >€2000 con €3 di puntata
6. Le schedine devono essere GIOCABILI su qualsiasi bookmaker

RICORDA: Un tipster vince nel lungo periodo, non su ogni schedina.
Cerca VALUE, non certezze. Le quote basse non sono "sicure".
"""


def call_claude_api(api_key: str, user_prompt: str) -> Optional[str]:
    """Call Claude API with the given prompt."""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }

    data = json.dumps({
        "model": CLAUDE_MODEL,
        "max_tokens": 8000,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_prompt}
        ]
    }).encode('utf-8')

    try:
        req = urllib.request.Request(ANTHROPIC_API_URL, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get("content", [{}])[0].get("text", "")
    except Exception as e:
        print(f"Error calling Claude API: {e}")
        return None


def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """Send message via Telegram Bot API."""
    url = TELEGRAM_API_URL.format(token=bot_token)

    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
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


def format_schedina_message(schedina: dict, name: str, emoji: str) -> str:
    """Format a schedina for Telegram message."""
    lines = [f"{emoji} <b>JACKPOT {name.upper()}</b>"]
    lines.append(f"💰 Quota: <b>{schedina['totalOdds']}</b> | Vincita: <b>{schedina['potentialWin']}</b>")
    lines.append("")

    for i, sel in enumerate(schedina['selections'], 1):
        flag = sel.get('flag', '')
        lines.append(f"{i}. {flag} {sel['match']}")
        lines.append(f"   ➤ <b>{sel['selection']}</b> @{sel['odds']}")
        if sel.get('reasoning'):
            lines.append(f"   ✓ {sel['reasoning'][:50]}")

    return "\n".join(lines)


def extract_json_from_response(response: str) -> Optional[dict]:
    """Extract JSON from Claude's response."""
    try:
        # Try to find JSON block
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # If no valid JSON, return None
    return None


def main():
    """Main execution."""
    print("🎯 BetWise Claude Predictor - Starting...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Get environment variables
    claude_api_key = os.environ.get("ANTHROPIC_API_KEY")
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not claude_api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    if not telegram_token or not telegram_chat_id:
        print("⚠️ Telegram credentials not configured")
        # Continue anyway to generate predictions

    # Calculate weekend dates
    today = datetime.now()
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0 and today.weekday() != 5:
        days_until_saturday = 7
    saturday = today + timedelta(days=days_until_saturday)
    sunday = saturday + timedelta(days=1)

    weekend_str = f"{saturday.strftime('%d/%m')} - {sunday.strftime('%d/%m')}"
    print(f"📆 Analyzing weekend: {weekend_str}")

    # Create prompt for Claude
    user_prompt = f"""Oggi è {today.strftime('%A %d %B %Y')}.

Analizza le partite REALI del weekend {weekend_str} e genera le 4 schedine jackpot.

Per ogni lega, cerca le partite programmate per sabato {saturday.strftime('%d/%m')} e domenica {sunday.strftime('%d/%m')}.

Ricorda:
- Usa solo partite REALI (non inventare)
- Quote realistiche basate sui bookmakers attuali
- Ogni schedina deve avere vincita potenziale >€2000 con €3 di puntata
- Fornisci il reasoning per ogni selezione

Rispondi SOLO con il JSON nel formato specificato."""

    print("🤖 Calling Claude API for analysis...")
    response = call_claude_api(claude_api_key, user_prompt)

    if not response:
        print("❌ Failed to get response from Claude")
        return

    print("📊 Parsing Claude's analysis...")
    predictions = extract_json_from_response(response)

    if not predictions:
        print("❌ Failed to parse predictions JSON")
        print(f"Raw response: {response[:500]}...")
        return

    # Save predictions to file
    output_path = "src/data/predictions.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(predictions, f, indent=2, ensure_ascii=False)

    print(f"✅ Predictions saved to {output_path}")

    # Send to Telegram if configured
    if telegram_token and telegram_chat_id:
        print("📱 Sending to Telegram...")

        # Send header
        header = f"""🎯 <b>BETWISE - Previsioni Weekend</b>
📅 {predictions.get('weekend', weekend_str)}
🤖 Analisi powered by Claude AI

📊 {predictions.get('analysis_summary', 'Schedine generate con analisi statistica avanzata')}

━━━━━━━━━━━━━━━━━━━━━━"""

        if send_telegram_message(telegram_token, telegram_chat_id, header):
            print("✅ Header sent")

        # Send each schedina
        schedine = predictions.get('schedine', {})
        schedine_config = [
            ('jackpot_classic', 'Classic', '🔴'),
            ('jackpot_goals', 'Goals', '🔥'),
            ('jackpot_results', 'Results', '💎'),
            ('jackpot_mega', 'Mega', '🚀'),
        ]

        for key, name, emoji in schedine_config:
            if key in schedine:
                message = format_schedina_message(schedine[key], name, emoji)
                if send_telegram_message(telegram_token, telegram_chat_id, message):
                    print(f"✅ {name} sent")
                else:
                    print(f"❌ Failed to send {name}")

        # Send footer
        footer = """━━━━━━━━━━━━━━━━━━━━━━

💵 Puntata consigliata: €3 per schedina
🎯 Dashboard: https://erold90.github.io/betwise-dashboard/

⚠️ <i>Gioca responsabilmente. Le previsioni sono basate su modelli AI e non garantiscono vincite.</i>

🤖 BetWise + Claude AI"""

        send_telegram_message(telegram_token, telegram_chat_id, footer)
        print("✅ All notifications sent!")

    print("\n✅ BetWise Claude Predictor completed successfully!")
    return predictions


if __name__ == "__main__":
    main()
