#!/usr/bin/env python3
"""
Cron entry point. Runs all scrapers and logs results.
Crontab on Pi: 0 */2 * * * cd ~/coding/game_ranking && /path/to/venv/bin/python scrape.py
"""
import os
import sys
import configparser
from datetime import datetime

import game_ranking as gr
from scrapers import reddit, bluesky


def load_config(path='config.txt'):
    config = configparser.ConfigParser()
    config.read(path)
    # credentials section is optional — Reddit scraper uses public JSON API
    return dict(config['credentials']) if 'credentials' in config else {}


def main():
    config = load_config()

    gr.init_db()
    gr.populate_puzzle_dates('connections', start_puzzle_number=550,  start_date='2024-12-12', num_days=999)
    gr.populate_puzzle_dates('strands',     start_puzzle_number=284,  start_date='2024-12-12', num_days=999)
    gr.populate_puzzle_dates('wordle',      start_puzzle_number=1292, start_date='2025-01-01', num_days=999)

    start = datetime.utcnow()
    print(f'[scrape] run started {start.isoformat()}')

    total = 0
    total += reddit.scrape(config)
    total += bluesky.scrape(config)

    elapsed = (datetime.utcnow() - start).total_seconds()
    print(f'[scrape] done — {total} new scores in {elapsed:.1f}s')


if __name__ == '__main__':
    main()
