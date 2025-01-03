from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
import uuid
import game_ranking as gr
import secrets  # This is used for generating a secret key
import numpy as np
import os
from datetime import datetime, timezone
# import logging
# logging.basicConfig(level=logging.DEBUG)
# Function to get current UTC date and time
utc_now = lambda: datetime.now(timezone.utc)
app = Flask(__name__, static_folder='static')
# app.debug = True  # This turns on debug mode.
# app.config['PROPAGATE_EXCEPTIONS'] = True

# CORS(app, support_credentials = True, resources={r'/*': {'origins': 'https://simonhansedasi.github.io'}})

CORS(app, support_credentials = True, resources={r'/*': {'origins': ['https://02a885916215.ngrok.app','https://127.0.0.1:4000','https://simonhansedasi.github.io']}})
# CORS(app, support_credentials=True, resources={r'/*': {'origins': ['http://127.0.0.1:4000']}})

# app.config['PREFERRED_URL_SCHEME'] = 'https'

secret_key = secrets.token_hex(16)

app.secret_key = secret_key  # Set the Flask secret key for sessions
app.permanent_session_lifetime = 60 * 60 * 24 * 30  # 30 days


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = 'https://simonhansedasi.github.io'
    # response.headers['Access-Control-Allow-Origin'] = 'http://127.0.0.1:4000'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@app.before_request
def ensure_session_id():
    # Ensure the session has an ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    

    
    
@app.route('/')
def index():
    return render_template('index.html')
    
    
    
    
@app.route('/get_session_id', methods=['GET'])
def get_session_id():
    existing_session_id = request.cookies.get('session_id')

    if existing_session_id:
        return jsonify({'session_id': existing_session_id})

    # Generate a new session ID if one doesn't exist
    new_session_id = gr.generate_unique_session_id()
    response = jsonify({'session_id': new_session_id})
    response.set_cookie('session_id', new_session_id, max_age=30*24*60*60, secure=True)
    return response


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)





@app.route('/sms', methods=['POST'])
def sms_reply():
    incoming_message = request.form['Body']

    from_number = request.form['From']
    game, puzzle_number, clean_string = gr.clean_puzzle_input(incoming_message) 
    if gr.score_exists(from_number, puzzle_number, game):
        response_message = f"Puzzle already scored."
        return f"<Response><Message>{response_message}</Message></Response>"
    else:
        if game == 'connections':
            score = gr.score_connections_puzzle(clean_string)
        if game == 'strands':
            score = gr.score_strands_puzzle(clean_string)  
        response_message = f"Your score: {score}. Visit simonhansedasi.github.io/game_ranking to view more scores"
        gr.insert_score(game, puzzle_number, score, session_id = from_number)
        gr.update_ranking(game, puzzle_number)
        # Twilio expects XML response
        return f"<Response><Message>{response_message}</Message></Response>"



@app.route('/static/images/<game_type>_recent_scores.png')
def serve_image(game_type):
    # This assumes images are saved in the 'static/images' folder
    return app.send_static_file(f'images/{game_type}_recent_scores.png')



@app.route('/score_game', methods=['POST'])
def score_game():
    data = request.get_json()
    game_string = data.get("puzzle_string")
    session_id = data.get('session_id')
    game, puzzle_number, clean_string = gr.clean_puzzle_input(game_string)
    if gr.score_exists(session_id, puzzle_number, game):
        print('no can do siree')
        return jsonify({'score': 'Score for this player and puzzle already submitted'}), 400
    
    
#     current_puzzle_number = gr.get_current_puzzle(game)
#     if not current_puzzle_number:
#         return jsonify({'score': 'Game not found'}), 400
    
    
#     if puzzle_number != current_puzzle_number:
#         return jsonify({'score': 'puzzle does not match current day'}), 400
    # else:
    if game == 'connections':
        score = gr.score_connections_puzzle(clean_string)

    if game == 'wordle':
        score = gr.score_wordle_puzzle(clean_string)
    if game == 'strands':
        score = gr.score_strands_puzzle(clean_string)
    utc_timestamp = datetime.utcnow()  # Current UTC time

    gr.insert_score(game, puzzle_number, score, session_id)
    gr.update_ranking(game, puzzle_number)

    rows, col_names = gr.get_recent_scores()
    strands, connecs, wordle = gr.organize_data(rows)
    if game == 'connections':
        connecs = gr.drop_old_scores(connecs)
        path = gr.plot_score_data(connecs, game = 'connections', session_id = session_id)

    if game == 'strands':
        path = gr.plot_score_data(strands, game = 'strands', session_id = session_id)

    if game == 'wordle':
        path = gr.plot_score_data(wordle, game = 'wordle', session_id = session_id)

    # else:
    #     return jsonify({'score': 'Invalid game type'}), 400

    rank = gr.get_ranking(game, puzzle_number)
    return jsonify({"score": score, "rank" : rank, "path" : f'/{path}'})

@app.route('/get_ranking', methods=['GET'])
def get_ranking():
    game_type = request.args.get('game_type')
    session_id = request.args.get('session_id')
    if not game_type:
        return jsonify({'error': 'Game type is required'}), 400

    # Query the database to get the current ranking for the game type
    
    
    
    rank = gr.get_current_rank(game_type)  # Implement this function to fetch the ranking
    # while len(rank) < 5:
    #     rank.append((3, 0, 7))
    # print(rank)
    
    if rank is None:
        return jsonify({'error': 'No ranking data available'}), 404
    # Convert NumPy int64 to Python int
    if isinstance(rank, (np.integer, np.floating)):
        rank = rank.item()
    rows, col_names = gr.get_recent_scores()
    strands, connecs, wordle = gr.organize_data(rows)
    if game_type == 'connections':
        connecs = gr.drop_old_scores(connecs)
        path = gr.plot_score_data(connecs, game = 'connections',session_id = session_id)

    if game_type == 'strands':
        strands = gr.drop_old_scores(strands)

        path = gr.plot_score_data(strands, game = 'strands',session_id = session_id)
        
    if game_type == 'wordle':
        wordle = gr.drop_old_scores(wordle)

        path = gr.plot_score_data(wordle, game = 'wordle',session_id = session_id)
        
    params = gr.calculate_parameters(
        gr.get_score_parameters(game_type)
    )
    response = {}
    for i, entry in enumerate(rank):
        index = i + 1
        puzzle_number = entry[1]

        # Fetch mean and variance from the dictionary; default to (0, 0) if not found
        mu, var = params.get(puzzle_number, (0, 0))

        response[f'date{index}'] = str(entry[2])
        response[f'puzz{index}'] = str(puzzle_number)
        response[f'rank{index}'] = str(entry[0])
        response[f'mu{index}'] = str(mu)
        response[f'var{index}'] = str(var)

    return jsonify(response)


if __name__ == '__main__':
    gr.init_db()
    # Populate puzzles for two games (customize as needed)
    gr.populate_puzzle_dates(game_type="connections", start_puzzle_number=550, start_date="2024-12-12", num_days=999)
    gr.populate_puzzle_dates(game_type="strands", start_puzzle_number=284, start_date="2024-12-12", num_days=999)
    gr.populate_puzzle_dates(game_type="wordle", start_puzzle_number=1292, start_date="2025-01-01", num_days=999)
    app.run(debug=True, port = 5005)
