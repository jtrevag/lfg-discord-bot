# Commander Pod Discord Bot

A Discord bot that automates weekly polls for 4-player Commander games and optimizes pod creation to maximize player participation.

## Features

- **Automated Weekly Polls**: Automatically posts polls at configured times
- **Discord Native Polls**: Uses Discord's built-in poll functionality with configurable duration
- **Smart Pod Optimization**: Maximizes number of players who get to play at least once
- **Multi-day Support**: Players can vote for multiple days
- **Conflict Resolution**: Detects when a player's choice is needed for optimal pod formation
- **Automatic Pod Calculation**: Automatically calculates and posts optimal pods when poll ends

## Quick Start

**Two deployment options available:**

- **Docker (Recommended for servers)**: See [docs/DOCKER.md](docs/DOCKER.md) for containerized deployment
- **Local Python**: See [docs/QUICKSTART.md](docs/QUICKSTART.md) for traditional setup

## Setup

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section and click "Add Bot"
4. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Server Members Intent
5. Copy the bot token (you'll need this for the `.env` file)

### 2. Invite Bot to Your Server

1. Go to the "OAuth2" -> "URL Generator" section
2. Select scopes:
   - `bot`
   - `applications.commands`
3. Select bot permissions:
   - Send Messages
   - Read Message History
   - Add Reactions
   - Create Polls
4. Copy the generated URL and open it in your browser to invite the bot

### 3. Get Channel ID

1. Enable Developer Mode in Discord (User Settings -> Advanced -> Developer Mode)
2. Right-click the channel where you want polls posted
3. Click "Copy Channel ID"

### 4. Install Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Configure the Bot

1. Copy the example environment file:
   ```bash
   cp config/.env.example config/.env
   ```

2. Edit `config/.env` and add your credentials:
   ```
   DISCORD_BOT_TOKEN=your_bot_token_here
   POLL_CHANNEL_ID=your_channel_id_here
   ```

3. (Optional) Edit `config/config.json` to customize:
   - Poll days (default: Monday, Tuesday, Wednesday)
   - Poll schedule (when polls are posted)
   - Poll duration in hours (how long polls stay open)
   - Timezone settings
   - Poll question text

## Project Structure

```
lfg-discord-bot/
├── src/lfg_bot/          # Main bot package
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── bot.py            # Bot setup and core functions
│   ├── cogs/             # Discord command modules
│   │   ├── __init__.py
│   │   └── polls.py      # Poll commands
│   └── utils/            # Helper modules
│       ├── __init__.py
│       ├── pod_optimizer.py
│       └── scheduler.py
├── tests/                # Test files
├── config/               # Configuration files
│   ├── config.json
│   └── .env.example
├── docs/                 # Documentation
├── run.py                # Simple entry point
└── README.md
```

## Configuration

The `config/config.json` file contains scheduling and poll settings:

```json
{
  "poll_days": ["Monday", "Tuesday", "Wednesday"],
  "poll_schedule": {
    "day_of_week": "sun",
    "hour": 18,
    "minute": 0,
    "timezone": "UTC"
  },
  "poll_question": "Which days are you available for Commander this week?",
  "poll_duration_hours": 24
}
```

**Settings:**
- `poll_days`: Days to include as options in the poll
- `poll_schedule`: When to automatically post polls (day, hour, minute, timezone)
- `poll_question`: The question displayed in the poll
- `poll_duration_hours`: How long the poll stays open (pods calculated automatically when it closes)

### Schedule Format

- **day_of_week**: `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun`
- **hour**: 0-23 (24-hour format)
- **minute**: 0-59
- **timezone**: Any valid timezone (e.g., `America/New_York`, `Europe/London`, `US/Pacific`)

### Example Configuration

**Poll posted Sunday at 6 PM, runs for 24 hours:**
```json
{
  "poll_schedule": {"day_of_week": "sun", "hour": 18, "minute": 0, "timezone": "America/New_York"},
  "poll_duration_hours": 24
}
```
Pods will be automatically calculated Monday at 6 PM (24 hours later).

**Poll posted Friday evening, runs for a week:**
```json
{
  "poll_schedule": {"day_of_week": "fri", "hour": 20, "minute": 0, "timezone": "US/Pacific"},
  "poll_duration_hours": 168
}
```
Pods will be automatically calculated the following Friday at 8 PM.

## Running the Bot

### Docker (Recommended)

```bash
docker-compose up -d
```

See [docs/DOCKER.md](docs/DOCKER.md) for full Docker deployment guide.

### Local Python

```bash
# Make sure virtual environment is activated
python run.py
```

Or use the module directly:
```bash
python -m lfg_bot.main
```

The bot will:
1. Connect to Discord
2. Start the scheduler
3. Automatically create polls at the configured time
4. Automatically calculate and announce pods when each poll ends

## Manual Commands

### Status Check

- `!ping` - Check if the bot is online and responsive (shows latency)

### Admin Commands

The following commands require Discord Administrator permissions:

- `!createpoll` - Manually create a poll
- `!calculatepods` - Manually calculate pods from the current poll

## How It Works

### Poll Creation

1. Bot posts a poll with configured days (Mon/Tue/Wed by default)
2. Players vote for all days they're available (multi-select)
3. Poll stays open for the configured duration (24 hours by default)

### Pod Optimization

When the poll ends, the bot automatically:

1. Collects all votes from the poll
2. Runs an optimization algorithm to:
   - Maximize the number of players who play at least once
   - Form 4-player pods for each day
   - Detect scenarios where a player must choose between days
3. Posts the results with:
   - Pod assignments (day + 4 players)
   - Players who got games
   - Players without games (if any)
   - Choice scenarios (if a player is critical for multiple pods)

### Example Output

```
**Pod Assignments for This Week**

**Monday:**
  Pod 1: @Alice, @Bob, @Charlie, @Dave

**Wednesday:**
  Pod 1: @Eve, @Frank, @Grace, @Henry

**Total players with games:** 8
```

### Choice Scenario Example

```
**PLAYER CHOICE REQUIRED**
@Alice is needed for pods on both Monday and Wednesday.
Please choose which day you prefer to play, or if you can attend both!

**Potential Pods:**
**Monday:** @Alice, @Bob, @Charlie, @Dave
**Wednesday:** @Alice, @Eve, @Frank, @Grace

Please react or respond with your choice!
```

## Troubleshooting

### Bot doesn't respond
- Check that the bot has proper permissions in the channel
- Verify intents are enabled in Discord Developer Portal
- Check bot token is correct in `config/.env`

### Polls not creating automatically
- Check scheduler configuration in `config/config.json`
- Verify timezone is correct
- Check bot logs for errors

### "Poll message not found" error
- Ensure the bot has "Read Message History" permission
- Check that the poll channel ID is correct in `config/.env`

## Future Enhancements

Potential features for future versions:
- Customizable poll days without code changes
- Player priority/rotation system
- Statistics tracking (games played per player)
- Support for different game formats (not just 4-player pods)
- Web dashboard for configuration

## License

MIT License - feel free to use and modify as needed!
