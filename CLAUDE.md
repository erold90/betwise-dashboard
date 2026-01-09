# BetWise - Documentazione per Claude

> Questo file serve a Claude per ricordare tutto del progetto senza bisogno di spiegazioni.
> Ultimo aggiornamento: 20 dicembre 2025

---

## PANORAMICA SISTEMA

BetWise è un sistema automatico di analisi scommesse calcistiche che:
1. **Ogni giovedì alle 19:00** analizza le partite del weekend
2. **Decide** se giocare (GIOCARE/CAUTELA/SALTARE)
3. **Genera schedine** solo se le condizioni sono favorevoli
4. **Invia su Telegram** analisi + schedine
5. **Aggiorna dashboard** su GitHub Pages

---

## ARCHITETTURA FILE

```
betwise-dashboard/
├── index.html                 # Dashboard frontend (GitHub Pages)
├── src/
│   ├── data/
│   │   └── predictions.json   # Output Claude API (schedine o skip)
│   └── python/
│       ├── claude_predictor.py    # Script principale (chiamato da workflow)
│       └── telegram_notify.py     # Legacy, non più usato
├── .github/
│   └── workflows/
│       └── update-predictions.yml  # GitHub Actions (giovedì 19:00)
└── CLAUDE.md                  # Questo file
```

---

## WORKFLOW GITHUB ACTIONS

**File:** `.github/workflows/update-predictions.yml`

**Schedule:** `cron: '0 18 * * 4'` = Giovedì 18:00 UTC = 19:00 CET

**Secrets richiesti:**
- `ANTHROPIC_API_KEY` - API key Claude
- `TELEGRAM_BOT_TOKEN` - Token bot Telegram (da @BotFather)
- `TELEGRAM_CHAT_ID` - Chat ID utente (usa @userinfobot per trovarlo)

**Cosa fa:**
1. Checkout repo
2. Setup Python 3.11
3. Esegue `claude_predictor.py`
4. Commit + push `predictions.json`
5. Deploy su GitHub Pages

---

## CLAUDE PREDICTOR

**File:** `src/python/claude_predictor.py`

**Modello:** `claude-sonnet-4-20250514`

### System Prompt (MOLTO IMPORTANTE)

Claude è istruito come **TIPSTER PROFESSIONISTA** con:

1. **FASE DECISIONE** (obbligatoria prima di generare schedine):
   - Criteri GIOCARE: almeno 3 leghe attive, 25+ partite, 5+ value bet
   - Red flags: pausa invernale, poche partite, calendario congestionato
   - Decisioni: GIOCARE / CAUTELA / SALTARE

2. **MENTALITÀ TIPSTER PRO:**
   - Value betting (quote sbagliate, non favoriti)
   - Analisi xG, regressione, form trends
   - Fattori nascosti (line movement, calendario, meteo, arbitro)
   - Psicologia e motivazione
   - Market intelligence

3. **STRATEGIA SCHEDINE:**
   - Correlazione intelligente tra schedine (stesse partite, bet diverse)
   - Banker selections (2-3 quasi certe in più schedine)
   - Bilanciamento rischio (60% sicure, 30% medie, 10% rischiose)
   - Diversificazione leghe (max 3-4 stessa lega)
   - NO duplicati nella stessa schedina (regola bookmaker)

4. **TIPI SCHEDINE:**

   **GIOCARE (4 schedine, €3):**
   - CLASSIC: 12 selezioni, DC/Over 1.5, quota 500-800x
   - GOALS: 12 selezioni, Over/BTTS, quota 800-1500x
   - RESULTS: 10 selezioni, solo 1X2, quota 500-1000x
   - MEGA: 15 selezioni, mix, quota 1500-3000x

   **CAUTELA (2 schedine, €2):**
   - SAFE: 6-8 selezioni, bet sicure, quota 300-500x
   - RISK: 6-8 selezioni, mix equilibrato, quota 500-800x

### Output JSON

```json
{
  "weekend": "27/12/2025 - 29/12/2025",
  "generated_at": "2025-12-26T19:00:00",
  "decision": "GIOCARE" | "CAUTELA" | "SALTARE",
  "analysis": {
    "leagues_active": 5,
    "matches_available": 48,
    "value_bets_found": 12,
    "red_flags": [],
    "recommendation": "Spiegazione decisione"
  },
  "next_analysis": "Giovedì 02/01/2026 alle 19:00",
  "schedine": {
    "jackpot_classic": {
      "name": "Classic",
      "emoji": "🔴",
      "selections": [
        {
          "match": "Team A vs Team B",
          "league": "Premier League",
          "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
          "selection": "Over 1.5",
          "odds": 1.15,
          "reasoning": "Max 50 caratteri"
        }
      ],
      "totalOdds": "XXX",
      "stake": 3,
      "potentialWin": "€XXXX"
    }
  }
}
```

---

## DASHBOARD

**File:** `index.html`

**URL:** https://erold90.github.io/betwise-dashboard/

### Stati gestiti:

1. **GIOCARE** (pallino verde):
   - Mostra 4 card schedine (Classic, Goals, Results, Mega)
   - Click apre modal con dettagli

2. **CAUTELA** (pallino giallo):
   - Mostra 2 card schedine (Safe, Risk)

3. **SALTARE** (pallino giallo):
   - Mostra "Weekend Saltato"
   - Mostra motivo (analysis.recommendation)
   - Mostra prossima analisi (next_analysis)

4. **Vuoto/Expired** (pallino grigio):
   - Mostra "Nessuna schedina disponibile"
   - "Le nuove schedine arriveranno giovedì alle 19:00"

### Auto-expire:
Le schedine scadono il giorno dopo l'ultima partita (lunedì dopo domenica).
Parsing date: `DD/MM/YYYY - DD/MM/YYYY`

---

## TELEGRAM

**Bot Token:** *(configurare in GitHub Secrets o localStorage)*
**Chat ID:** *(configurare in GitHub Secrets o localStorage)*

> **SICUREZZA:** I token Telegram NON devono essere committati nel codice. Usare:
> - GitHub Secrets per workflow automatici
> - localStorage per la dashboard (il token viene chiesto al primo utilizzo)

### Messaggi inviati:

1. **Sempre:** Messaggio analisi con decisione
2. **Se GIOCARE/CAUTELA:** Schedine formattate
3. **Se GIOCARE/CAUTELA:** Footer con puntata consigliata

### Formato analisi:
```
🟢 ANALISI WEEKEND 27/12/2025 - 29/12/2025

📊 Statistiche:
• Leghe attive: 5/5
• Partite disponibili: 48
• Value bet trovate: 12

VERDETTO: GIOCHIAMO!

💬 Tutte le condizioni favorevoli...

⏳ Schedine in arrivo tra pochi secondi...
```

---

## LEGHE ANALIZZATE

- 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League (Inghilterra)
- 🇮🇹 Serie A (Italia)
- 🇪🇸 La Liga (Spagna)
- 🇩🇪 Bundesliga (Germania)
- 🇫🇷 Ligue 1 (Francia)

**Nota:** In inverno (dicembre-gennaio) alcune leghe sono in pausa.
Premier League gioca sempre (Boxing Day tradition).

---

## COSTI API

- ~7.000 token per chiamata
- ~$0.08 per chiamata
- ~$0.32/mese (4 chiamate)
- ~$4/anno

---

## MODIFICHE COMUNI

### Cambiare giorno/ora workflow:
```yaml
# .github/workflows/update-predictions.yml
cron: '0 18 * * 4'  # 4=giovedì, 18:00 UTC = 19:00 CET
```

### Cambiare modello Claude:
```python
# src/python/claude_predictor.py
CLAUDE_MODEL = "claude-sonnet-4-20250514"
```

### Aggiungere strategia al prompt:
Modifica `SYSTEM_PROMPT` in `claude_predictor.py`

### Aggiungere lega:
Aggiungi nel SYSTEM_PROMPT sezione "LEGHE DA ANALIZZARE"

### Cambiare stake/vincita minima:
Modifica nel SYSTEM_PROMPT sezione "TIPI DI SCHEDINE"

---

## CRONOLOGIA DECISIONI

| Data | Decisione | Note |
|------|-----------|------|
| 20/12/2025 | Setup | Sistema creato |
| 26/12/2025 | TBD | Primo run automatico (probabile SKIP - Natale) |

---

## CONTATTI

- **GitHub Repo:** erold90/betwise-dashboard

---

## COMANDI UTILI

```bash
# Test locale (richiede ANTHROPIC_API_KEY)
ANTHROPIC_API_KEY=xxx TELEGRAM_BOT_TOKEN=xxx TELEGRAM_CHAT_ID=xxx python3 src/python/claude_predictor.py

# Trigger manuale workflow
gh workflow run update-predictions.yml

# Vedere log workflow
gh run list --workflow=update-predictions.yml
gh run view <run-id> --log
```

---

## NOTA IMPORTANTE

**Correlazione tra schedine:** Le stesse partite possono apparire in schedine DIVERSE con bet complementari. Questo crea "sweet spot" dove un risultato (es. 1-1) vince su più schedine contemporaneamente.

**Esempio:**
- Schedina 1: Sassuolo-Torino DC 1X
- Schedina 2: Sassuolo-Torino BTTS
- Schedina 3: Sassuolo-Torino X

Se finisce 1-1 → tutte e 3 vincono!

Questa strategia è INTENZIONALE e consigliata (non obbligatoria).
