import httpx
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import game_ranking as gr

PLATFORM = 'reddit'
BASE = 'https://www.reddit.com'
HEADERS = {'User-Agent': 'linux:game_ranking_scraper:1.0 (by /u/simonhansedasi)'}

# (subreddit, game_type, keyword to find daily thread)
from datetime import date

def _today_label():
    return date.today().strftime('%B %-d, %Y')  # e.g. "April 17, 2026"

TARGETS = [
    ('wordle',         'wordle',      'Daily Wordle'),
    ('NYTConnections', 'connections', _today_label),   # callable — evaluated at scrape time
    ('NYTStrands',     'strands',     'Strands Daily Thread'),
]


def find_daily_thread(subreddit, title_keyword):
    url = f'{BASE}/r/{subreddit}/search.json'
    params = {'q': title_keyword, 'sort': 'new', 'restrict_sr': 1, 'limit': 5}
    try:
        resp = httpx.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f'[reddit] Request failed for r/{subreddit}: {e}')
        return None
    posts = resp.json()['data']['children']
    for post in posts:
        if title_keyword.lower() in post['data']['title'].lower():
            return post['data']['id']
    return None


def get_comments(subreddit, thread_id):
    url = f'{BASE}/r/{subreddit}/comments/{thread_id}.json'
    resp = httpx.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # data[1] is the comment listing
    return data[1]['data']['children']


def flatten_comments(children):
    for child in children:
        d = child.get('data', {})
        if child.get('kind') == 't1':
            yield d
            replies = d.get('replies', '')
            if isinstance(replies, dict):
                yield from flatten_comments(replies['data']['children'])


def find_recent_threads(subreddit, title_keyword, n_days=7):
    """Find daily threads for the last n_days."""
    url = f'{BASE}/r/{subreddit}/search.json'
    params = {'q': title_keyword, 'sort': 'new', 'restrict_sr': 1, 'limit': n_days + 3}
    try:
        resp = httpx.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f'[reddit] Request failed for r/{subreddit}: {e}')
        return []
    posts = resp.json()['data']['children']
    return [p['data']['id'] for p in posts if title_keyword.lower() in p['data']['title'].lower()][:n_days]


def scrape(config, n_days=7):
    inserted = 0
    errors = 0

    for subreddit, game_keyword, thread_keyword in TARGETS:
        if callable(thread_keyword):
            # For date-based threads, search by month name to catch recent days
            thread_keyword = date.today().strftime('%B')
        thread_ids = find_recent_threads(subreddit, thread_keyword, n_days=n_days)
        if not thread_ids:
            print(f'[reddit] No threads found in r/{subreddit}')
            continue

        for thread_id in thread_ids:
            comments = get_comments(subreddit, thread_id)
            for comment in flatten_comments(comments):
                body = comment.get('body', '')
                username = comment.get('author', 'deleted')
                if not body or username in ('deleted', '[deleted]'):
                    continue

                try:
                    game, puzzle_number, clean_string = gr.clean_puzzle_input(body)
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
                    username=username,
                    raw_share=body,
                )
                if did_insert:
                    gr.update_ranking(game, puzzle_number, PLATFORM)
                    inserted += 1

            time.sleep(1)  # be polite between thread requests

    print(f'[reddit] inserted={inserted} errors={errors}')
    return inserted
