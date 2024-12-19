from flask import Flask, request, jsonify, session
from flask_cors import CORS
import uuid
import game_ranking as gr
import secrets  # This is used for generating a secret key

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
    return jsonify({'session_id': session['session_id']})
        
@app.route('/score_game', methods=['POST'])
def score_game():
    data = request.get_json()
    ip_address = request.remote_addr
    game_string = data.get("puzzle_string")
    
    session_id = session['session_id']
    
    
    print(game_string)
    game, puzzle_number, clean_string = gr.clean_puzzle_input(game_string)
    if gr.score_exists(session_id, puzzle_number):
        return jsonify({'message': 'Score for this player and puzzle already submitted'}), 400
    
    
    
    
    if game == 'connections':
        score = gr.score_connections_puzzle(clean_string)
    if game == 'strands':
        score = gr.score_strands_puzzle(clean_string)
        
        
    gr.insert_score(game, puzzle_number, score, session_id)
    gr.update_ranking(game, puzzle_number)
    
    rank = gr.get_ranking(game, puzzle_number)
    
    return jsonify({"score": score, "rank" : rank})




if __name__ == '__main__':
    gr.init_db()

    app.run(debug=True, port = 5005)
