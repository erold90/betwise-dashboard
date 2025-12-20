// BetWise Dashboard - Main Application Logic

// Configuration
const CONFIG = {
    dataUrl: 'src/data/predictions.json',
    updateDay: 5, // Friday
    leagues: {
        'premier': { name: 'Premier League', flag: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', code: 'E0' },
        'laliga': { name: 'La Liga', flag: '🇪🇸', code: 'SP1' },
        'seriea': { name: 'Serie A', flag: '🇮🇹', code: 'I1' },
        'bundesliga': { name: 'Bundesliga', flag: '🇩🇪', code: 'D1' },
        'ligue1': { name: 'Ligue 1', flag: '🇫🇷', code: 'F1' },
        'eredivisie': { name: 'Eredivisie', flag: '🇳🇱', code: 'N1' },
        'primeira': { name: 'Primeira Liga', flag: '🇵🇹', code: 'P1' }
    }
};

// State
let state = {
    predictions: null,
    schedine: null,
    currentLeague: 'all',
    myBets: [],
    customSelections: []
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadLocalData();
    loadPredictions();
    initChart();
    setupEventListeners();
});

// Load predictions from JSON
async function loadPredictions() {
    try {
        const response = await fetch(CONFIG.dataUrl);
        if (!response.ok) {
            // If no data yet, load demo data
            loadDemoData();
            return;
        }
        const data = await response.json();
        state.predictions = data.matches;
        state.schedine = data.schedine;
        updateUI();
    } catch (error) {
        console.log('Loading demo data...');
        loadDemoData();
    }
}

// Demo data for initial display
function loadDemoData() {
    const demoData = generateDemoData();
    state.predictions = demoData.matches;
    state.schedine = demoData.schedine;
    updateUI();
}

// Generate demo predictions
function generateDemoData() {
    const teams = {
        premier: [
            { home: 'Liverpool', away: 'Tottenham', homeStrength: 85, awayStrength: 75 },
            { home: 'Arsenal', away: 'Brighton', homeStrength: 82, awayStrength: 68 },
            { home: 'Man City', away: 'Crystal Palace', homeStrength: 90, awayStrength: 60 },
            { home: 'Chelsea', away: 'Brentford', homeStrength: 78, awayStrength: 65 }
        ],
        laliga: [
            { home: 'Real Madrid', away: 'Getafe', homeStrength: 88, awayStrength: 55 },
            { home: 'Barcelona', away: 'Las Palmas', homeStrength: 86, awayStrength: 52 },
            { home: 'Atletico Madrid', away: 'Sevilla', homeStrength: 80, awayStrength: 70 }
        ],
        seriea: [
            { home: 'Inter', away: 'Venezia', homeStrength: 85, awayStrength: 48 },
            { home: 'Napoli', away: 'Monza', homeStrength: 82, awayStrength: 55 },
            { home: 'Juventus', away: 'Cagliari', homeStrength: 80, awayStrength: 58 },
            { home: 'Milan', away: 'Verona', homeStrength: 78, awayStrength: 52 }
        ],
        bundesliga: [
            { home: 'Bayern Monaco', away: 'Hoffenheim', homeStrength: 88, awayStrength: 62 },
            { home: 'Dortmund', away: 'Union Berlin', homeStrength: 80, awayStrength: 65 },
            { home: 'Leverkusen', away: 'Mainz', homeStrength: 84, awayStrength: 60 }
        ],
        ligue1: [
            { home: 'PSG', away: 'Montpellier', homeStrength: 90, awayStrength: 50 },
            { home: 'Monaco', away: 'Lens', homeStrength: 75, awayStrength: 70 },
            { home: 'Marsiglia', away: 'Nantes', homeStrength: 76, awayStrength: 58 }
        ],
        eredivisie: [
            { home: 'PSV', away: 'Twente', homeStrength: 82, awayStrength: 68 },
            { home: 'Ajax', away: 'Utrecht', homeStrength: 80, awayStrength: 65 }
        ],
        primeira: [
            { home: 'Benfica', away: 'Braga', homeStrength: 82, awayStrength: 72 },
            { home: 'Porto', away: 'Guimaraes', homeStrength: 80, awayStrength: 65 }
        ]
    };

    const matches = [];
    const today = new Date();
    const saturday = new Date(today);
    saturday.setDate(today.getDate() + (6 - today.getDay()));
    const sunday = new Date(saturday);
    sunday.setDate(saturday.getDate() + 1);

    Object.entries(teams).forEach(([league, leagueTeams]) => {
        leagueTeams.forEach((match, idx) => {
            const prediction = calculatePrediction(match.homeStrength, match.awayStrength);
            const isWeekend = idx % 2 === 0;
            const matchDate = isWeekend ? saturday : sunday;
            const hours = [13, 15, 18, 20, 21];

            matches.push({
                id: `${league}_${idx}`,
                league: league,
                leagueName: CONFIG.leagues[league].name,
                leagueFlag: CONFIG.leagues[league].flag,
                homeTeam: match.home,
                awayTeam: match.away,
                date: matchDate.toISOString().split('T')[0],
                time: `${hours[idx % hours.length]}:00`,
                prediction: prediction,
                odds: generateOdds(prediction),
                valueBets: findValueBets(prediction, generateOdds(prediction)),
                confidence: Math.round(50 + Math.random() * 40)
            });
        });
    });

    // Generate schedine
    const schedine = generateSchedine(matches);

    return { matches, schedine };
}

// Poisson-based prediction calculation
function calculatePrediction(homeStrength, awayStrength) {
    // Simplified Poisson model
    const homeAdvantage = 1.35;
    const avgGoals = 2.7;

    const homeExpected = (homeStrength / 100) * avgGoals * homeAdvantage;
    const awayExpected = (awayStrength / 100) * avgGoals * 0.9;

    // Calculate probabilities using Poisson distribution
    const probMatrix = [];
    for (let h = 0; h <= 6; h++) {
        probMatrix[h] = [];
        for (let a = 0; a <= 6; a++) {
            probMatrix[h][a] = poissonProb(h, homeExpected) * poissonProb(a, awayExpected);
        }
    }

    let pHome = 0, pDraw = 0, pAway = 0;
    let pOver25 = 0, pBTTS = 0;
    let pOver15 = 0, pOver05 = 0;

    for (let h = 0; h <= 6; h++) {
        for (let a = 0; a <= 6; a++) {
            const p = probMatrix[h][a];
            if (h > a) pHome += p;
            else if (h === a) pDraw += p;
            else pAway += p;

            if (h + a > 2.5) pOver25 += p;
            if (h + a > 1.5) pOver15 += p;
            if (h + a > 0.5) pOver05 += p;
            if (h > 0 && a > 0) pBTTS += p;
        }
    }

    // Find most likely score
    let maxProb = 0, likelyScore = [1, 1];
    for (let h = 0; h <= 4; h++) {
        for (let a = 0; a <= 4; a++) {
            if (probMatrix[h][a] > maxProb) {
                maxProb = probMatrix[h][a];
                likelyScore = [h, a];
            }
        }
    }

    return {
        homeWin: Math.round(pHome * 100),
        draw: Math.round(pDraw * 100),
        awayWin: Math.round(pAway * 100),
        over25: Math.round(pOver25 * 100),
        over15: Math.round(pOver15 * 100),
        over05: Math.round(pOver05 * 100),
        btts: Math.round(pBTTS * 100),
        likelyScore: likelyScore,
        homeXG: homeExpected.toFixed(2),
        awayXG: awayExpected.toFixed(2)
    };
}

// Poisson probability function
function poissonProb(k, lambda) {
    return (Math.pow(lambda, k) * Math.exp(-lambda)) / factorial(k);
}

function factorial(n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}

// Generate realistic odds based on prediction
function generateOdds(prediction) {
    const margin = 1.05; // 5% bookmaker margin

    const homeOdds = Math.round((100 / prediction.homeWin * margin) * 100) / 100;
    const drawOdds = Math.round((100 / prediction.draw * margin) * 100) / 100;
    const awayOdds = Math.round((100 / prediction.awayWin * margin) * 100) / 100;
    const over25Odds = Math.round((100 / prediction.over25 * margin) * 100) / 100;
    const under25Odds = Math.round((100 / (100 - prediction.over25) * margin) * 100) / 100;
    const bttsYesOdds = Math.round((100 / prediction.btts * margin) * 100) / 100;
    const bttsNoOdds = Math.round((100 / (100 - prediction.btts) * margin) * 100) / 100;
    const over15Odds = Math.round((100 / prediction.over15 * margin) * 100) / 100;

    // Double chance
    const dc1xOdds = Math.round((100 / (prediction.homeWin + prediction.draw) * margin) * 100) / 100;
    const dc12Odds = Math.round((100 / (prediction.homeWin + prediction.awayWin) * margin) * 100) / 100;
    const dcx2Odds = Math.round((100 / (prediction.draw + prediction.awayWin) * margin) * 100) / 100;

    return {
        home: Math.min(homeOdds, 15),
        draw: Math.min(drawOdds, 10),
        away: Math.min(awayOdds, 15),
        over25: Math.min(over25Odds, 4),
        under25: Math.min(under25Odds, 4),
        over15: Math.min(over15Odds, 2),
        bttsYes: Math.min(bttsYesOdds, 3),
        bttsNo: Math.min(bttsNoOdds, 3),
        dc1x: Math.min(dc1xOdds, 3),
        dc12: Math.min(dc12Odds, 2),
        dcx2: Math.min(dcx2Odds, 3)
    };
}

// Find value bets
function findValueBets(prediction, odds) {
    const valueBets = [];
    const minEdge = 0.03; // 3% minimum edge

    // Check each market
    const markets = [
        { name: '1', prob: prediction.homeWin / 100, odds: odds.home },
        { name: 'X', prob: prediction.draw / 100, odds: odds.draw },
        { name: '2', prob: prediction.awayWin / 100, odds: odds.away },
        { name: 'Over 2.5', prob: prediction.over25 / 100, odds: odds.over25 },
        { name: 'Under 2.5', prob: (100 - prediction.over25) / 100, odds: odds.under25 },
        { name: 'Over 1.5', prob: prediction.over15 / 100, odds: odds.over15 },
        { name: 'BTTS Si', prob: prediction.btts / 100, odds: odds.bttsYes },
        { name: 'BTTS No', prob: (100 - prediction.btts) / 100, odds: odds.bttsNo },
        { name: 'DC 1X', prob: (prediction.homeWin + prediction.draw) / 100, odds: odds.dc1x },
        { name: 'DC X2', prob: (prediction.draw + prediction.awayWin) / 100, odds: odds.dcx2 }
    ];

    markets.forEach(market => {
        const expectedValue = (market.prob * market.odds) - 1;
        if (expectedValue > minEdge) {
            valueBets.push({
                market: market.name,
                odds: market.odds,
                probability: Math.round(market.prob * 100),
                edge: Math.round(expectedValue * 100)
            });
        }
    });

    return valueBets.sort((a, b) => b.edge - a.edge);
}

// Generate schedine
function generateSchedine(matches) {
    // Sort by value and confidence
    const sortedMatches = [...matches].sort((a, b) => {
        const aValue = a.valueBets.length > 0 ? a.valueBets[0].edge : 0;
        const bValue = b.valueBets.length > 0 ? b.valueBets[0].edge : 0;
        return bValue - aValue;
    });

    // Schedina Sicura: 3 selezioni, quote basse (1.20-1.50)
    const sicura = [];
    sortedMatches.forEach(match => {
        if (sicura.length >= 3) return;

        // Prefer DC or Over 1.5 with high probability
        if (match.prediction.homeWin + match.prediction.draw > 80 && match.odds.dc1x <= 1.50) {
            sicura.push({
                match: `${match.homeTeam} vs ${match.awayTeam}`,
                league: match.leagueName,
                flag: match.leagueFlag,
                selection: 'DC 1X',
                odds: match.odds.dc1x,
                probability: match.prediction.homeWin + match.prediction.draw
            });
        } else if (match.prediction.over15 > 80 && match.odds.over15 <= 1.40) {
            sicura.push({
                match: `${match.homeTeam} vs ${match.awayTeam}`,
                league: match.leagueName,
                flag: match.leagueFlag,
                selection: 'Over 1.5',
                odds: match.odds.over15,
                probability: match.prediction.over15
            });
        }
    });

    // Fill with safe bets if needed
    if (sicura.length < 3) {
        sortedMatches.forEach(match => {
            if (sicura.length >= 3) return;
            if (!sicura.find(s => s.match.includes(match.homeTeam))) {
                if (match.prediction.over15 > 75) {
                    sicura.push({
                        match: `${match.homeTeam} vs ${match.awayTeam}`,
                        league: match.leagueName,
                        flag: match.leagueFlag,
                        selection: 'Over 1.5',
                        odds: match.odds.over15,
                        probability: match.prediction.over15
                    });
                }
            }
        });
    }

    // Schedina Media: 5 selezioni, mix di mercati
    const media = [];
    sortedMatches.forEach(match => {
        if (media.length >= 5) return;
        if (media.find(s => s.match.includes(match.homeTeam))) return;

        const bestValue = match.valueBets[0];
        if (bestValue && bestValue.odds >= 1.40 && bestValue.odds <= 2.00) {
            media.push({
                match: `${match.homeTeam} vs ${match.awayTeam}`,
                league: match.leagueName,
                flag: match.leagueFlag,
                selection: bestValue.market,
                odds: bestValue.odds,
                probability: bestValue.probability,
                edge: bestValue.edge
            });
        } else if (match.prediction.over25 > 55 && match.odds.over25 <= 1.90) {
            media.push({
                match: `${match.homeTeam} vs ${match.awayTeam}`,
                league: match.leagueName,
                flag: match.leagueFlag,
                selection: 'Over 2.5',
                odds: match.odds.over25,
                probability: match.prediction.over25
            });
        }
    });

    // Fill media if needed
    if (media.length < 5) {
        sortedMatches.forEach(match => {
            if (media.length >= 5) return;
            if (!media.find(s => s.match.includes(match.homeTeam))) {
                if (match.prediction.btts > 55) {
                    media.push({
                        match: `${match.homeTeam} vs ${match.awayTeam}`,
                        league: match.leagueName,
                        flag: match.leagueFlag,
                        selection: 'BTTS Si',
                        odds: match.odds.bttsYes,
                        probability: match.prediction.btts
                    });
                }
            }
        });
    }

    // Schedina Jackpot: 12+ selezioni per quota > 1000
    const jackpot = [];
    let currentQuota = 1;

    sortedMatches.forEach(match => {
        if (jackpot.length >= 15 || currentQuota > 2500) return;
        if (jackpot.find(s => s.match.includes(match.homeTeam))) return;

        // For jackpot, mix safe and risky bets
        let selection, odds, probability;

        if (jackpot.length < 6 && match.prediction.over15 > 80) {
            selection = 'Over 1.5';
            odds = match.odds.over15;
            probability = match.prediction.over15;
        } else if (jackpot.length < 10 && match.prediction.homeWin + match.prediction.draw > 75) {
            selection = 'DC 1X';
            odds = match.odds.dc1x;
            probability = match.prediction.homeWin + match.prediction.draw;
        } else if (match.prediction.over25 > 60) {
            selection = 'Over 2.5';
            odds = match.odds.over25;
            probability = match.prediction.over25;
        } else if (match.prediction.btts > 55) {
            selection = 'BTTS Si';
            odds = match.odds.bttsYes;
            probability = match.prediction.btts;
        }

        if (selection) {
            jackpot.push({
                match: `${match.homeTeam} vs ${match.awayTeam}`,
                league: match.leagueName,
                flag: match.leagueFlag,
                selection,
                odds,
                probability
            });
            currentQuota *= odds;
        }
    });

    return {
        sicura: {
            selections: sicura,
            totalOdds: sicura.reduce((acc, s) => acc * s.odds, 1).toFixed(2),
            stake: 4,
            winRate: 45
        },
        media: {
            selections: media,
            totalOdds: media.reduce((acc, s) => acc * s.odds, 1).toFixed(2),
            stake: 3,
            winRate: 20
        },
        jackpot: {
            selections: jackpot,
            totalOdds: jackpot.reduce((acc, s) => acc * s.odds, 1).toFixed(0),
            stake: 1,
            winRate: 0.1
        }
    };
}

// Update UI
function updateUI() {
    updateStats();
    updateSchedineCards();
    updateMatches();
    updateBetsTable();
    updateChart();
}

// Update stats cards
function updateStats() {
    if (!state.predictions) return;

    document.getElementById('totalMatches').textContent = state.predictions.length;

    const valueBetsCount = state.predictions.reduce((acc, m) => acc + m.valueBets.length, 0);
    document.getElementById('valueBets').textContent = valueBetsCount;

    // Calculate from my bets
    const bets = state.myBets.filter(b => b.result !== 'pending');
    const wonBets = bets.filter(b => b.result === 'won');
    const winRate = bets.length > 0 ? Math.round((wonBets.length / bets.length) * 100) : 0;
    document.getElementById('winRate').textContent = winRate + '%';

    const totalStaked = state.myBets.reduce((acc, b) => acc + b.stake, 0);
    const totalWon = state.myBets.filter(b => b.result === 'won').reduce((acc, b) => acc + (b.stake * b.odds), 0);
    const roi = totalStaked > 0 ? Math.round(((totalWon - totalStaked) / totalStaked) * 100) : 0;
    document.getElementById('totalROI').textContent = (roi >= 0 ? '+' : '') + roi + '%';

    // Update weekend date
    const today = new Date();
    const saturday = new Date(today);
    saturday.setDate(today.getDate() + (6 - today.getDay()));
    const sunday = new Date(saturday);
    sunday.setDate(saturday.getDate() + 1);
    document.getElementById('weekendDate').textContent =
        `${saturday.getDate()}/${saturday.getMonth() + 1} - ${sunday.getDate()}/${sunday.getMonth() + 1}`;

    document.getElementById('lastUpdate').textContent = new Date().toLocaleString('it-IT');
}

// Update schedine cards
function updateSchedineCards() {
    if (!state.schedine) return;

    const { sicura, media, jackpot } = state.schedine;

    document.getElementById('quotaSicura').textContent = sicura.totalOdds;
    document.getElementById('vincitaSicura').textContent = `Vincita: €${(sicura.stake * sicura.totalOdds).toFixed(2)}`;

    document.getElementById('quotaMedia').textContent = media.totalOdds;
    document.getElementById('vincitaMedia').textContent = `Vincita: €${(media.stake * media.totalOdds).toFixed(2)}`;

    document.getElementById('quotaJackpot').textContent = jackpot.totalOdds;
    document.getElementById('vincitaJackpot').textContent = `Vincita: €${jackpot.totalOdds}+`;
}

// Update matches display
function updateMatches() {
    const container = document.getElementById('matchesContainer');
    if (!state.predictions) return;

    let matches = state.predictions;
    if (state.currentLeague !== 'all') {
        matches = matches.filter(m => m.league === state.currentLeague);
    }

    container.innerHTML = matches.map(match => `
        <div class="match-card glass-card rounded-xl p-5 cursor-pointer" onclick="showMatchDetail('${match.id}')">
            <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-2">
                    <span>${match.leagueFlag}</span>
                    <span class="text-sm text-gray-400">${match.leagueName}</span>
                </div>
                <div class="text-sm text-gray-400">
                    ${match.date} ${match.time}
                </div>
            </div>

            <div class="flex items-center justify-between mb-4">
                <div class="flex-1">
                    <p class="font-bold text-lg">${match.homeTeam}</p>
                    <p class="text-gray-400 text-sm">Casa</p>
                </div>
                <div class="text-center px-4">
                    <p class="text-2xl font-bold text-gray-500">vs</p>
                    <p class="text-xs text-gray-600">Pred: ${match.prediction.likelyScore[0]}-${match.prediction.likelyScore[1]}</p>
                </div>
                <div class="flex-1 text-right">
                    <p class="font-bold text-lg">${match.awayTeam}</p>
                    <p class="text-gray-400 text-sm">Trasferta</p>
                </div>
            </div>

            <div class="grid grid-cols-3 gap-2 mb-4">
                <div class="text-center p-2 rounded-lg ${match.prediction.homeWin > 50 ? 'bg-green-600/20' : 'bg-dark-700'}">
                    <p class="text-xs text-gray-400">1</p>
                    <p class="font-bold ${match.prediction.homeWin > 50 ? 'text-green-400' : ''}">${match.prediction.homeWin}%</p>
                    <p class="text-xs text-gray-500">@${match.odds.home}</p>
                </div>
                <div class="text-center p-2 rounded-lg ${match.prediction.draw > 35 ? 'bg-yellow-600/20' : 'bg-dark-700'}">
                    <p class="text-xs text-gray-400">X</p>
                    <p class="font-bold ${match.prediction.draw > 35 ? 'text-yellow-400' : ''}">${match.prediction.draw}%</p>
                    <p class="text-xs text-gray-500">@${match.odds.draw}</p>
                </div>
                <div class="text-center p-2 rounded-lg ${match.prediction.awayWin > 50 ? 'bg-blue-600/20' : 'bg-dark-700'}">
                    <p class="text-xs text-gray-400">2</p>
                    <p class="font-bold ${match.prediction.awayWin > 50 ? 'text-blue-400' : ''}">${match.prediction.awayWin}%</p>
                    <p class="text-xs text-gray-500">@${match.odds.away}</p>
                </div>
            </div>

            <div class="flex items-center justify-between text-sm">
                <div class="flex items-center gap-4">
                    <span class="text-gray-400">O2.5: <span class="${match.prediction.over25 > 55 ? 'text-green-400' : 'text-white'}">${match.prediction.over25}%</span></span>
                    <span class="text-gray-400">BTTS: <span class="${match.prediction.btts > 55 ? 'text-green-400' : 'text-white'}">${match.prediction.btts}%</span></span>
                </div>
                ${match.valueBets.length > 0 ? `
                    <span class="value-badge px-2 py-1 rounded-full bg-green-600/30 text-green-400 text-xs">
                        💎 ${match.valueBets.length} Value
                    </span>
                ` : ''}
            </div>

            ${match.valueBets.length > 0 ? `
                <div class="mt-3 pt-3 border-t border-gray-700">
                    <p class="text-xs text-gray-500 mb-2">Value Bets:</p>
                    <div class="flex flex-wrap gap-2">
                        ${match.valueBets.slice(0, 3).map(vb => `
                            <span class="px-2 py-1 rounded bg-green-600/20 text-green-400 text-xs">
                                ${vb.market} @${vb.odds} (+${vb.edge}%)
                            </span>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `).join('');
}

// Show schedina modal
function showSchedina(type) {
    if (!state.schedine) return;

    const modal = document.getElementById('schedinaModal');
    const title = document.getElementById('modalTitle');
    const content = document.getElementById('modalContent');
    const quota = document.getElementById('modalQuota');
    const win = document.getElementById('modalWin');

    const schedina = state.schedine[type];
    const colors = {
        sicura: { title: 'Schedina Sicura 🟢', color: 'green' },
        media: { title: 'Schedina Media 🟡', color: 'yellow' },
        jackpot: { title: 'Schedina Jackpot 🔴', color: 'red' }
    };

    title.textContent = colors[type].title;
    quota.textContent = schedina.totalOdds;
    win.textContent = `€${(schedina.stake * parseFloat(schedina.totalOdds)).toFixed(2)}`;

    content.innerHTML = schedina.selections.map((sel, idx) => `
        <div class="p-4 rounded-lg bg-dark-700 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <span class="w-8 h-8 rounded-full bg-${colors[type].color}-600/30 text-${colors[type].color}-400 flex items-center justify-center font-bold">
                    ${idx + 1}
                </span>
                <div>
                    <p class="font-medium">${sel.match}</p>
                    <p class="text-sm text-gray-400">${sel.flag} ${sel.league}</p>
                </div>
            </div>
            <div class="text-right">
                <p class="font-bold text-${colors[type].color}-400">${sel.selection}</p>
                <p class="text-sm text-gray-400">@${sel.odds} (${sel.probability}%)</p>
            </div>
        </div>
    `).join('');

    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

// Show custom builder
function showCustomBuilder() {
    alert('Custom Builder - Coming Soon!\n\nPotrai selezionare le partite e creare la tua schedina personalizzata.');
}

// Close modal
function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
    document.getElementById(modalId).classList.remove('flex');
}

// Copy schedina
function copySchedina() {
    const content = document.getElementById('modalContent').innerText;
    const quota = document.getElementById('modalQuota').innerText;
    const text = `🎯 BetWise Schedina\n\n${content}\n\nQuota Totale: ${quota}`;

    navigator.clipboard.writeText(text).then(() => {
        alert('Schedina copiata negli appunti!');
    });
}

// Filter by league
function filterLeague(league) {
    state.currentLeague = league;

    // Update tabs
    document.querySelectorAll('#leagueTabs button').forEach(btn => {
        btn.classList.remove('tab-active');
        btn.classList.add('bg-dark-700');
    });
    event.target.classList.add('tab-active');
    event.target.classList.remove('bg-dark-700');

    updateMatches();
}

// Refresh data
function refreshData() {
    loadPredictions();
}

// Local storage functions
function loadLocalData() {
    const bets = localStorage.getItem('betwise_bets');
    if (bets) {
        state.myBets = JSON.parse(bets);
    }
}

function saveLocalData() {
    localStorage.setItem('betwise_bets', JSON.stringify(state.myBets));
}

// Show add bet modal
function showAddBetModal() {
    document.getElementById('addBetModal').classList.remove('hidden');
    document.getElementById('addBetModal').classList.add('flex');
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('addBetForm').addEventListener('submit', (e) => {
        e.preventDefault();

        const bet = {
            id: Date.now(),
            date: new Date().toISOString().split('T')[0],
            type: document.getElementById('betType').value,
            selections: parseInt(document.getElementById('betSelections').value),
            odds: parseFloat(document.getElementById('betOdds').value),
            stake: parseFloat(document.getElementById('betStake').value),
            result: document.getElementById('betResult').value
        };

        state.myBets.unshift(bet);
        saveLocalData();
        updateUI();
        closeModal('addBetModal');

        // Reset form
        document.getElementById('addBetForm').reset();
    });
}

// Update bets table
function updateBetsTable() {
    const tbody = document.getElementById('betsTableBody');

    if (state.myBets.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="px-4 py-8 text-center text-gray-500">
                    Nessuna scommessa registrata. Clicca "Aggiungi Scommessa" per iniziare.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = state.myBets.map(bet => {
        const pl = bet.result === 'won' ? (bet.stake * bet.odds - bet.stake).toFixed(2) :
                   bet.result === 'lost' ? (-bet.stake).toFixed(2) : '-';
        const plClass = bet.result === 'won' ? 'text-green-400' :
                       bet.result === 'lost' ? 'text-red-400' : 'text-gray-400';
        const resultBadge = bet.result === 'won' ? 'bg-green-600/30 text-green-400' :
                          bet.result === 'lost' ? 'bg-red-600/30 text-red-400' :
                          'bg-yellow-600/30 text-yellow-400';

        return `
            <tr class="hover:bg-dark-700">
                <td class="px-4 py-3">${bet.date}</td>
                <td class="px-4 py-3 capitalize">${bet.type}</td>
                <td class="px-4 py-3">${bet.selections}</td>
                <td class="px-4 py-3">${bet.odds.toFixed(2)}</td>
                <td class="px-4 py-3">€${bet.stake.toFixed(2)}</td>
                <td class="px-4 py-3">
                    <span class="px-2 py-1 rounded-full text-xs ${resultBadge}">
                        ${bet.result === 'pending' ? 'In Attesa' : bet.result === 'won' ? 'Vinta' : 'Persa'}
                    </span>
                </td>
                <td class="px-4 py-3 ${plClass}">${pl !== '-' ? '€' + pl : pl}</td>
            </tr>
        `;
    }).join('');

    // Update tracking stats
    const bets = state.myBets.filter(b => b.result !== 'pending');
    document.getElementById('totalPlayed').textContent = bets.length;
    document.getElementById('totalWon').textContent = bets.filter(b => b.result === 'won').length;
    document.getElementById('totalStaked').textContent = '€' + state.myBets.reduce((acc, b) => acc + b.stake, 0).toFixed(2);

    const totalWonAmount = state.myBets.filter(b => b.result === 'won').reduce((acc, b) => acc + (b.stake * b.odds), 0);
    document.getElementById('totalWonAmount').textContent = '€' + totalWonAmount.toFixed(2);

    const totalStaked = state.myBets.reduce((acc, b) => acc + b.stake, 0);
    const profitLoss = totalWonAmount - totalStaked;
    const plElement = document.getElementById('profitLoss');
    plElement.textContent = (profitLoss >= 0 ? '+' : '') + '€' + profitLoss.toFixed(2);
    plElement.className = 'font-bold text-xl ' + (profitLoss >= 0 ? 'text-green-400' : 'text-red-400');
}

// Initialize chart
let performanceChart = null;

function initChart() {
    const ctx = document.getElementById('performanceChart').getContext('2d');

    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Sett 1', 'Sett 2', 'Sett 3', 'Sett 4', 'Sett 5', 'Sett 6', 'Sett 7', 'Sett 8'],
            datasets: [{
                label: 'Profitto/Perdita (€)',
                data: [0, 0, 0, 0, 0, 0, 0, 0],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#9ca3af'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#9ca3af'
                    }
                }
            }
        }
    });
}

function updateChart() {
    if (!performanceChart) return;

    // Group bets by week and calculate P/L
    const weeklyPL = [0, 0, 0, 0, 0, 0, 0, 0];
    // For demo, we'll use random data if no bets
    if (state.myBets.length === 0) {
        performanceChart.data.datasets[0].data = [2, -3, 5, -1, 8, 4, -2, 6];
    } else {
        // Calculate actual weekly P/L
        let runningTotal = 0;
        state.myBets.slice(0, 8).reverse().forEach((bet, idx) => {
            if (bet.result === 'won') {
                runningTotal += (bet.stake * bet.odds - bet.stake);
            } else if (bet.result === 'lost') {
                runningTotal -= bet.stake;
            }
            weeklyPL[idx] = runningTotal;
        });
        performanceChart.data.datasets[0].data = weeklyPL;
    }

    performanceChart.update();
}

// Show match detail (placeholder)
function showMatchDetail(matchId) {
    const match = state.predictions.find(m => m.id === matchId);
    if (!match) return;

    alert(`Dettaglio Partita:\n\n${match.homeTeam} vs ${match.awayTeam}\n\nxG Casa: ${match.prediction.homeXG}\nxG Trasferta: ${match.prediction.awayXG}\n\nPredizione: ${match.prediction.likelyScore[0]}-${match.prediction.likelyScore[1]}\n\nConfidenza: ${match.confidence}%`);
}
