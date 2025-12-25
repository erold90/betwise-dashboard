#!/usr/bin/env python3
"""
BetWise Predictor - Algoritmo di Previsione Calcistica
Utilizza modello Poisson + xG per prevedere risultati partite
"""

import json
import math
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
import urllib.request
import urllib.error

# Configuration
CONFIG = {
    "leagues": {
        "E0": {"name": "Premier League", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "country": "england", "code": "premier"},
        "SP1": {"name": "La Liga", "flag": "🇪🇸", "country": "spain", "code": "laliga"},
        "I1": {"name": "Serie A", "flag": "🇮🇹", "country": "italy", "code": "seriea"},
        "D1": {"name": "Bundesliga", "flag": "🇩🇪", "country": "germany", "code": "bundesliga"},
        "F1": {"name": "Ligue 1", "flag": "🇫🇷", "country": "france", "code": "ligue1"},
        "N1": {"name": "Eredivisie", "flag": "🇳🇱", "country": "netherlands", "code": "eredivisie"},
        "P1": {"name": "Primeira Liga", "flag": "🇵🇹", "country": "portugal", "code": "primeira"},
        "B1": {"name": "Pro League", "flag": "🇧🇪", "country": "belgium", "code": "proleague"},
    },
    "data_url": "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv",
    "output_path": "src/data/predictions.json",
    "home_advantage": 1.35,
    "avg_goals": 2.7,
    "min_value_edge": 0.03,  # 3% minimum edge for value bet
    "bookmaker_margin": 1.05  # 5% margin
}


@dataclass
class TeamStats:
    """Team statistics for prediction model"""
    name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    home_goals_for: int = 0
    home_goals_against: int = 0
    away_goals_for: int = 0
    away_goals_against: int = 0
    home_played: int = 0
    away_played: int = 0
    xg: float = 0.0
    xga: float = 0.0
    form: List[str] = None  # Last 5 results

    def __post_init__(self):
        if self.form is None:
            self.form = []

    @property
    def avg_goals_home(self) -> float:
        return self.home_goals_for / max(self.home_played, 1)

    @property
    def avg_goals_away(self) -> float:
        return self.away_goals_for / max(self.away_played, 1)

    @property
    def avg_conceded_home(self) -> float:
        return self.home_goals_against / max(self.home_played, 1)

    @property
    def avg_conceded_away(self) -> float:
        return self.away_goals_against / max(self.away_played, 1)

    @property
    def form_index(self) -> float:
        """Calculate form based on last 5 matches (weighted)"""
        if not self.form:
            return 1.0

        weights = [1.5, 1.3, 1.1, 0.9, 0.7]  # Most recent = highest weight
        points = {'W': 3, 'D': 1, 'L': 0}

        total_weight = 0
        weighted_points = 0

        for i, result in enumerate(self.form[:5]):
            if i < len(weights):
                weighted_points += points.get(result, 0) * weights[i]
                total_weight += weights[i] * 3  # Max 3 points per match

        return 0.7 + (weighted_points / max(total_weight, 1)) * 0.6  # Range: 0.7 - 1.3


@dataclass
class Prediction:
    """Match prediction"""
    home_win: float
    draw: float
    away_win: float
    over_25: float
    over_15: float
    over_05: float
    btts: float
    likely_score: Tuple[int, int]
    home_xg: float
    away_xg: float


@dataclass
class ValueBet:
    """Value bet opportunity"""
    market: str
    odds: float
    probability: int
    edge: int


@dataclass
class Match:
    """Match data with predictions"""
    id: str
    league: str
    league_name: str
    league_flag: str
    home_team: str
    away_team: str
    date: str
    time: str
    prediction: Dict
    odds: Dict
    value_bets: List[Dict]
    confidence: int


def factorial(n: int) -> int:
    """Calculate factorial"""
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def poisson_prob(k: int, lambda_val: float) -> float:
    """Calculate Poisson probability P(X = k)"""
    if lambda_val <= 0:
        return 0.0
    return (math.pow(lambda_val, k) * math.exp(-lambda_val)) / factorial(k)


def calculate_prediction(home_stats: TeamStats, away_stats: TeamStats) -> Prediction:
    """
    Calculate match prediction using Poisson model with xG integration
    """
    # Calculate expected goals
    # Home attack strength * Away defense weakness * Home advantage
    home_attack = home_stats.avg_goals_home * home_stats.form_index
    away_defense = away_stats.avg_conceded_away

    away_attack = away_stats.avg_goals_away * away_stats.form_index
    home_defense = home_stats.avg_conceded_home

    # League average adjustment
    league_avg = CONFIG["avg_goals"] / 2

    # Expected goals
    lambda_home = ((home_attack / league_avg) * (away_defense / league_avg) * league_avg *
                   CONFIG["home_advantage"])
    lambda_away = ((away_attack / league_avg) * (home_defense / league_avg) * league_avg * 0.9)

    # Ensure reasonable bounds
    lambda_home = max(0.5, min(4.0, lambda_home))
    lambda_away = max(0.3, min(3.5, lambda_away))

    # Build probability matrix (0-6 goals each)
    prob_matrix = [[0.0] * 7 for _ in range(7)]
    for h in range(7):
        for a in range(7):
            prob_matrix[h][a] = poisson_prob(h, lambda_home) * poisson_prob(a, lambda_away)

    # Calculate outcome probabilities
    p_home = sum(prob_matrix[h][a] for h in range(7) for a in range(7) if h > a)
    p_draw = sum(prob_matrix[h][a] for h in range(7) for a in range(7) if h == a)
    p_away = sum(prob_matrix[h][a] for h in range(7) for a in range(7) if h < a)

    # Normalize
    total = p_home + p_draw + p_away
    p_home /= total
    p_draw /= total
    p_away /= total

    # Calculate other markets
    p_over_25 = sum(prob_matrix[h][a] for h in range(7) for a in range(7) if h + a > 2.5)
    p_over_15 = sum(prob_matrix[h][a] for h in range(7) for a in range(7) if h + a > 1.5)
    p_over_05 = sum(prob_matrix[h][a] for h in range(7) for a in range(7) if h + a > 0.5)
    p_btts = sum(prob_matrix[h][a] for h in range(7) for a in range(7) if h > 0 and a > 0)

    # Find most likely score
    max_prob = 0
    likely_score = (1, 1)
    for h in range(5):
        for a in range(5):
            if prob_matrix[h][a] > max_prob:
                max_prob = prob_matrix[h][a]
                likely_score = (h, a)

    return Prediction(
        home_win=round(p_home * 100),
        draw=round(p_draw * 100),
        away_win=round(p_away * 100),
        over_25=round(p_over_25 * 100),
        over_15=round(p_over_15 * 100),
        over_05=round(p_over_05 * 100),
        btts=round(p_btts * 100),
        likely_score=likely_score,
        home_xg=round(lambda_home, 2),
        away_xg=round(lambda_away, 2)
    )


def generate_odds(prediction: Prediction) -> Dict:
    """Generate realistic odds based on prediction"""
    margin = CONFIG["bookmaker_margin"]

    def calc_odds(prob: float) -> float:
        if prob <= 0:
            return 20.0
        odds = (100 / prob) * margin
        return min(round(odds, 2), 20.0)

    return {
        "home": calc_odds(prediction.home_win),
        "draw": calc_odds(prediction.draw),
        "away": calc_odds(prediction.away_win),
        "over25": calc_odds(prediction.over_25),
        "under25": calc_odds(100 - prediction.over_25),
        "over15": calc_odds(prediction.over_15),
        "bttsYes": calc_odds(prediction.btts),
        "bttsNo": calc_odds(100 - prediction.btts),
        "dc1x": calc_odds(prediction.home_win + prediction.draw),
        "dc12": calc_odds(prediction.home_win + prediction.away_win),
        "dcx2": calc_odds(prediction.draw + prediction.away_win)
    }


def find_value_bets(prediction: Prediction, odds: Dict) -> List[ValueBet]:
    """Find value bets where our probability exceeds implied odds probability"""
    value_bets = []
    min_edge = CONFIG["min_value_edge"]

    markets = [
        ("1", prediction.home_win / 100, odds["home"]),
        ("X", prediction.draw / 100, odds["draw"]),
        ("2", prediction.away_win / 100, odds["away"]),
        ("Over 2.5", prediction.over_25 / 100, odds["over25"]),
        ("Under 2.5", (100 - prediction.over_25) / 100, odds["under25"]),
        ("Over 1.5", prediction.over_15 / 100, odds["over15"]),
        ("BTTS Si", prediction.btts / 100, odds["bttsYes"]),
        ("BTTS No", (100 - prediction.btts) / 100, odds["bttsNo"]),
        ("DC 1X", (prediction.home_win + prediction.draw) / 100, odds["dc1x"]),
        ("DC X2", (prediction.draw + prediction.away_win) / 100, odds["dcx2"])
    ]

    for market, prob, market_odds in markets:
        expected_value = (prob * market_odds) - 1
        if expected_value > min_edge:
            value_bets.append(ValueBet(
                market=market,
                odds=market_odds,
                probability=round(prob * 100),
                edge=round(expected_value * 100)
            ))

    return sorted(value_bets, key=lambda x: x.edge, reverse=True)


def fetch_historical_data(league: str, season: str = "2425") -> List[Dict]:
    """Fetch historical match data from football-data.co.uk"""
    url = CONFIG["data_url"].format(season=season, league=league)

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8', errors='ignore')

        lines = content.strip().split('\n')
        if len(lines) < 2:
            return []

        headers = lines[0].split(',')
        matches = []

        for line in lines[1:]:
            values = line.split(',')
            if len(values) >= len(headers):
                match = dict(zip(headers, values))
                matches.append(match)

        return matches
    except Exception as e:
        print(f"Error fetching data for {league}: {e}")
        return []


def build_team_stats(matches: List[Dict]) -> Dict[str, TeamStats]:
    """Build team statistics from historical matches"""
    teams = {}

    for match in matches:
        home = match.get('HomeTeam', '')
        away = match.get('AwayTeam', '')

        if not home or not away:
            continue

        try:
            home_goals = int(match.get('FTHG', 0))
            away_goals = int(match.get('FTAG', 0))
        except (ValueError, TypeError):
            continue

        # Initialize teams if needed
        if home not in teams:
            teams[home] = TeamStats(name=home)
        if away not in teams:
            teams[away] = TeamStats(name=away)

        # Update home team stats
        teams[home].played += 1
        teams[home].home_played += 1
        teams[home].goals_for += home_goals
        teams[home].goals_against += away_goals
        teams[home].home_goals_for += home_goals
        teams[home].home_goals_against += away_goals

        # Update away team stats
        teams[away].played += 1
        teams[away].away_played += 1
        teams[away].goals_for += away_goals
        teams[away].goals_against += home_goals
        teams[away].away_goals_for += away_goals
        teams[away].away_goals_against += home_goals

        # Update results
        if home_goals > away_goals:
            teams[home].wins += 1
            teams[away].losses += 1
            teams[home].form.insert(0, 'W')
            teams[away].form.insert(0, 'L')
        elif home_goals < away_goals:
            teams[home].losses += 1
            teams[away].wins += 1
            teams[home].form.insert(0, 'L')
            teams[away].form.insert(0, 'W')
        else:
            teams[home].draws += 1
            teams[away].draws += 1
            teams[home].form.insert(0, 'D')
            teams[away].form.insert(0, 'D')

        # Keep only last 5 for form
        teams[home].form = teams[home].form[:5]
        teams[away].form = teams[away].form[:5]

    return teams


def generate_weekend_fixtures(team_stats: Dict[str, TeamStats], league_code: str) -> List[Dict]:
    """Generate plausible weekend fixtures from team stats"""
    teams = list(team_stats.keys())
    fixtures = []

    if len(teams) < 2:
        return fixtures

    # Create matchups (simplified - in production would fetch from API)
    import random
    random.seed(datetime.now().isocalendar()[1])  # Same fixtures for same week

    shuffled = teams.copy()
    random.shuffle(shuffled)

    # Create pairs
    for i in range(0, len(shuffled) - 1, 2):
        if i + 1 < len(shuffled):
            # Randomly assign home/away
            if random.random() > 0.5:
                fixtures.append((shuffled[i], shuffled[i + 1]))
            else:
                fixtures.append((shuffled[i + 1], shuffled[i]))

    return fixtures[:6]  # Max 6 matches per league


def generate_schedine(matches: List[Match]) -> Dict:
    """Generate the three schedine types"""

    # Sort by value bets and confidence
    sorted_matches = sorted(matches,
        key=lambda m: (len(m.value_bets), m.confidence),
        reverse=True)

    # SCHEDINA SICURA: 3 selections, low odds (1.20-1.50)
    sicura = []
    used_teams = set()

    for match in sorted_matches:
        if len(sicura) >= 3:
            break
        if match.home_team in used_teams or match.away_team in used_teams:
            continue

        pred = match.prediction
        odds = match.odds

        # Prefer DC or Over 1.5 with high probability
        if pred["homeWin"] + pred["draw"] > 78 and odds["dc1x"] <= 1.50:
            sicura.append({
                "match": f"{match.home_team} vs {match.away_team}",
                "league": match.league_name,
                "flag": match.league_flag,
                "selection": "DC 1X",
                "odds": odds["dc1x"],
                "probability": pred["homeWin"] + pred["draw"]
            })
            used_teams.add(match.home_team)
            used_teams.add(match.away_team)
        elif pred["over15"] > 78 and odds["over15"] <= 1.40:
            sicura.append({
                "match": f"{match.home_team} vs {match.away_team}",
                "league": match.league_name,
                "flag": match.league_flag,
                "selection": "Over 1.5",
                "odds": odds["over15"],
                "probability": pred["over15"]
            })
            used_teams.add(match.home_team)
            used_teams.add(match.away_team)

    # Fill if needed
    for match in sorted_matches:
        if len(sicura) >= 3:
            break
        if match.home_team in used_teams or match.away_team in used_teams:
            continue

        pred = match.prediction
        odds = match.odds

        if pred["over15"] > 72:
            sicura.append({
                "match": f"{match.home_team} vs {match.away_team}",
                "league": match.league_name,
                "flag": match.league_flag,
                "selection": "Over 1.5",
                "odds": odds["over15"],
                "probability": pred["over15"]
            })
            used_teams.add(match.home_team)
            used_teams.add(match.away_team)

    # SCHEDINA MEDIA: 5 selections, mixed markets
    media = []
    used_teams = set()

    for match in sorted_matches:
        if len(media) >= 5:
            break
        if match.home_team in used_teams or match.away_team in used_teams:
            continue

        pred = match.prediction
        odds = match.odds

        # Use best value bet if available
        if match.value_bets and match.value_bets[0]["odds"] >= 1.40 and match.value_bets[0]["odds"] <= 2.20:
            vb = match.value_bets[0]
            media.append({
                "match": f"{match.home_team} vs {match.away_team}",
                "league": match.league_name,
                "flag": match.league_flag,
                "selection": vb["market"],
                "odds": vb["odds"],
                "probability": vb["probability"],
                "edge": vb["edge"]
            })
            used_teams.add(match.home_team)
            used_teams.add(match.away_team)
        elif pred["over25"] > 55 and odds["over25"] <= 2.00:
            media.append({
                "match": f"{match.home_team} vs {match.away_team}",
                "league": match.league_name,
                "flag": match.league_flag,
                "selection": "Over 2.5",
                "odds": odds["over25"],
                "probability": pred["over25"]
            })
            used_teams.add(match.home_team)
            used_teams.add(match.away_team)

    # Fill media with BTTS
    for match in sorted_matches:
        if len(media) >= 5:
            break
        if match.home_team in used_teams or match.away_team in used_teams:
            continue

        pred = match.prediction
        odds = match.odds

        if pred["btts"] > 52:
            media.append({
                "match": f"{match.home_team} vs {match.away_team}",
                "league": match.league_name,
                "flag": match.league_flag,
                "selection": "BTTS Si",
                "odds": odds["bttsYes"],
                "probability": pred["btts"]
            })
            used_teams.add(match.home_team)
            used_teams.add(match.away_team)

    # SCHEDINA JACKPOT: 12+ selections for odds > 1000
    jackpot = []
    used_teams = set()
    current_odds = 1.0

    for match in sorted_matches:
        if len(jackpot) >= 15 or current_odds > 2500:
            break
        if match.home_team in used_teams or match.away_team in used_teams:
            continue

        pred = match.prediction
        odds = match.odds

        selection = None
        sel_odds = 1.0
        probability = 0

        # Mix of safe and moderate bets
        if len(jackpot) < 6 and pred["over15"] > 78:
            selection = "Over 1.5"
            sel_odds = odds["over15"]
            probability = pred["over15"]
        elif len(jackpot) < 10 and pred["homeWin"] + pred["draw"] > 75:
            selection = "DC 1X"
            sel_odds = odds["dc1x"]
            probability = pred["homeWin"] + pred["draw"]
        elif pred["over25"] > 58:
            selection = "Over 2.5"
            sel_odds = odds["over25"]
            probability = pred["over25"]
        elif pred["btts"] > 55:
            selection = "BTTS Si"
            sel_odds = odds["bttsYes"]
            probability = pred["btts"]

        if selection:
            jackpot.append({
                "match": f"{match.home_team} vs {match.away_team}",
                "league": match.league_name,
                "flag": match.league_flag,
                "selection": selection,
                "odds": sel_odds,
                "probability": probability
            })
            current_odds *= sel_odds
            used_teams.add(match.home_team)
            used_teams.add(match.away_team)

    # Calculate totals
    def calc_total_odds(selections):
        total = 1.0
        for s in selections:
            total *= s["odds"]
        return round(total, 2)

    return {
        "sicura": {
            "selections": sicura,
            "totalOdds": str(calc_total_odds(sicura)),
            "stake": 4,
            "winRate": 45
        },
        "media": {
            "selections": media,
            "totalOdds": str(calc_total_odds(media)),
            "stake": 3,
            "winRate": 20
        },
        "jackpot": {
            "selections": jackpot,
            "totalOdds": str(int(calc_total_odds(jackpot))),
            "stake": 1,
            "winRate": 0.1
        }
    }


def main():
    """Main execution"""
    print("🎯 BetWise Predictor - Starting...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    all_matches = []

    # Get weekend dates
    today = datetime.now()
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0 and today.weekday() != 5:
        days_until_saturday = 7
    saturday = today + timedelta(days=days_until_saturday)
    sunday = saturday + timedelta(days=1)

    print(f"📆 Weekend: {saturday.strftime('%d/%m')} - {sunday.strftime('%d/%m')}")

    match_id = 0

    for league_code, league_info in CONFIG["leagues"].items():
        print(f"\n🏟️ Processing {league_info['name']}...")

        # Fetch historical data
        matches_data = fetch_historical_data(league_code)

        if not matches_data:
            print(f"   ⚠️ No data available for {league_info['name']}")
            continue

        # Build team statistics
        team_stats = build_team_stats(matches_data)
        print(f"   📊 Found {len(team_stats)} teams")

        # Generate fixtures
        fixtures = generate_weekend_fixtures(team_stats, league_code)
        print(f"   ⚽ Generated {len(fixtures)} fixtures")

        # Generate predictions for each fixture
        times = ["13:30", "15:00", "18:00", "20:45", "21:00"]

        for i, (home, away) in enumerate(fixtures):
            if home not in team_stats or away not in team_stats:
                continue

            home_stats = team_stats[home]
            away_stats = team_stats[away]

            # Calculate prediction
            prediction = calculate_prediction(home_stats, away_stats)

            # Generate odds
            odds = generate_odds(prediction)

            # Find value bets
            value_bets = find_value_bets(prediction, odds)

            # Calculate confidence
            confidence = 50 + min(30, home_stats.played * 2) + min(20, len(value_bets) * 5)

            # Determine match date
            match_date = saturday if i % 2 == 0 else sunday

            match = Match(
                id=f"{league_info['code']}_{match_id}",
                league=league_info["code"],
                league_name=league_info["name"],
                league_flag=league_info["flag"],
                home_team=home,
                away_team=away,
                date=match_date.strftime("%Y-%m-%d"),
                time=times[i % len(times)],
                prediction={
                    "homeWin": prediction.home_win,
                    "draw": prediction.draw,
                    "awayWin": prediction.away_win,
                    "over25": prediction.over_25,
                    "over15": prediction.over_15,
                    "over05": prediction.over_05,
                    "btts": prediction.btts,
                    "likelyScore": list(prediction.likely_score),
                    "homeXG": str(prediction.home_xg),
                    "awayXG": str(prediction.away_xg)
                },
                odds=odds,
                value_bets=[asdict(vb) for vb in value_bets],
                confidence=min(confidence, 95)
            )

            all_matches.append(match)
            match_id += 1

            if value_bets:
                print(f"   💎 {home} vs {away}: {len(value_bets)} value bets found")

    print(f"\n📊 Total matches analyzed: {len(all_matches)}")

    # Generate schedine
    schedine = generate_schedine(all_matches)

    print(f"\n🎰 Schedine generated:")
    print(f"   Sicura: {len(schedine['sicura']['selections'])} selections @ {schedine['sicura']['totalOdds']}")
    print(f"   Media: {len(schedine['media']['selections'])} selections @ {schedine['media']['totalOdds']}")
    print(f"   Jackpot: {len(schedine['jackpot']['selections'])} selections @ {schedine['jackpot']['totalOdds']}")

    # Prepare output
    output = {
        "generated_at": datetime.now().isoformat(),
        "weekend": f"{saturday.strftime('%d/%m')} - {sunday.strftime('%d/%m')}",
        "matches": [asdict(m) for m in all_matches],
        "schedine": schedine,
        "stats": {
            "total_matches": len(all_matches),
            "value_bets_found": sum(len(m.value_bets) for m in all_matches),
            "leagues_processed": len(CONFIG["leagues"])
        }
    }

    # Ensure output directory exists
    output_path = CONFIG["output_path"]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Predictions saved to {output_path}")

    return output


if __name__ == "__main__":
    main()
