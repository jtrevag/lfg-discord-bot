# Database Testing Commands

## 1. Check Bot Status
```bash
# View bot logs to confirm database initialized
docker-compose logs -f commander-pod-bot

# Look for these lines:
# "Database initialized and verified"
# "Checking for incomplete polls..."
```

## 2. Verify Database File Created
```bash
# Check database file exists
ls -la data/

# Should show:
# lfg_bot.db (your database)
# lfg_bot.db-journal (temporary SQLite file, may not always be present)
```

## 3. Test Poll Creation (saves to DB)
In Discord, run:
```
!createpoll
```

Then vote on the poll. After 24 hours (or poll duration), pods will be calculated and saved to database.

## 4. Inspect Database Contents
```bash
# Install sqlite3 if not already installed
# sudo apt-get install sqlite3

# Open database
sqlite3 data/lfg_bot.db

# Once in sqlite prompt, run:
.tables                          # Show all tables
SELECT * FROM league;            # View leagues
SELECT * FROM poll;              # View polls
SELECT * FROM pod;               # View pods (after poll completes)
SELECT * FROM player;            # View players
.quit                            # Exit sqlite
```

## 5. Quick Database Query Script
```bash
# One-liner to check database contents
sqlite3 data/lfg_bot.db "SELECT name FROM sqlite_master WHERE type='table';"

# Check if default league was created
sqlite3 data/lfg_bot.db "SELECT * FROM league;"

# After creating a poll, check it was saved
sqlite3 data/lfg_bot.db "SELECT id, discord_message_id, created_at FROM poll;"

# After poll completes, check pods were saved
sqlite3 data/lfg_bot.db "SELECT id, day_of_week, player1_id, player2_id, player3_id, player4_id FROM pod;"
```

## 6. Test Startup Recovery
```bash
# Create a poll that completes while bot is offline
!createpoll

# Stop bot before poll completes
docker-compose down

# Wait for poll to end (or manually end it in Discord)

# Restart bot
docker-compose up -d

# Check logs - should show:
# "Found X poll(s) that might need processing"
# "Processing completed poll: [message_id]"
# "✅ Successfully processed X incomplete poll(s)"
docker-compose logs -f
```

