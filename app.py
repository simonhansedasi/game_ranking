from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
import uuid
import game_ranking as gr
import secrets  # This is used for generating a secret key
import numpy as np
import os
from datetime import datetime, timezone

# Function to get current UTC date and time
utc_now = lambda: datetime.now(timezone.utc)
app = Flask(__name__, static_folder='static')
CORS(app, support_credentials = True, resources={r'/*': {'origins': 'https://simonhansedasi.github.io'}})

# CORS(app, support_credentials = True, resources={r'/*': {'origins': ['https://02a885916215.ngrok.app','https://127.0.0.1:4000','https://simonhansedasi.github.io']}})
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
    # print(f"Session ID: {session['session_id']}")  # Debugging
    
    

    
    
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





@app.route('/static/images/<game_type>_recent_scores.png')
def serve_image(game_type):
    # This assumes images are saved in the 'static/images' folder
    return app.send_static_file(f'images/{game_type}_recent_scores.png')



@app.route('/score_game', methods=['POST'])
def score_game():
    data = request.get_json()
    # ip_address = request.remote_addr
    game_string = data.get("puzzle_string")
    print(data)
    session_id = data.get('session_id')
    print(game_string)
    print('whaaaa')
    # print(game_string)
    game, puzzle_number, clean_string = gr.clean_puzzle_input(game_string)
    print(game)
    print('data cleaned')
    print(game)
    if gr.score_exists(session_id, puzzle_number, game):
        print('no can do siree')
        return jsonify({'score': 'Score for this player and puzzle already submitted'}), 400
    
    
#     current_puzzle_number = gr.get_current_puzzle(game)
#     if not current_puzzle_number:
#         print('wrong day?')
#         return jsonify({'score': 'Game not found'}), 400
    
    
#     if puzzle_number != current_puzzle_number:
#         print(current_puzzle_number)
#         print('wrong day')
#         return jsonify({'score': 'puzzle does not match current day'}), 400
    else:
        if game == 'connections':
            score = gr.score_connections_puzzle(clean_string)
        if game == 'strands':
            score = gr.score_strands_puzzle(clean_string)

        utc_timestamp = datetime.utcnow()  # Current UTC time

        gr.insert_score(game, puzzle_number, score, session_id)
        gr.update_ranking(game, puzzle_number)

        rows, col_names = gr.get_recent_scores()
        strands, connecs = gr.organize_data(rows)

        # print(game)
        if game == 'connections':
            connecs = gr.drop_old_scores(connecs)
            path = gr.plot_score_data(connecs, game = 'connections', session_id = session_id)

        if game == 'strands':
            path = gr.plot_score_data(strands, game = 'strands', session_id = session_id)

        # else:
        #     print('Invalid game type')
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
    
    row = gr.get_current_rank(game_type)
    # print(row)
    
    
    rank = np.round(gr.get_current_rank(game_type),2)  # Implement this function to fetch the ranking
    # print(rank, 'hhhhooo')
    if rank is None:
        return jsonify({'error': 'No ranking data available'}), 404
    # Convert NumPy int64 to Python int
    if isinstance(rank, (np.integer, np.floating)):
        rank = rank.item()
    print(session_id)
    rows, col_names = gr.get_recent_scores()
    strands, connecs = gr.organize_data(rows)
    if game_type == 'connections':
        connecs = gr.drop_old_scores(connecs)
        path = gr.plot_score_data(connecs, game = 'connections',session_id = session_id)

    if game_type == 'strands':
        strands = gr.drop_old_scores(strands)

        path = gr.plot_score_data(strands, game = 'strands',session_id = session_id)
        
    print(path)
    # print(rank)
    return jsonify(
        {
            'puzz1': str(np.round(rank[0][1],3)),
            'rank1': str(rank[0][0]),
            'puzz2': str(rank[1][1]),
            'rank2': str(rank[1][0]),
            'puzz3': str(rank[2][1]),
            'rank3': str(rank[2][0]),
            'puzz4': str(rank[3][1]),
            'rank4': str(rank[3][0]),
            
            'puzz5': str(rank[4][1]),
            'rank5': str(rank[4][0]),
            # "path" : f"/{path}"
        }
    )


if __name__ == '__main__':
    gr.init_db()
    # Populate puzzles for two games (customize as needed)
    gr.populate_puzzle_dates(game_type="connections", start_puzzle_number=550, start_date="2024-12-12", num_days=999)
    gr.populate_puzzle_dates(game_type="strands", start_puzzle_number=284, start_date="2024-12-12", num_days=999)
    app.run(debug=True, port = 5005)
