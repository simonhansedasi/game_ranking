#!/usr/bin/env python3
"""
Generates per-game grouped boxplots: 5 most recent puzzles on x-axis,
one box per platform per puzzle. Saves PNGs to static/images/.

Usage: python analyze.py
"""
import sqlite3
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import re
import scipy.stats as st
import game_ranking as gr
import bayes

OUTPUT_DIR = 'static/images'
GAMES = ['wordle', 'connections', 'strands']
GAME_TITLES = {'wordle': 'Wordle', 'connections': 'Connections', 'strands': 'Strands'}
PLATFORM_COLORS = {'reddit': '#DD8452', 'bluesky': '#4C72B0'}


def fetch_scores_by_platform(game_type):
    """Returns {platform: [all scores]} for a game across all puzzles."""
    conn = sqlite3.connect(gr.DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT platform, score FROM puzzles WHERE game_type = ?', (game_type,))
    rows = cursor.fetchall()
    conn.close()
    by_platform = {}
    for platform, score in rows:
        by_platform.setdefault(platform, []).append(score)
    return by_platform


def fetch_recent_by_platform(game_type, n_puzzles=5):
    """Returns {puzzle_number: {platform: [scores]}} for the n most recent puzzles."""
    conn = sqlite3.connect(gr.DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT puzzle_number FROM puzzles
        WHERE game_type = ?
        ORDER BY puzzle_number DESC
        LIMIT ?
    ''', (game_type, n_puzzles))
    recent = [row[0] for row in cursor.fetchall()]

    if not recent:
        conn.close()
        return {}

    cursor.execute(f'''
        SELECT puzzle_number, platform, score FROM puzzles
        WHERE game_type = ? AND puzzle_number IN ({",".join("?" * len(recent))})
    ''', [game_type] + recent)
    rows = cursor.fetchall()
    conn.close()

    data = {}
    for puzzle_number, platform, score in rows:
        data.setdefault(puzzle_number, {}).setdefault(platform, []).append(score)
    return data


def plot_score_data(game_type):
    data = fetch_recent_by_platform(game_type)
    if not data:
        print(f'[analyze] No data for {game_type}, skipping.')
        return

    def puzzle_int(x):
        m = re.search(r'\d+', str(x))
        return int(m.group()) if m else 0

    puzzle_numbers = sorted(data.keys(), key=puzzle_int)  # oldest left, newest right
    platforms = sorted(set(p for d in data.values() for p in d))
    n_platforms = len(platforms)
    width = 0.5 / n_platforms
    offsets = np.linspace(-0.25 + width / 2, 0.25 - width / 2, n_platforms)

    fig, ax = plt.subplots(figsize=(5, 3))

    for i, platform in enumerate(platforms):
        color = PLATFORM_COLORS.get(platform, '#888888')
        for j, puzzle in enumerate(puzzle_numbers):
            scores = data[puzzle].get(platform)
            if not scores:
                continue
            pos = j + 1 + offsets[i]
            bp = ax.boxplot(
                scores,
                positions=[pos],
                widths=width,
                patch_artist=True,
                notch=False,
                manage_ticks=False,
                boxprops=dict(facecolor='white', color=color),
                medianprops=dict(color=color, linewidth=2),
                whiskerprops=dict(color=color, linewidth=1.5),
                capprops=dict(color=color, linewidth=1.5),
                flierprops=dict(marker='o', color=color, alpha=0.5),
            )

    # Legend
    for platform in platforms:
        color = PLATFORM_COLORS.get(platform, '#888888')
        ax.plot([], [], color=color, linewidth=3, label=platform)
    ax.legend(fontsize=9, loc='upper right')

    ax.set_xticks(range(1, len(puzzle_numbers) + 1))
    ax.set_xticklabels([str(p) for p in puzzle_numbers], fontsize=12)
    ax.set_xlabel('Puzzle Number', fontsize=14)
    ax.set_ylabel('Scores', fontsize=14)
    ax.set_title(f'{GAME_TITLES[game_type]} Recent Scores', fontsize=16)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f'{game_type}_platform_distribution.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    print(f'[analyze] saved {path}')
    return path


def plot_gaussian(game_type):
    by_platform = fetch_scores_by_platform(game_type)
    if not by_platform:
        return

    platforms = sorted(by_platform.keys())
    fig, ax = plt.subplots(figsize=(5, 3))

    for platform in platforms:
        scores = np.array(by_platform[platform])
        if len(scores) < 3:
            continue
        mu, std = scores.mean(), scores.std()
        x = np.linspace(mu - 4*std, mu + 4*std, 300)
        color = PLATFORM_COLORS.get(platform, '#888888')
        ax.plot(x, st.norm.pdf(x, mu, std), color=color, linewidth=2, label=f'{platform} (n={len(scores)})')
        ax.axvline(mu, color=color, linewidth=1, linestyle='--', alpha=0.6)

    ax.set_xlabel('Score', fontsize=14)
    ax.set_ylabel('Density', fontsize=14)
    ax.set_title(f'{GAME_TITLES[game_type]} Score Distribution', fontsize=16)
    ax.legend(fontsize=9)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f'{game_type}_gaussian.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    print(f'[analyze] saved {path}')
    return path


def plot_convergence(game_type):
    """
    For each platform, average D across all puzzles at each n milestone.
    One smooth line per platform showing how quickly D stabilizes.
    """
    conn = sqlite3.connect(gr.DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT platform, n, D FROM d_history WHERE game_type = ?
    ''', (game_type,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print(f'[analyze] No d_history for {game_type}, skipping convergence plot.')
        return

    # Group D values by (platform, n)
    from collections import defaultdict
    by_platform_n = defaultdict(lambda: defaultdict(list))
    for platform, n, D in rows:
        by_platform_n[platform][n].append(D)

    fig, ax = plt.subplots(figsize=(5, 3))
    plotted = False

    for platform, n_map in sorted(by_platform_n.items()):
        ns = sorted(n_map.keys())
        if len(ns) < 2:
            continue
        mean_ds = [np.mean(n_map[n]) for n in ns]
        color = PLATFORM_COLORS.get(platform, '#888888')
        ax.plot(ns, mean_ds, color=color, linewidth=2, label=platform)
        plotted = True

    if not plotted:
        plt.close(fig)
        print(f'[analyze] Not enough d_history to plot convergence for {game_type}.')
        return

    ax.set_xlabel('n (scores)', fontsize=14)
    ax.set_ylabel('D (avg across puzzles)', fontsize=14)
    ax.set_title(f'{GAME_TITLES[game_type]} D Convergence', fontsize=16)
    ax.legend(fontsize=9)
    ax.grid(linestyle='--', alpha=0.6)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f'{game_type}_convergence.png')
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)
    print(f'[analyze] saved {path}')
    return path


def main():
    for game in GAMES:
        plot_score_data(game)
        plot_gaussian(game)
        plot_convergence(game)


if __name__ == '__main__':
    main()
