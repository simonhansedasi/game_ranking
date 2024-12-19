from flask import Flask, request, jsonify, session
from flask_cors import CORS
import uuid
import game_ranking as gr
import secrets  # This is used for generating a secret key
import numpy as np

app = Flask(__name__)
CORS(app, support_credentials = True, resources={r'/*': {'origins': ['http://127.0.0.1:4000', 'https://simonhansedasi.github.io']}})


app.config['PREFERRED_URL_SCHEME'] = 'https'

secret_key = secrets.token_hex(16)

app.secret_key = secret_key  # Set the Flask secret key for sessions
app.permanent_session_lifetime = 60 * 60 * 24 * 30  # 30 days


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = 'http://127.0.0.1:4000'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@app.before_request
def ensure_session_id():
    # Ensure the session has an ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    print(f"Session ID: {session['session_id']}")  # Debugging
    
    
    
    
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
        
@app.route('/score_game', methods=['POST'])
def score_game():
    data = request.get_json()
    # ip_address = request.remote_addr
    game_string = data.get("puzzle_string")
    
    session_id = data.get('session_id')
    
    
    # print(game_string)
    game, puzzle_number, clean_string = gr.clean_puzzle_input(game_string)
    if gr.score_exists(session_id, puzzle_number):
        return jsonify({'message': 'Score for this player and puzzle already submitted'}), 400
    
    
    current_puzzle_number = gr.get_current_puzzle(game)
    if not current_puzzle_number:
        return jsonify({'error': 'Game not found'}), 400
    
    
    if puzzle_number != current_puzzle_number:
        return jsonify({'error': 'puzzle does not match current day'}), 400
    
    if game == 'connections':
        score = gr.score_connections_puzzle(clean_string)
    if game == 'strands':
        score = gr.score_strands_puzzle(clean_string)
        
        
    gr.insert_score(game, puzzle_number, score, session_id)
    gr.update_ranking(game, puzzle_number)
    
    rank = gr.get_ranking(game, puzzle_number)
    
    return jsonify({"score": score, "rank" : rank})

@app.route('/get_ranking', methods=['GET'])
def get_ranking():
    game_type = request.args.get('game_type')
    
    if not game_type:
        return jsonify({'error': 'Game type is required'}), 400

    # Query the database to get the current ranking for the game type
    rank = np.round(gr.get_current_rank(game_type),2)  # Implement this function to fetch the ranking

    if rank is None:
        return jsonify({'error': 'No ranking data available'}), 404

    return jsonify({'rank': rank})


if __name__ == '__main__':
    gr.init_db()
    # Populate puzzles for two games (customize as needed)
    gr.populate_puzzle_dates(game_type="connections", start_puzzle_number=557, start_date="2024-12-19", num_days=999)
    gr.populate_puzzle_dates(game_type="strands", start_puzzle_number=291, start_date="2024-12-19", num_days=999)
    app.run(debug=True, port = 5005)
