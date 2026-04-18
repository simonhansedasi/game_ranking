# game_ranking

Leaderboard tracker for daily word puzzle games (Wordle, Connections, Strands) — scores arrive via SMS and are ranked automatically.

## What it does

Players text their puzzle results to a Twilio number. The Flask backend parses the pasted score blocks, stores results in SQLite, and serves a ranked leaderboard with performance charts. Supports multiple games with per-game scoring logic.

## Tech

Python, Flask, SQLite, matplotlib, numpy, Twilio API, HTML/CSS/JS

## Run

```bash
python app.py   # starts on port 5005
```

Set up a Twilio webhook pointing to `/sms` to receive scores via text message.
