import sqlite3
import uuid
import re
from datetime import date, timedelta
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import os
import scipy.stats as st


DB_FILE = 'rankings.db'


def generate_unique_session_id():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

connections_score_map = {
    '🟨': 1,
    '🟩': 2,
    '🟦': 3,
    '🟪': 4,
}

PUZZLE_EMOJIS = set('🟨🟩🟦🟪🟡🔵💡⬛⬜')


def clean_puzzle_input(puzzle_string):
    lines = puzzle_string.strip().split('\n')

    game = None
    game_line_idx = None
    for i, line in enumerate(lines):
        first_word = line.strip().split(' ')[0].lower()
        if first_word in ('connections', 'strands', 'wordle'):
            game = first_word
            game_line_idx = i
            break

    if game is None:
        raise ValueError('No recognized game found in message')

    try:
        if game == 'strands':
            raw = lines[game_line_idx].split('#')[1].strip().split()[0]
            puzzle_number = re.sub(r'\D', '', raw)
        if game == 'connections':
            raw = lines[game_line_idx + 1].split('#')[1].strip().split()[0]
            puzzle_number = re.sub(r'\D', '', raw)
        if game == 'wordle':
            puzzle_number = int(re.sub(r'\D', '', lines[game_line_idx].split(' ')[1].strip()))
    except (IndexError, ValueError) as e:
        raise ValueError(f'Could not parse puzzle number for {game}: {e}')

    # Reject puzzle numbers outside valid NYT ranges — filters out clones using dates etc.
    VALID_RANGES = {'wordle': (1, 2500), 'connections': (1, 10000), 'strands': (1, 10000)}
    try:
        pn_str = re.sub(r'\D', '', str(puzzle_number))
        if not pn_str:
            raise ValueError(f'No digits found in puzzle number: {puzzle_number!r}')
        pn = int(pn_str)
        lo, hi = VALID_RANGES[game]
        if not (lo <= pn <= hi):
            raise ValueError(f'Puzzle number {pn} out of valid range for {game}')
    except (ValueError, TypeError) as e:
        raise ValueError(str(e))

    skip = game_line_idx + 2 if game == 'connections' else game_line_idx + 1
    puzzle_lines = [
        l.strip() for l in lines[skip:]
        if l.strip() and all(c in PUZZLE_EMOJIS for c in l.strip())
    ]

    clean_puzzle_string = '\n'.join(puzzle_lines)
    return game, puzzle_number, clean_puzzle_string


def score_connections_puzzle(connections_string):
    score = 60
    rows = connections_string.strip().split('\n')
    ticker = 4
    for row in rows:
        if all(emoji == row[0] for emoji in row):
            score += (sum(connections_score_map[emoji] for emoji in row) * ticker)
            ticker -= 1
        else:
            score -= sum(connections_score_map[emoji] for emoji in row)
    return score


strands_score_map = {
    '🟡': 10,
    '🔵': 5,
    '💡': -5,
}


def score_strands_puzzle(strands_string):
    score = 85
    yellow_pos = len(strands_string)
    for index, emoji in enumerate(strands_string):
        if emoji == '🟡':
            score += strands_score_map[emoji]
            yellow_pos = index
        elif emoji == '🔵':
            if index < yellow_pos:
                score += 2
            elif index > yellow_pos:
                score += strands_score_map[emoji]
        elif emoji == '💡':
            score += strands_score_map[emoji]
    if score < 0:
        score = 0
    return score


wordle_score_map = {
    '⬛': 5,
    '⬜': 5,
    '🟨': 3,
    '🟩': 0,
}


def score_wordle_puzzle(wordle_string):
    score = 0
    rows = wordle_string.strip().split('\n')
    for row in rows:
        for emoji in row:
            score += wordle_score_map[emoji]
        if all(emoji == '🟩' for emoji in row):
            break
    return score


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS puzzles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_type TEXT NOT NULL,
            puzzle_number INTEGER NOT NULL,
            score INTEGER NOT NULL,
            platform TEXT NOT NULL,
            username TEXT NOT NULL,
            raw_share TEXT,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS uq_score
        ON puzzles (platform, username, game_type, puzzle_number)
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rankings (
            game_type TEXT,
            puzzle_number INTEGER,
            platform TEXT,
            ranking REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (game_type, puzzle_number, platform)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS puzzle_dates (
            game_type TEXT NOT NULL,
            puzzle_number INTEGER NOT NULL,
            puzzle_date DATE NOT NULL,
            PRIMARY KEY (game_type, puzzle_number)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS d_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_type TEXT NOT NULL,
            puzzle_number INTEGER NOT NULL,
            platform TEXT NOT NULL,
            n INTEGER NOT NULL,
            D REAL NOT NULL,
            recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def populate_puzzle_dates(game_type, start_puzzle_number, start_date, num_days):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    current_date = date.fromisoformat(start_date)
    for i in range(num_days):
        puzzle_number = start_puzzle_number + i
        puzzle_date = current_date + timedelta(days=i)
        try:
            cursor.execute('''
                INSERT INTO puzzle_dates (game_type, puzzle_number, puzzle_date)
                VALUES (?, ?, ?)
            ''', (game_type, puzzle_number, puzzle_date.isoformat()))
        except sqlite3.IntegrityError:
            continue
    conn.commit()
    conn.close()


def insert_score(game_type, puzzle_number, score, platform, username, raw_share=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO puzzles (game_type, puzzle_number, score, platform, username, raw_share)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (game_type, puzzle_number, score, platform, username, raw_share))
        conn.commit()
        inserted = True
    except sqlite3.IntegrityError:
        inserted = False
    conn.close()
    return inserted


def score_exists(platform, username, game_type, puzzle_number):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM puzzles
        WHERE platform = ? AND username = ? AND game_type = ? AND puzzle_number = ?
    ''', (platform, username, game_type, puzzle_number))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def update_ranking(game_type, puzzle_number, platform):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT score FROM puzzles WHERE game_type = ? AND puzzle_number = ? AND platform = ?
    ''', (game_type, puzzle_number, platform))
    scores = [row[0] for row in cursor.fetchall()]

    m = np.mean(scores)
    var = np.var(scores)
    gamma = 1
    var = var + gamma
    skew = st.skew(scores)

    a = 1 if game_type == 'wordle' else 15
    b = 0.015
    n = len(scores)
    skew_factor = 1 + (0.01 * skew) if n > 1 else 1
    norm_var = np.sqrt(var) / (m + gamma)

    if game_type == 'wordle':
        alpha = a * m
        beta = b * norm_var
        D = np.round((alpha + beta) / skew_factor, 5)
    else:
        alpha = a * (1 / (m + gamma))
        beta = b * norm_var
        D = np.round((alpha + beta) / skew_factor, 5)
        D = np.clip(D * 1000, 1, 10000)

    D = np.round(D, 2)

    cursor.execute('''
        INSERT INTO rankings (game_type, puzzle_number, platform, ranking)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(game_type, puzzle_number, platform) DO UPDATE SET ranking = excluded.ranking
    ''', (game_type, puzzle_number, platform, D))

    cursor.execute('''
        INSERT INTO d_history (game_type, puzzle_number, platform, n, D)
        VALUES (?, ?, ?, ?, ?)
    ''', (game_type, puzzle_number, platform, n, D))

    conn.commit()
    conn.close()


def get_ranking(game_type, puzzle_number, platform=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if platform:
        cursor.execute('''
            SELECT platform, ranking FROM rankings
            WHERE game_type = ? AND puzzle_number = ? AND platform = ?
        ''', (game_type, puzzle_number, platform))
    else:
        cursor.execute('''
            SELECT platform, ranking FROM rankings
            WHERE game_type = ? AND puzzle_number = ?
        ''', (game_type, puzzle_number))
    rank = cursor.fetchall()
    conn.close()
    return rank


def get_platform_rankings(game_type, limit=10):
    """Returns recent puzzle rankings grouped by platform for comparison."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.puzzle_number, r.platform, r.ranking,
               COALESCE(pd.puzzle_date, 'N/A') as date,
               COUNT(p.id) as n
        FROM rankings r
        JOIN puzzle_dates pd ON r.game_type = pd.game_type AND r.puzzle_number = pd.puzzle_number
        JOIN puzzles p ON p.game_type = r.game_type
                      AND p.puzzle_number = r.puzzle_number
                      AND p.platform = r.platform
        WHERE r.game_type = ?
        GROUP BY r.puzzle_number, r.platform
        ORDER BY r.puzzle_number DESC
        LIMIT ?
    ''', (game_type, limit))
    rows = cursor.fetchall()
    conn.close()
    # Restructure: {puzzle_number: {platform: {ranking, date, n}}}
    result = {}
    for puzzle_number, platform, ranking, date, n in rows:
        result.setdefault(puzzle_number, {'date': date})
        result[puzzle_number][platform] = {'ranking': ranking, 'n': n}
    return result


def get_current_rank(game_type):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.ranking, r.puzzle_number, COALESCE(pd.puzzle_date, 'N/A') as date
        FROM rankings r
        JOIN puzzle_dates pd ON r.game_type = pd.game_type AND r.puzzle_number = pd.puzzle_number
        WHERE r.game_type = ?
        ORDER BY r.ranking DESC LIMIT 5
    ''', (game_type,))
    row = cursor.fetchall()
    conn.close()
    while len(row) < 5:
        row.append((None, None, None))
    return row


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_scores_by_platform(game_type, puzzle_number=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if puzzle_number is not None:
        cursor.execute('''
            SELECT platform, puzzle_number, score FROM puzzles
            WHERE game_type = ? AND puzzle_number = ?
        ''', (game_type, puzzle_number))
    else:
        cursor.execute('''
            SELECT platform, puzzle_number, score FROM puzzles WHERE game_type = ?
        ''', (game_type,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_score_parameters(game_type):
    rank = get_current_rank(game_type)
    puzzles = [rank[i][1] for i in range(5) if rank[i][1] is not None]
    if not puzzles:
        return {}
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    query = f'''
        SELECT puzzle_number, score FROM puzzles
        WHERE puzzle_number IN ({','.join(['?'] * len(puzzles))})
        AND game_type = ?
    '''
    cursor.execute(query, tuple(puzzles) + (game_type,))
    results = cursor.fetchall()
    conn.close()
    score_dict = {}
    for puzzle_number, score in results:
        score_dict.setdefault(puzzle_number, []).append(score)
    return score_dict


def calculate_parameters(scores):
    params = {}
    for puzzle, score_list in scores.items():
        params[puzzle] = (
            np.round(np.mean(score_list), 2),
            np.round(np.std(score_list), 2),
            len(score_list),
        )
    return params


def get_recent_scores(puzzle_number=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    query = '''
        WITH recent_puzzles AS (
            SELECT DISTINCT puzzle_number FROM puzzles ORDER BY scraped_at DESC
        )
        SELECT p.game_type, p.puzzle_number, p.score, p.platform
        FROM puzzles p
        INNER JOIN recent_puzzles rp ON p.puzzle_number = rp.puzzle_number
    '''
    if puzzle_number is not None:
        query += ' WHERE p.puzzle_number = ?'
        cursor.execute(query, (puzzle_number,))
    else:
        cursor.execute(query)
    rows = cursor.fetchall()
    col_names = [d[0] for d in cursor.description]
    conn.close()
    return rows, col_names


def organize_data(rows):
    strands, connecs, wordle = {}, {}, {}
    for game, puzzle_number, score, *_ in rows:
        target = {'strands': strands, 'connections': connecs, 'wordle': wordle}.get(game)
        if target is not None:
            target.setdefault(puzzle_number, []).append(score)
    return strands, connecs, wordle


def drop_old_scores(data):
    if not data:
        return data
    max_key = max(data.keys())
    return {k: v for k, v in data.items() if k >= max_key - 4}
