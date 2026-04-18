import httpx
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import game_ranking as gr

PLATFORM = 'bluesky'
BSKY_API = 'https://bsky.social/xrpc'
SEARCH_URL = f'{BSKY_API}/app.bsky.feed.searchPosts'

QUERIES = [
    ('wordle',      'Wordle'),
    ('connections', 'Connections Puzzle #'),
    ('strands',     'Strands #'),
]


def create_session(handle, password):
    resp = httpx.post(f'{BSKY_API}/com.atproto.server.createSession',
                      json={'identifier': handle, 'password': password}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data['accessJwt']


def search_posts(token, query, limit=100, max_pages=10):
    headers = {'Authorization': f'Bearer {token}'}
    all_posts = []
    cursor = None
    for _ in range(max_pages):
        params = {'q': query, 'limit': limit}
        if cursor:
            params['cursor'] = cursor
        resp = httpx.get(SEARCH_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        posts = data.get('posts', [])
        all_posts.extend(posts)
        cursor = data.get('cursor')
        if not cursor or not posts:
            break
    return all_posts


def scrape(config):
    handle = config.get('bot_bluesky_handle')
    password = config.get('bot_bluesky_password')
    if not handle or not password:
        print('[bluesky] No credentials in config, skipping.')
        return 0

    try:
        token = create_session(handle, password)
    except Exception as e:
        print(f'[bluesky] Auth failed: {e}')
        return 0

    inserted = 0
    errors = 0

    for game_keyword, query in QUERIES:
        try:
            posts = search_posts(token, query)
        except Exception as e:
            print(f'[bluesky] Search failed for "{query}": {e}')
            continue

        for post in posts:
            text = post.get('record', {}).get('text', '')
            handle = post.get('author', {}).get('handle', 'unknown')

            try:
                game, puzzle_number, clean_string = gr.clean_puzzle_input(text)
            except ValueError:
                continue

            try:
                if game == 'connections':
                    score = gr.score_connections_puzzle(clean_string)
                elif game == 'strands':
                    score = gr.score_strands_puzzle(clean_string)
                elif game == 'wordle':
                    score = gr.score_wordle_puzzle(clean_string)
                else:
                    continue
            except Exception:
                errors += 1
                continue

            did_insert = gr.insert_score(
                game_type=game,
                puzzle_number=puzzle_number,
                score=score,
                platform=PLATFORM,
                username=handle,
                raw_share=text,
            )
            if did_insert:
                gr.update_ranking(game, puzzle_number, PLATFORM)
                inserted += 1

    print(f'[bluesky] inserted={inserted} errors={errors}')
    return inserted
