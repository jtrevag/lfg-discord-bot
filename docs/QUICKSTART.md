# Quick Start Guide

Get your Commander Pod Bot running in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- A Discord account with permissions to add bots to a server

## Step-by-Step Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Discord Bot

1. Go to https://discord.com/developers/applications
2. Click "New Application"
3. Name it "Commander Pod Bot" (or whatever you like)
4. Go to "Bot" section → "Add Bot"
5. Enable these intents under "Privileged Gateway Intents":
   - Message Content Intent
   - Server Members Intent
6. Click "Reset Token" and copy the token

### 3. Invite Bot to Server

1. In Developer Portal, go to "OAuth2" → "URL Generator"
2. Select scopes: `bot` and `applications.commands`
3. Select permissions:
   - Send Messages
   - Read Message History
   - Add Reactions
   - Create Polls
4. Copy the URL and open in browser
5. Select your server and authorize

### 4. Get Channel ID

1. In Discord: Settings → Advanced → Enable "Developer Mode"
2. Right-click the channel where you want polls → "Copy Channel ID"

### 5. Configure Bot

Create a `.env` file:
```bash
cp config/.env.example config/.env
```

Edit `config/.env` with your values:
```
DISCORD_BOT_TOKEN=your_token_from_step_2
POLL_CHANNEL_ID=your_channel_id_from_step_4
```

### 6. Run the Bot

```bash
python run.py
```

You should see:
```
Commander Pod Bot has connected to Discord!
Bot is in 1 guild(s)
Poll scheduler started!
```

## Testing

### Test the Optimizer (No Discord Required)

```bash
python test_optimizer.py
```

This runs the pod optimization algorithm with various scenarios.

### Test Poll Creation Manually

In your Discord channel, type:
```
!createpoll
```

The bot will create a poll immediately (requires admin permissions).

### Test Pod Calculation Manually

After creating a poll and getting some votes:
```
!calculatepods
```

The bot will calculate and display optimal pods.

## Scheduling

By default (from `config/config.json`):
- Polls posted: **Sunday at 6:00 PM UTC**
- Poll duration: **24 hours**
- Pods calculated: **Automatically when poll ends (Monday at 6:00 PM UTC)**

To change this, edit `config/config.json`:

```json
{
  "poll_schedule": {
    "day_of_week": "sun",
    "hour": 18,
    "minute": 0,
    "timezone": "America/New_York"
  },
  "poll_duration_hours": 24
}
```

**Note:** Pods are automatically calculated when the poll ends. The duration determines when this happens.

Common timezones:
- `America/New_York` (EST/EDT)
- `America/Los_Angeles` (PST/PDT)
- `America/Chicago` (CST/CDT)
- `Europe/London` (GMT/BST)
- `UTC` (Universal Time)

## Common Issues

**Bot is offline**
- Check your token in `config/.env`
- Make sure `python run.py` is running

**Poll not appearing**
- Check POLL_CHANNEL_ID in `config/.env`
- Verify bot has "Send Messages" and "Create Polls" permissions

**"Missing Permissions" on commands**
- Commands require Discord Administrator permission
- Or update bot to check for specific roles

## Next Steps

- Customize poll days in `config/config.json`
- Adjust schedule times for your group
- Read the full README.md for more details
- Check out `docs/TESTING.md` for testing information

## Need Help?

Check the main README.md for troubleshooting and advanced configuration!
