const BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? `http://${window.location.hostname}:5005`
    : 'https://game-ranking.duckdns.org';

const GAMES = ['wordle', 'connections', 'strands'];

function loadPlot(game) {
    fetch(`${BASE_URL}/plots/${game}`, {})
        .then(r => r.json())
        .then(data => {
            const dist  = document.getElementById(`${game}-distribution`);
            const gauss = document.getElementById(`${game}-gaussian`);
            const conv  = document.getElementById(`${game}-convergence`);
            if (dist)  dist.src  = `${BASE_URL}${data.distribution}`;
            if (gauss) gauss.src = `${BASE_URL}${data.gaussian}`;
            if (conv)  conv.src  = `${BASE_URL}${data.convergence}`;
        })
        .catch(err => console.error(`Failed to load ${game} plot:`, err));
}

function loadRankings(game) {
    fetch(`${BASE_URL}/rankings/${game}`, {})
        .then(r => r.json())
        .then(entries => {
            const container = document.getElementById(`${game}-rankings`);
            if (!container || !entries.length) return;

            const platforms = [...new Set(
                entries.flatMap(e => Object.keys(e).filter(k => !['puzzle','date','comparison'].includes(k)))
            )].sort();

            const hasCmp = entries.some(e => e.comparison);

            const headerCells = [
                'Puzzle', 'Date',
                ...platforms.flatMap(p => [`${p} D`, `${p} D*`, `${p} n`]),
                ...(hasCmp ? ['BS&minus;Reddit', 'P(BS higher)'] : []),
            ];
            const header = headerCells.map(h => `<th>${h}</th>`).join('');

            const sorted = [...entries].sort((a, b) => {
                const avgD = e => {
                    const vals = platforms.map(p => e[p]?.D).filter(v => v != null);
                    return vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : 0;
                };
                return avgD(b) - avgD(a);
            }).slice(0, 5);

            const rows = sorted.map(entry => {
                const cells = [
                    `<td>${entry.puzzle}</td>`,
                    `<td>${entry.date}</td>`,
                    ...platforms.flatMap(p => {
                        const s = entry[p];
                        return s
                            ? [`<td>${s.D}</td>`, `<td>${s.D_shrunk}</td>`, `<td>${s.n}</td>`]
                            : [`<td>-</td>`, `<td>-</td>`, `<td>-</td>`];
                    }),
                    ...(hasCmp ? [
                        entry.comparison
                            ? `<td>${entry.comparison.diff > 0 ? '+' : ''}${entry.comparison.diff}</td>`
                            : `<td>-</td>`,
                        entry.comparison
                            ? `<td>${(entry.comparison.p_bluesky_higher * 100).toFixed(0)}%</td>`
                            : `<td>-</td>`,
                    ] : []),
                ].join('');
                return `<tr>${cells}</tr>`;
            }).join('');

            container.innerHTML = `<table><thead><tr>${header}</tr></thead><tbody>${rows}</tbody></table>`;
        })
        .catch(err => console.error(`Failed to load ${game} rankings:`, err));
}

window.onload = () => GAMES.forEach(game => {
    loadPlot(game);
    loadRankings(game);
});
