from flask import Flask, request, jsonify
from flask_cors import CORS

import game_ranking as gr
app = Flask(__name__)
CORS(app, support_credentials = True, resources={r'/*': {'origins': '*'}})

 

@app.route('/score_game', methods=['POST'])
def score_game():
    data = request.get_json()
    ip_address = request.remote_addr
    game_string = data.get("puzzle_string")
    
    
    
    
    print(game_string)
    game, puzzle_number, clean_string = gr.clean_puzzle_input(game_string)
    if gr.score_exists(ip_address, puzzle_number):
        return jsonify({'message': 'Score for this player and puzzle already submitted'}), 400
    
    
    
    
    if game == 'connections':
        score = gr.score_connections_puzzle(clean_string)
    if game == 'strands':
        score = gr.score_strands_puzzle(clean_string)
        
        
    gr.insert_score(game, puzzle_number, score, ip_address)
    gr.update_ranking(game, puzzle_number)
    
    rank = gr.get_ranking(game, puzzle_number)
    
    return jsonify({"score": score, "rank" : rank})




if __name__ == '__main__':
    gr.init_db()

    app.run(debug=True, port = 5005)
