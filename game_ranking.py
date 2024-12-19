import sqlite3
import uuid
from datetime import date, timedelta


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
    
    puzzle_lines = lines[2:]

    clean_puzzle_string = "\n".join(puzzle_lines)
    
    return game, puzzle_number, clean_puzzle_string

def score_connections_puzzle(connections_string):
    score = 0
    rows = connections_string.strip().split("\n")
    
    for row in rows:
        if all(emoji == row[0] for emoji in row):
            score += sum(connections_score_map[emoji] for emoji in row)
        else:
            score -= sum(connections_score_map[emoji] for emoji in row)
    return score



strands_score_map = {
    '🟡' : 20,
    '🔵' : 1,
    '💡' : -3
}


def score_strands_puzzle(strands_string):
    # yellow_pos = []
    score = 0
    yellow_pos = len(strands_string)
    for index, emoji in enumerate(strands_string):
        # print(index)
        # print(yellow_pos)
        if emoji == '🟡':
            # Yellow always adds +10
            score += strands_score_map[emoji]
            yellow_pos = index
        elif emoji == '🔵':
            # Blue has different scores depending on its position relative to yellow
            # for yellow_position in yellow_positions:
            if index < yellow_pos:
                score -= strands_score_map[emoji]  # Blue is to the left of yellow (negative)
                # break
            elif index > yellow_pos:
                score += strands_score_map[emoji]  # Blue is to the right of yellow (positive)
                    # break
        elif emoji == '💡':
            # Light bulbs always subtract 5
            score += strands_score_map[emoji]
    
    # print(f"Total score: {score}")
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
            # print(f"Skipping duplicate entry for {game_type} puzzle {puzzle_number} on {puzzle_date}.")

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
    current_puzzle_number = start_puzzle_number + days_elapsed

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
    
    
    
def score_exists(session_id, puzzle_number ):
    conn = sqlite3.connect('rankings.db')
    c = conn.cursor()
    
    # Query to check if a score for this player and puzzle already exists
    c.execute('SELECT COUNT(*) FROM puzzles WHERE session_id = ? AND puzzle_number = ?', (session_id, puzzle_number))
    count = c.fetchone()[0]
    
    conn.close()
    
    return count > 0



def update_ranking(game_type, puzzle_number):
    conn = sqlite3.connect('rankings.db')
    cursor = conn.cursor()

    # Calculate the new average score
    cursor.execute('''
        SELECT AVG(score) 
        FROM puzzles 
        WHERE game_type = ? AND puzzle_number = ?
    ''', (game_type, puzzle_number))
    average_score = cursor.fetchone()[0]

    # Update the rankings table with the new average score
    cursor.execute('''
        INSERT INTO rankings (game_type, puzzle_number, ranking)
        VALUES (?, ?, ?)
        ON CONFLICT(game_type, puzzle_number) DO UPDATE SET 
        ranking = excluded.ranking
    ''', (game_type, puzzle_number, average_score))

    conn.commit()
    conn.close()



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
    cursor.execute("SELECT ranking FROM rankings WHERE game_type = ? ORDER BY timestamp DESC LIMIT 1", (game_type,))
    row = cursor.fetchone()
    conn.close()

    return row[0] if row else 0.0