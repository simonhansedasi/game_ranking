import sqlite3
import uuid
from datetime import date, timedelta
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import os
import scipy.stats as st







def generate_unique_session_id():
    return str(uuid.uuid4())


connections_score_map = {
    '🟨' : 1,
    '🟩' : 2,
    '🟦' : 3,
    '🟪' : 4
}
def clean_puzzle_input(puzzle_string):

    lines = puzzle_string.strip().split("\n")
    game = lines[0].split(" ")[0].lower()
    if game == 'strands':
        puzzle_number = lines[0].split("#")[1].strip()
        
    if game == 'connections':
        puzzle_number = lines[1].split("#")[1].strip()
        
    if game == 'wordle':
        puzzle_number = int(lines[0].split(" ")[1].strip().replace(',',''))

    # elif game != 'Strands' or 'Connections':
    #     puzzle_number = None
    puzzle_lines = lines[2:]

    clean_puzzle_string = "\n".join(puzzle_lines)
    
    return game, puzzle_number, clean_puzzle_string

def score_connections_puzzle(connections_string):
    score = 60
    rows = connections_string.strip().split("\n")
    ticker = 4
    for row in rows:
        if all(emoji == row[0] for emoji in row):
            score += (sum(connections_score_map[emoji] for emoji in row) * ticker)
            ticker -= 1
        else:
            score -= sum(connections_score_map[emoji] for emoji in row)
    return score



strands_score_map = {
    '🟡' : 10,
    '🔵' : 5,
    '💡' : -5
}


def score_strands_puzzle(strands_string):
    # yellow_pos = []
    score = 85
    yellow_pos = len(strands_string)
    for index, emoji in enumerate(strands_string):
        if emoji == '🟡':
            # Yellow always adds +10
            score += strands_score_map[emoji]
            yellow_pos = index
        elif emoji == '🔵':
            # Blue has different scores depending on its position relative to yellow
            # for yellow_position in yellow_positions:
            if index < yellow_pos:
                score += 2  # Blue is to the left of yellow (negative)
                # break
            elif index > yellow_pos:
                score += strands_score_map[emoji]  # Blue is to the right of yellow (positive)
                    # break
        elif emoji == '💡':
            # Light bulbs always subtract 5
            score += strands_score_map[emoji]
    if score < 0:
        score = 0
    return score




wordle_score_map = {
    '⬛' : 5,
    '⬜' : 5,
    '🟨' : 3,
    '🟩' : 0
}


def score_wordle_puzzle(wordle_string):

    score = 0

    rows = wordle_string.strip().split('\n')

    for row in rows:
        for emoji in row:
            score += (wordle_score_map[emoji])            
        
        if all(emoji == '🟩' for emoji in row):
            break
    return score




def init_db():
    conn = sqlite3.connect('rankings.db')
    cursor = conn.cursor()

    # Create the 'puzzles' table if it doesn't already exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS puzzles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_type TEXT NOT NULL,
            puzzle_number INTEGER NOT NULL,
            score INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            release_date DATE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rankings (
            game_type TEXT,
            puzzle_number INTEGER,
            ranking INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (game_type, puzzle_number)
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
    # Prepopulate rankings with default values (e.g., ranking of 0)
    cursor.execute('''
        INSERT OR IGNORE INTO rankings (game_type, puzzle_number, ranking)
        VALUES ('connections', 1, 0), ('strands', 1, 0)
    ''')

    conn.commit()
    conn.close()
    
    
def create_puzzle_dates_table():
    # Connect to the database
    conn = sqlite3.connect('rankings.db')
    cursor = conn.cursor()

    # Create the puzzle_dates table


    conn.commit()
    conn.close()

    
    
def populate_puzzle_dates(game_type, start_puzzle_number, start_date, num_days):
    # Connect to the database
    conn = sqlite3.connect('rankings.db')
    cursor = conn.cursor()

    # Generate puzzle dates for the specified range
    current_date = date.fromisoformat(start_date)
    for i in range(num_days):
        puzzle_number = start_puzzle_number + i
        puzzle_date = current_date + timedelta(days=i)
        try:
            cursor.execute("""
                INSERT INTO puzzle_dates (game_type, puzzle_number, puzzle_date)
                VALUES (?, ?, ?)
            """, (game_type, puzzle_number, puzzle_date.isoformat()))
        except sqlite3.IntegrityError:
            continue

    conn.commit()
    conn.close()
    

def get_current_puzzle(game_type):
    conn = sqlite3.connect('rankings.db')
    cursor = conn.cursor()

    # Retrieve the starting puzzle and date for the game
    cursor.execute("""
        SELECT puzzle_date, puzzle_number
        FROM puzzle_dates
        WHERE game_type = ?
        LIMIT 1
    """, (game_type,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return None

    start_date, start_puzzle_number = result
    start_date = date.fromisoformat(start_date)

    # Calculate the current puzzle number
    days_elapsed = (date.today() - start_date).days
    current_puzzle_number = str(start_puzzle_number + days_elapsed)
    
    return current_puzzle_number


# Insert a score into the database
def insert_score(game_type, puzzle_number, score, session_id):
    conn = sqlite3.connect('rankings.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO puzzles (game_type, puzzle_number, score, session_id)
        VALUES (?, ?, ?, ?)
    ''', (game_type, puzzle_number, score, session_id))
    
    conn.commit()
    conn.close()
    
    
    
def score_exists(session_id, puzzle_number, game_type ):
    conn = sqlite3.connect('rankings.db')
    c = conn.cursor()
    
    # Query to check if a score for this player and puzzle already exists
    c.execute('''
        SELECT COUNT(*) FROM puzzles 
        WHERE session_id = ? AND puzzle_number = ? AND game_type = ?
        ''', (session_id, puzzle_number, game_type))
    count = c.fetchone()[0]
    
    conn.close()
    
    return count > 0



def get_session_scores(session_id, game_type ):
    conn = sqlite3.connect('rankings.db')
    c = conn.cursor()
    
    # Query to check if a score for this player and puzzle already exists
    c.execute('''
        SELECT puzzle_number, score 
        FROM puzzles WHERE session_id = ? AND game_type = ?
        ORDER BY puzzle_number DESC LIMIT 5

    ''', (session_id, game_type))
    scores = c.fetchall()
    
    conn.close()
    
    return scores

def update_ranking(game_type, puzzle_number):
    conn = sqlite3.connect('rankings.db')
    cursor = conn.cursor()
    
    # Calculate the new average score
    cursor.execute('''
        SELECT score
        FROM puzzles 
        WHERE game_type = ? AND puzzle_number = ?
    ''', (game_type, puzzle_number))
    rows = cursor.fetchall()

    scores = []
    for item in rows:
        score = item[0]
        scores.append(score)
        
    m = np.mean(scores)
    var = np.var(scores)
    gamma = 1
    var = var + gamma
    skew = st.skew(scores)
    
    a = 1 if game_type == 'wordle' else 15
    # b = 0.1 * m / var
    b = 0.015
    n = len(scores)
    skew_factor = 1 + (0.01 * skew)
    norm_var = np.sqrt(var) / (m)
    
    
    if game_type == 'wordle':
        alpha = a * m
        beta = b * (norm_var)
        N = 1/n
        
        D = np.round((alpha + beta) / (skew_factor), 5)
        
    else:
        alpha = a * (1/(m + gamma))
        beta = b * norm_var
        N = 1/n        
        
        
        D = np.round((alpha + beta) / (skew_factor), 5)
        
        D = np.clip(D * 1000, 1, 10000)
    
    D = np.round(D, 2)
    print(game_type, alpha, m,beta, skew_factor, D)
    cursor.execute('''
        INSERT INTO rankings (game_type, puzzle_number, ranking)
        VALUES (?, ?, ?)
        ON CONFLICT(game_type, puzzle_number) DO UPDATE SET 
        ranking = excluded.ranking
    ''', (game_type, puzzle_number, D))
    
    
    conn.commit()
    conn.close()
    return

# def update_ranking(game_type, puzzle_number):
#     conn = sqlite3.connect('rankings.db')
#     cursor = conn.cursor()

#     # Calculate the new average score
#     cursor.execute('''
#         SELECT AVG(score) 
#         FROM puzzles 
#         WHERE game_type = ? AND puzzle_number = ?
#     ''', (game_type, puzzle_number))
#     average_score = cursor.fetchone()[0]

#     # Update the rankings table with the new average score
#     cursor.execute('''
#         INSERT INTO rankings (game_type, puzzle_number, ranking)
#         VALUES (?, ?, ?)
#         ON CONFLICT(game_type, puzzle_number) DO UPDATE SET 
#         ranking = excluded.ranking
#     ''', (game_type, puzzle_number, average_score))

#     conn.commit()
#     conn.close()



def get_ranking(game_type, puzzle_number):
    conn = sqlite3.connect('rankings.db')
    cursor = conn.cursor()
    
    cursor.execute(
        '''
        SELECT ranking FROM rankings WHERE game_type = ? AND puzzle_number = ?
        ''', (game_type, puzzle_number)
    )
    
    rank = cursor.fetchall()
    conn.close()
    return rank




def get_current_rank(game_type):
    conn = sqlite3.connect('rankings.db')
    cursor = conn.cursor()

    # Check if a puzzle date exists for the game type
    cursor.execute("""
        SELECT r.ranking, r.puzzle_number, COALESCE(pd.puzzle_date, 'N/A') as date
        FROM rankings r
        JOIN puzzle_dates pd ON r.game_type = pd.game_type AND r.puzzle_number = pd.puzzle_number
        WHERE r.game_type = ?
        ORDER BY r.ranking DESC LIMIT 5
    """, (game_type,))

    row = cursor.fetchall()
    conn.close()
    
    
    
    
    while len(row) < 5:
        row.append((0, 0, '0'))

    return row


def get_recent_scores(puzzle_number = None, db_file = 'rankings.db'):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    query = '''
    WITH recent_puzzles AS (
        SELECT DISTINCT puzzle_number
        FROM puzzles
        ORDER BY timestamp DESC
        
    )
    SELECT p.game_type, p.puzzle_number, p.score
    FROM puzzles p
    INNER JOIN recent_puzzles rp ON p.puzzle_number = rp.puzzle_number
    '''
    if puzzle_number is not None:
        query += ' WHERE p.puzzle_number = ?'
        cursor.execute(query, (puzzle_number,))
    else:
        cursor.execute(query)
        
    rows = cursor.fetchall()

    column_names = [description[0] for description in cursor.description]

    conn.close()
    
    return rows, column_names




def get_score_parameters(game_type):
    rank = get_current_rank(game_type) 
    
    puzzles = []
    for i in range(5):
        if rank[i][1] == 0:
            break
            
        puzzles.append(rank[i][1])

    conn = sqlite3.connect('rankings.db')
    cursor = conn.cursor()
    
    query = f'''
        SELECT puzzle_number, score 
        FROM puzzles WHERE puzzle_number IN ({','.join(['?'] * len(puzzles))})
    '''
    
    cursor.execute(query, tuple(puzzles))
    
    results = cursor.fetchall()
    conn.close()
    score_dict = {}
    for result in results:
        if result[0] not in score_dict:
            score_dict[result[0]] = []
        score_dict[result[0]].append(result[1])
    return score_dict


def calculate_parameters(scores):

    params = {}
    for puzzle, scores in scores.items():
        mu = np.round(np.mean(scores), 2)
        
        std = np.round(np.std(scores), 2)
        
        params[puzzle] = (mu, std)
        
    return params



def organize_data(rows):
    strands = {}
    connecs = {}
    wordle = {}
    for item in rows:

        game = item[0]
        puzzle_number = item[1]
        score = item[2]

        if game == 'strands':
            if puzzle_number not in strands:
                strands[puzzle_number] = []
            strands[puzzle_number].append(score)

        if game == 'connections':
            if puzzle_number not in connecs:
                connecs[puzzle_number] = []
            connecs[puzzle_number].append(score)
            
        if game == 'wordle':
            if puzzle_number not in wordle:
                wordle[puzzle_number] = []
            wordle[puzzle_number].append(score)
    return strands, connecs, wordle



def drop_old_scores(data):
    if data == {}:
        return
    max_key = max(data.keys())
    keys_to_keep = [key for key in data.keys() if key >= max_key - 4]
    data = {key: data[key] for key in keys_to_keep}
    
    return data

def plot_score_data(data,game,session_id):
    
    session_scores = get_session_scores(session_id, game )
    
    
    if data == None:
        return
    data = dict(sorted(data.items()))
    
    data = drop_old_scores(data)
    
    sesh_scores = {}
    
    for key, item in session_scores:
        sesh_scores[key] = item 
        
    sesh_scores = dict(sorted(sesh_scores.items()))

    labels = list(data.keys())[::-1]
    values = [data[key] for key in labels]
    
    label_to_x = {label: idx + 1 for idx, label in enumerate(labels)}
    
    sesh_x_positions = [label_to_x[label] for label in sesh_scores if label in label_to_x]    
    sesh_score = [sesh_scores[key] for key in sesh_scores if key in label_to_x]

    
    
    iqrs, medians, q1s, q2s = [], [], [], []

    for scores in values:

        q1 = np.percentile(scores, 75)
        q2 = np.percentile(scores, 25)
        iqr = q1 - q2

        q1s.append(q1)
        q2s.append(q2)
        iqrs.append(iqr)
    x_positions = np.arange(len(labels))
    
    
    
    
    plt.figure(figsize=(5, 3)) 

    plt.boxplot(
        values, 
        patch_artist=True,               
        notch=False,                     
        vert=True,                       
        widths=0.5,                      
        boxprops=dict(facecolor="white", color="black"),  
        medianprops=dict(color = 'black',linewidth=2),      
        whiskerprops=dict(linewidth=1.5),   
        capprops=dict(color="black", linewidth=1.5),       
        flierprops=dict(marker="o", color="blue", alpha=0.5)  
    )
    if game == 'strands':
        game_title = 'Strands'
    if game == 'connections':
        game_title = 'Connections'
    if game == 'wordle':
        game_title = 'Wordle'
    # if game == 'wordle':
    #     game_title = 'Wordle'

    flattened_values = sorted(np.concatenate([np.atleast_1d(v if isinstance(v, list) else [v]) for v in values if v]))

    # plt.scatter(sesh_x_positions[::-1] + 1, sesh_score,zorder = 3)
    plt.scatter(sesh_x_positions, sesh_score,zorder = 3)
    plt.ylim([np.min(flattened_values) - 10, np.max(flattened_values) + 10])
    plt.xticks(ticks=np.arange(1, len(labels) + 1), labels=labels, fontsize=12)  
    plt.xlabel('Puzzle Number', fontsize=14)
    plt.ylabel('Scores', fontsize=14)
    plt.title(f'{game_title} Recent Scores', fontsize=16)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.gca().invert_xaxis()

    output_path = f'static/images/{game}_recent_scores.png'
    
    plt.savefig(output_path, bbox_inches = 'tight')
    plt.close()
    return output_path