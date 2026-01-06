# Docker Deployment Guide

Deploy the Commander Pod Bot using Docker for easy installation and management on your home server.

## Prerequisites

- Docker installed on your server ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed ([Install Docker Compose](https://docs.docker.com/compose/install/))
- Discord bot token and channel ID (see [QUICKSTART.md](QUICKSTART.md) for setup)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/jtrevag/lfg-discord-bot.git
cd lfg-discord-bot
```

### 2. Configure Environment

Create your `.env` file:

```bash
cp config/.env.example config/.env
```

Edit `config/.env` with your credentials:

```bash
nano config/.env
```

```
DISCORD_BOT_TOKEN=your_bot_token_here
POLL_CHANNEL_ID=your_channel_id_here
```

### 3. Build and Run

**Using Docker Compose (Recommended):**

```bash
docker-compose up -d
```

**Or using Docker directly:**

```bash
# Build the image
docker build -t commander-pod-bot .

# Run the container
docker run -d \
  --name commander-pod-bot \
  --restart unless-stopped \
  -v $(pwd)/config:/app/config:ro \
  commander-pod-bot
```

### 4. Verify It's Running

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f
```

You should see:
```
Commander Pod Bot has connected to Discord!
Bot is in 1 guild(s)
Scheduler started with poll creation on sun at 18:00 UTC
```

## Management Commands

### Start the Bot

```bash
docker-compose up -d
```

### Stop the Bot

```bash
docker-compose down
```

### Restart the Bot

```bash
docker-compose restart
```

### View Logs

```bash
# Follow logs in real-time
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100
```

### Update the Bot

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

## Configuration

### Customize Poll Schedule

Edit `config/config.json`:

```json
{
  "poll_days": ["Monday", "Tuesday", "Wednesday"],
  "poll_schedule": {
    "day_of_week": "sun",
    "hour": 18,
    "minute": 0,
    "timezone": "America/New_York"
  },
  "poll_question": "Which days are you available for Commander this week?",
  "poll_duration_hours": 24
}
```

After editing, restart the container:

```bash
docker-compose restart
```

### Resource Limits

The default `docker-compose.yml` sets resource limits:
- CPU: 0.5 cores max (0.1 reserved)
- Memory: 256MB max (128MB reserved)

To adjust these, edit `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
```

## Deployment Options

### Option 1: Docker Compose (Recommended)

Best for home servers with Docker Compose installed.

```bash
docker-compose up -d
```

### Option 2: Docker Run

Manual container management:

```bash
docker run -d \
  --name commander-pod-bot \
  --restart unless-stopped \
  -v $(pwd)/config:/app/config:ro \
  commander-pod-bot
```

### Option 3: Docker Swarm / Kubernetes

For advanced deployments, the Docker image can be used with orchestration platforms.

## Troubleshooting

### Bot not connecting to Discord

```bash
# Check logs for errors
docker-compose logs

# Common issues:
# - Invalid bot token in config/.env
# - Missing Message Content Intent in Discord Developer Portal
```

### Container keeps restarting

```bash
# Check logs for Python errors
docker-compose logs --tail=50

# Verify .env file exists and is readable
ls -la config/.env
```

### Configuration changes not taking effect

```bash
# Restart the container
docker-compose restart

# Or rebuild if Dockerfile changed
docker-compose up -d --build
```

### Permission issues

```bash
# Ensure config directory is readable
chmod 755 config
chmod 644 config/.env config/config.json
```

## Security Best Practices

1. **Never commit `.env` files**: The `.env` file contains sensitive tokens
2. **Use read-only volume mounts**: Config is mounted as `:ro` (read-only)
3. **Run as non-root user**: Container runs as `botuser` (UID 1000)
4. **Keep image updated**: Regularly pull latest code and rebuild

## Backup and Migration

### Backup Configuration

```bash
# Backup your config directory
tar -czf commander-bot-config-backup.tar.gz config/
```

### Migrate to New Server

```bash
# On new server:
git clone https://github.com/jtrevag/lfg-discord-bot.git
cd lfg-discord-bot

# Copy your backup
scp user@old-server:commander-bot-config-backup.tar.gz .
tar -xzf commander-bot-config-backup.tar.gz

# Start the bot
docker-compose up -d
```

## System Requirements

- **CPU**: 0.1-0.5 cores (very lightweight)
- **Memory**: 128-256MB
- **Disk**: ~100MB (image + logs)
- **Network**: Outbound HTTPS to Discord API

## Auto-Start on Boot

Docker Compose with `restart: unless-stopped` automatically starts on server boot.

To ensure Docker starts on boot:

```bash
# Enable Docker service
sudo systemctl enable docker
```

## Monitoring

### Health Check

```bash
# Check if container is running
docker ps | grep commander-pod-bot

# Check resource usage
docker stats commander-pod-bot
```

### Log Rotation

Logs are automatically rotated (max 10MB per file, 3 files kept).

To view disk usage:

```bash
docker system df
```

## Uninstall

```bash
# Stop and remove container
docker-compose down

# Remove image
docker rmi commander-pod-bot

# Remove config (WARNING: deletes your settings)
rm -rf config/
```

## Getting Help

- Check [QUICKSTART.md](QUICKSTART.md) for bot setup
- Check [README.md](../README.md) for feature documentation
- Check [TESTING.md](TESTING.md) for development info
