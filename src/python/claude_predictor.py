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
Un vero tipster NON gioca ogni weekend - aspetta le opportunità giuste.

═══════════════════════════════════════════════════════════════
              FASE 1: ANALISI E DECISIONE (OBBLIGATORIA)
═══════════════════════════════════════════════════════════════

PRIMA di generare schedine, DEVI analizzare il weekend e DECIDERE se giocare.

CRITERI PER GIOCARE (servono ALMENO 3 su 5):
   ✓ Almeno 3 leghe attive (no pause invernali/nazionali)
   ✓ Almeno 25 partite disponibili nel weekend
   ✓ Almeno 5 value bet identificate (edge positivo)
   ✓ Possibilità di diversificare (non tutto su 1 lega)
   ✓ Nessun red flag critico (vedi sotto)

RED FLAGS CRITICI (se presenti, valuta SKIP):
   ✗ Solo 1-2 leghe attive (es. Natale, pause)
   ✗ Meno di 15 partite disponibili
   ✗ Calendario congestionato (3 partite in 7 giorni = rotazioni)
   ✗ Fine stagione con molte partite "morte"
   ✗ Post-nazionale (prima giornata = imprevedibile)

DECISIONI POSSIBILI:
   🟢 GIOCARE: Tutte le condizioni favorevoli → 4 schedine standard
   🟡 CAUTELA: Condizioni miste → 2 schedine ridotte (6-8 selezioni, €2)
   🔴 SALTARE: Troppe red flags → Nessuna schedina, aspetta prossimo weekend

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

6. RED FLAGS (evitare queste partite):
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

LEGHE DA ANALIZZARE (venerdì/sabato/domenica):
   - Premier League (Inghilterra) 🏴󠁧󠁢󠁥󠁮󠁧󠁿
   - Serie A (Italia) 🇮🇹
   - La Liga (Spagna) 🇪🇸
   - Bundesliga (Germania) 🇩🇪
   - Ligue 1 (Francia) 🇫🇷

TIPI DI SCHEDINE:

   MODALITÀ STANDARD (quando decisione = 🟢 GIOCARE):
   4 schedine, €3 ciascuna, vincita minima €2000

      A) JACKPOT CLASSIC (quota ~500-800x):
         - 12 selezioni, mix di Over 1.5, DC
      B) JACKPOT GOALS (quota ~800-1500x):
         - 12 selezioni, focus Over 2.5, BTTS
      C) JACKPOT RESULTS (quota ~500-1000x):
         - 10 selezioni, solo 1X2
      D) JACKPOT MEGA (quota ~1500-3000x):
         - 15 selezioni, mix tutti i mercati

   MODALITÀ CAUTELA (quando decisione = 🟡 CAUTELA):
   2 schedine, €2 ciascuna, vincita minima €1000

      A) JACKPOT SAFE (quota ~300-500x):
         - 6-8 selezioni, solo bet sicure
      B) JACKPOT RISK (quota ~500-800x):
         - 6-8 selezioni, mix equilibrato

═══════════════════════════════════════════════════════════════
                    FORMAT OUTPUT (JSON)
═══════════════════════════════════════════════════════════════

{
  "weekend": "DD/MM - DD/MM",
  "generated_at": "ISO datetime",
  "decision": "GIOCARE" | "CAUTELA" | "SALTARE",
  "analysis": {
    "leagues_active": 5,
    "matches_available": 48,
    "value_bets_found": 12,
    "red_flags": [],
    "recommendation": "Spiegazione breve della decisione"
  },
  "next_analysis": "Giovedì DD/MM alle 19:00",
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
  }
}

NOTA: Se decision = "SALTARE", il campo "schedine" sarà vuoto {}.

═══════════════════════════════════════════════════════════════
                    REGOLE CRITICHE FINALI
═══════════════════════════════════════════════════════════════

1. ANALIZZA PRIMA, DECIDI POI - Mai generare schedine senza analisi
2. NESSUNA PARTITA DUPLICATA nella stessa schedina (regola bookmaker)
3. Usa SOLO partite REALI del weekend corrente
4. Le quote devono essere REALISTICHE (basate su bookmakers attuali)
5. Ogni selezione deve avere un reasoning breve ma concreto (MAX 50 caratteri)
6. Se GIOCARE: vincita >€2000 con €3 | Se CAUTELA: vincita >€1000 con €2
7. Le schedine devono essere GIOCABILI su qualsiasi bookmaker

RICORDA: Un tipster vince nel lungo periodo, non su ogni schedina.
Saltare un weekend difficile È una vittoria.
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


def format_analysis_message(predictions: dict) -> str:
    """Format the analysis message for Telegram."""
    decision = predictions.get('decision', 'SALTARE')
    analysis = predictions.get('analysis', {})
    weekend = predictions.get('weekend', 'N/A')
    next_analysis = predictions.get('next_analysis', 'Prossimo giovedì')

    # Decision emoji and color
    if decision == "GIOCARE":
        emoji = "🟢"
        status = "GIOCHIAMO!"
    elif decision == "CAUTELA":
        emoji = "🟡"
        status = "CAUTELA - Schedine ridotte"
    else:
        emoji = "🔴"
        status = "SALTIAMO"

    lines = [
        f"{emoji} <b>ANALISI WEEKEND {weekend}</b>",
        "",
        "📊 <b>Statistiche:</b>",
        f"• Leghe attive: {analysis.get('leagues_active', 'N/A')}/5",
        f"• Partite disponibili: {analysis.get('matches_available', 'N/A')}",
        f"• Value bet trovate: {analysis.get('value_bets_found', 'N/A')}",
    ]

    # Red flags
    red_flags = analysis.get('red_flags', [])
    if red_flags:
        lines.append("")
        lines.append("⚠️ <b>Red Flags:</b>")
        for flag in red_flags[:3]:  # Max 3 flags
            lines.append(f"• {flag}")

    lines.append("")
    lines.append(f"<b>VERDETTO: {status}</b>")
    lines.append("")
    lines.append(f"💬 {analysis.get('recommendation', '')}")

    if decision == "SALTARE":
        lines.append("")
        lines.append(f"📅 Prossima analisi: {next_analysis}")
    elif decision in ["GIOCARE", "CAUTELA"]:
        lines.append("")
        lines.append("⏳ Schedine in arrivo tra pochi secondi...")

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

    # Calculate weekend dates (Friday/Saturday/Sunday)
    today = datetime.now()

    # Days until Friday (weekday 4)
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0 and today.weekday() == 4:
        days_until_friday = 1  # If today is Thursday, Friday is tomorrow
    elif days_until_friday == 0:
        days_until_friday = 7

    friday = today + timedelta(days=days_until_friday)
    saturday = friday + timedelta(days=1)
    sunday = friday + timedelta(days=2)

    # Calculate next Thursday for "next_analysis"
    next_thursday = today + timedelta(days=7)
    next_analysis_str = f"Giovedì {next_thursday.strftime('%d/%m/%Y')} alle 19:00"

    weekend_str = f"{friday.strftime('%d/%m/%Y')} - {sunday.strftime('%d/%m/%Y')}"
    print(f"📆 Analyzing weekend: {weekend_str}")

    # Create prompt for Claude
    user_prompt = f"""DATA CORRENTE: {today.strftime('%A %d %B %Y')} (oggi è giovedì).
ANNO CORRENTE: {today.year}
ANNO PROSSIMO: {today.year + 1}

FASE 1 - ANALISI:
Analizza le partite REALI del weekend {weekend_str} (venerdì {friday.strftime('%d/%m/%Y')}, sabato {saturday.strftime('%d/%m/%Y')}, domenica {sunday.strftime('%d/%m/%Y')}).

Verifica:
- Quali leghe sono attive (attenzione a pause invernali/nazionali)
- Quante partite sono disponibili
- Quante value bet riesci a identificare
- Eventuali red flags (poche partite, calendario congestionato, ecc.)

FASE 2 - DECISIONE:
Basandoti sull'analisi, decidi:
- 🟢 GIOCARE: Se almeno 3 criteri su 5 sono soddisfatti → genera 4 schedine standard
- 🟡 CAUTELA: Se condizioni miste → genera 2 schedine ridotte
- 🔴 SALTARE: Se troppe red flags → nessuna schedina

FASE 3 - OUTPUT:
Rispondi SOLO con il JSON nel formato specificato.

Imposta "next_analysis": "{next_analysis_str}"

Ricorda:
- Usa solo partite REALI (non inventare)
- Quote realistiche basate sui bookmakers attuali
- Se GIOCARE: vincita >€2000 con €3
- Se CAUTELA: vincita >€1000 con €2
- Fornisci reasoning per ogni selezione (max 50 caratteri)"""

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

    # Get decision
    decision = predictions.get('decision', 'SALTARE')
    print(f"📋 Decision: {decision}")

    # Save predictions to file (even if SALTARE - for dashboard)
    output_path = "src/data/predictions.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(predictions, f, indent=2, ensure_ascii=False)

    print(f"✅ Predictions saved to {output_path}")

    # Send to Telegram if configured
    if telegram_token and telegram_chat_id:
        print("📱 Sending to Telegram...")

        # Always send analysis message first
        analysis_msg = format_analysis_message(predictions)
        if send_telegram_message(telegram_token, telegram_chat_id, analysis_msg):
            print("✅ Analysis sent")
        else:
            print("❌ Failed to send analysis")

        # Only send schedine if decision is GIOCARE or CAUTELA
        if decision in ["GIOCARE", "CAUTELA"]:
            schedine = predictions.get('schedine', {})

            if decision == "GIOCARE":
                # Standard 4 schedine
                schedine_config = [
                    ('jackpot_classic', 'Classic', '🔴'),
                    ('jackpot_goals', 'Goals', '🔥'),
                    ('jackpot_results', 'Results', '💎'),
                    ('jackpot_mega', 'Mega', '🚀'),
                ]
            else:
                # Cautela - 2 schedine ridotte
                schedine_config = [
                    ('jackpot_safe', 'Safe', '🟡'),
                    ('jackpot_risk', 'Risk', '🟠'),
                ]

            for key, name, emoji in schedine_config:
                if key in schedine and schedine[key].get('selections'):
                    message = format_schedina_message(schedine[key], name, emoji)
                    if send_telegram_message(telegram_token, telegram_chat_id, message):
                        print(f"✅ {name} sent")
                    else:
                        print(f"❌ Failed to send {name}")

            # Send footer
            stake = "€3" if decision == "GIOCARE" else "€2"
            footer = f"""━━━━━━━━━━━━━━━━━━━━━━

💵 Puntata consigliata: {stake} per schedina
🎯 Dashboard: https://erold90.github.io/betwise-dashboard/

⚠️ <i>Gioca responsabilmente. Le previsioni sono basate su modelli AI e non garantiscono vincite.</i>

🤖 BetWise + Claude AI"""

            send_telegram_message(telegram_token, telegram_chat_id, footer)
            print("✅ All notifications sent!")
        else:
            print("ℹ️ Decision is SALTARE - no schedine sent")

    print(f"\n✅ BetWise Claude Predictor completed! Decision: {decision}")
    return predictions


if __name__ == "__main__":
    main()
