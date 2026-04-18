from flask import Flask, jsonify, send_from_directory, send_file
from flask_cors import CORS
import secrets
import os

import game_ranking as gr
import bayes

app = Flask(__name__, static_folder='static')
CORS(app, resources={r'/*': {'origins': [
    'https://simonhansedasi.github.io',
    'http://localhost:5005',
    'http://127.0.0.1:5005',
]}})
app.secret_key = secrets.token_hex(16)


@app.route('/')
def index():
    return send_file('index.html')

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('js', filename)

@app.route('/styles.css')
def serve_css():
    return send_file('styles.css')


@app.route('/rankings/<game_type>', methods=['GET'])
def get_rankings(game_type):
    if game_type not in ('wordle', 'connections', 'strands'):
        return jsonify({'error': 'unknown game type'}), 400
    rankings = gr.get_platform_rankings(game_type, limit=20)

    # Hierarchical shrinkage per platform
    shrunk = {}
    for platform in ('reddit', 'bluesky'):
        raw = bayes.get_all_rankings(game_type, platform)
        if raw:
            shrunk[platform] = {
                r['puzzle_number']: r['D_shrunk']
                for r in bayes.hierarchical_shrinkage(raw)
            }

    result = []
    for puzzle_number in sorted(rankings.keys()):
        entry = {'puzzle': puzzle_number, 'date': rankings[puzzle_number].get('date', 'N/A')}
        platform_scores = {}
        for platform, stats in rankings[puzzle_number].items():
            if platform == 'date':
                continue
            entry[platform] = {
                'D': round(stats['ranking'], 1),
                'D_shrunk': round(shrunk.get(platform, {}).get(puzzle_number, stats['ranking']), 1),
                'n': stats['n'],
            }
            platform_scores[platform] = stats

        # Cross-platform comparison for this puzzle
        scores_by_platform = bayes.get_platform_scores(game_type, puzzle_number)
        platforms_present = [p for p in scores_by_platform if len(scores_by_platform[p]) >= 2]
        if 'bluesky' in platforms_present and 'reddit' in platforms_present:
            cmp = bayes.cross_platform_comparison(
                scores_by_platform['bluesky'],
                scores_by_platform['reddit'],
                label_a='bluesky', label_b='reddit'
            )
            if cmp:
                entry['comparison'] = {
                    'diff': cmp['diff_mean'],
                    'ci_95': cmp['diff_ci_95'],
                    'p_bluesky_higher': cmp['p_bluesky_greater'],
                }

        result.append(entry)
    return jsonify(result)


@app.route('/plots/<game_type>', methods=['GET'])
def get_plots(game_type):
    if game_type not in ('wordle', 'connections', 'strands'):
        return jsonify({'error': 'unknown game type'}), 400
    return jsonify({
        'ranking':      f'/static/images/{game_type}_platform_ranking.png',
        'distribution': f'/static/images/{game_type}_platform_distribution.png',
        'gaussian':     f'/static/images/{game_type}_gaussian.png',
        'convergence':  f'/static/images/{game_type}_convergence.png',
    })


@app.route('/static/images/<filename>')
def serve_image(filename):
    return send_from_directory(os.path.join(app.static_folder, 'images'), filename)


@app.route('/debug_db', methods=['GET'])
def debug_db():
    import sqlite3
    conn = sqlite3.connect('rankings.db')
    cursor = conn.cursor()
    result = {}
    for table in ['puzzles', 'rankings', 'puzzle_dates']:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        cursor.execute(f'SELECT * FROM {table} ORDER BY rowid DESC LIMIT 5')
        rows = cursor.fetchall()
        result[table] = {'count': count, 'recent': rows}
    conn.close()
    return jsonify(result)


if __name__ == '__main__':
    gr.init_db()
    gr.populate_puzzle_dates('connections', start_puzzle_number=550,  start_date='2024-12-12', num_days=999)
    gr.populate_puzzle_dates('strands',     start_puzzle_number=284,  start_date='2024-12-12', num_days=999)
    gr.populate_puzzle_dates('wordle',      start_puzzle_number=1292, start_date='2025-01-01', num_days=999)
    app.run(host='0.0.0.0', port=5005)
