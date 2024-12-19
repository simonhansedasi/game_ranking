import sqlite3





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
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rankings (
            game_type TEXT,
            puzzle_number INTEGER,
            ranking INTEGER,
            PRIMARY KEY (game_type, puzzle_number)
        )
    ''')

    conn.commit()
    conn.close()

# Retrieve the leaderboard scores from the database
def get_scores():
    conn = sqlite3.connect('rankings.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM puzzles ORDER BY score DESC
    ''')

    scores = cursor.fetchall()
    conn.close()
    # print(scores)
    return scores   

def update_scores(scores):
    
    game = {}
    score = 0
    
    # for player in scores
    
    
    
    
    
    
    
    return
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



