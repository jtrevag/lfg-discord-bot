# Claude Code Development Log

This document tracks the development of the Commander Pod Discord Bot, built with assistance from Claude Code.

## Project Overview

**Name**: Commander Pod Discord Bot
**Purpose**: Automate weekly polls for 4-player Magic: The Gathering Commander games and optimize pod creation to maximize player participation
**Language**: Python 3.11+
**Framework**: discord.py
**Repository**: https://github.com/jtrevag/lfg-discord-bot

## Core Features Implemented

### 1. Automated Poll System
- Uses Discord's native poll functionality
- Automatically posts polls on configurable schedule (default: Sunday 6 PM)
- Multi-day voting support (players can select multiple days)
- Configurable poll duration (default: 24 hours)
- Automatic pod calculation when poll ends

### 2. Smart Pod Optimization Algorithm

Implements a greedy optimization algorithm with two key enhancements:

#### Algorithm 5a: Unique Player Priority
- Prioritizes days with players who are only available on that specific day
- Ensures inflexible players get matched before flexible ones
- Sorts days by: (unique player count, total player count)
- Maximizes total number of players who get to play at least once

#### Algorithm 5b: Critical Flexible Player Detection
- Detects when a flexible player is critical for forming a specific pod
- Pre-assigns critical players to their required day
- Notifies users when manual choice is needed
- Prevents suboptimal pod formations

#### Algorithm Enhancement: Complete Pod Priority & Double-Play
- Prioritizes days with exact multiples of 4 players (complete pods)
- Detects when 3 players are waiting and flexible players could volunteer
- Instead of auto-assigning, prompts eligible players with interactive buttons
- First volunteer to click creates the pod automatically in database
- Maximizes total games played while respecting player autonomy

**Test Coverage**: 15 tests covering all scenarios, all passing

### 3. Discord Bot Features
- **Commands**:
  - `!ping` - Check bot status and latency (public)
  - `!createpoll` - Manually create a poll (admin)
  - `!calculatepods` - Manually calculate pods (admin)
- **Automatic Scheduling**: APScheduler with timezone support
- **Discord Cogs**: Modular command organization
- **Message Content Intent**: Enabled for poll processing
- **Server Members Intent**: Enabled for user mentions

### 4. Poll Processing & Results
- Extracts votes from Discord poll objects
- Builds player availability matrix
- Runs optimization algorithm
- Formats results with Discord mentions
- Posts pod assignments automatically
- Handles edge cases:
  - Not enough players (< 4)
  - Player choice required
  - Players without games
  - Multiple pods per day

### 5. Docker Deployment
- **Base Image**: python:3.11-slim
- **Container Size**: ~150MB
- **Security**: Non-root user (botuser, UID 1000)
- **Resource Limits**: 0.5 CPU, 256MB memory
- **Auto-restart**: unless-stopped policy
- **Log Rotation**: 10MB max, 3 files
- **Docker Compose**: Simple orchestration included

### 6. Project Structure

```
lfg-discord-bot/
├── src/lfg_bot/              # Main package
│   ├── main.py               # Entry point
│   ├── bot.py                # Bot setup, events, core functions
│   ├── cogs/                 # Command modules
│   │   └── polls.py          # Poll commands (!ping, !createpoll, !calculatepods)
│   └── utils/                # Helper modules
│       ├── pod_optimizer.py  # 5a & 5b algorithms
│       └── scheduler.py      # APScheduler integration
├── tests/                    # All test files (37 tests, all passing)
│   ├── test_pod_optimizer.py
│   ├── test_scheduler.py
│   ├── test_complex_scenarios.py
│   └── test_optimizer.py
├── config/                   # Configuration
│   ├── config.json           # Poll schedule, days, duration
│   └── .env.example          # Token and channel ID template
├── docs/                     # Documentation
│   ├── QUICKSTART.md         # 5-minute setup guide
│   ├── DOCKER.md             # Docker deployment guide
│   └── TESTING.md            # Test documentation
├── scripts/                  # Helper scripts
├── Dockerfile                # Container definition
├── docker-compose.yml        # Container orchestration
└── run.py                    # Simple entry point
```

## Configuration

### Environment Variables (.env)
```bash
DISCORD_BOT_TOKEN=your_token_here
POLL_CHANNEL_ID=your_channel_id_here
```

### Poll Configuration (config.json)
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

## Technical Implementation Details

### Discord Bot Setup
- **Intents Required**:
  - `message_content` - Read poll results
  - `guilds` - Access server information
  - `polls` - Create and read Discord polls

- **Permissions Required**:
  - Send Messages
  - Read Message History
  - Add Reactions
  - Create Polls

### Scheduler Implementation
- Uses APScheduler AsyncIOScheduler
- CronTrigger for weekly scheduling
- Timezone-aware scheduling (pytz)
- Poll completion scheduled with asyncio.sleep
- Automatic pod calculation on poll end

### Pod Optimization Algorithm

**Input**: Player availability matrix (player_id → [days])
**Output**: OptimizationResult with pods, players_with_games, players_without_games

**Process**:
1. Detect critical flexible players (5b)
2. Pre-assign critical players to required days
3. Count unique players per day (5a)
4. Sort days by (unique_count DESC, total_count DESC)
5. Greedily form 4-player pods
6. Track assigned players to prevent duplicates
7. Return formatted results

**Edge Cases Handled**:
- Player needed for multiple pods (choice scenario)
- Insufficient players for any pod
- Overflow players (more than can fit in pods)
- Empty availability

### Testing Strategy
- **Unit Tests**: 25 tests covering core functionality
- **Integration Tests**: Example scenarios with formatted output
- **Complex Scenarios**: 12 progressive test cases
- **All Tests Passing**: 37/37 ✅

## Development Timeline

### Session 1: Initial Implementation
- Created Discord bot with poll functionality
- Implemented basic greedy algorithm
- Added scheduler for automated polls
- Created comprehensive test suite
- Initialized Git repository

### Session 2: Algorithm Improvements
- Implemented 5a: Unique Player Priority
- Implemented 5b: Critical Flexible Player Assignment
- All 12 test scenarios passing
- Pushed to GitHub

### Session 3: Poll Completion Feature
- Removed manual cutoff schedule
- Implemented automatic calculation when poll ends
- Used asyncio.sleep for duration-based completion
- Updated configuration and documentation

### Session 4: Project Restructure
- Reorganized to Python best practices (src/ layout)
- Implemented Discord cogs pattern
- Separated tests/, config/, docs/, scripts/
- Created run.py entry point
- Updated all imports and tests
- All 37 tests passing

### Session 5: Docker Deployment
- Created Dockerfile with multi-stage build
- Added docker-compose.yml
- Created comprehensive DOCKER.md guide
- Configured security (non-root user)
- Set resource limits
- Added log rotation

### Session 6: Status Command
- Added !ping command for bot health check
- Shows latency in milliseconds
- Updated all documentation
- Deployed to production

## Git Commit History

```
d1f9dc8 - Add ping command for bot status check
7784649 - Add Docker support for easy deployment
ab797b0 - Restructure project to follow Python best practices
5a2e71e - Add automatic pod calculation when polls end
e670197 - Implement 5b: Critical Flexible Player Assignment
7bb9e50 - Initial commit: Discord Commander pod bot with 5a optimization
```

## Deployment

**Production Environment**: Docker container on home server
**Deployment Method**: docker-compose
**Status**: Deployed and running
**Next Scheduled Poll**: Sunday at configured time

### Deployment Commands
```bash
# Deploy
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Update
git pull && docker-compose up -d --build
```

## Future Enhancement Ideas

- [ ] Customizable poll days without code changes
- [ ] Player priority/rotation system
- [ ] Statistics tracking (games played per player)
- [ ] Support for different game formats (not just 4-player)
- [ ] Web dashboard for configuration
- [ ] Database persistence (currently in-memory)
- [ ] Player availability history
- [ ] Notification preferences
- [ ] Integration with calendar systems

## Key Design Decisions

### Why Discord Native Polls?
- Better user experience than reactions
- Built-in multi-select support
- Clean UI/UX
- No custom database needed for votes

### Why Greedy Algorithm vs Full Optimization?
- Fast execution (O(n) instead of exponential)
- Good enough for typical use case (8-20 players)
- Easier to understand and debug
- 5a + 5b enhancements handle most edge cases

### Why Docker?
- Consistent deployment across environments
- Easy updates (git pull + rebuild)
- Resource isolation
- Simple rollback if needed
- No Python version conflicts

### Why Cogs Pattern?
- Modular command organization
- Easy to add new command categories
- Follows discord.py best practices
- Clean separation of concerns

### Why Automatic Poll Completion?
- User requested feature
- Simpler than separate cutoff schedule
- Self-contained: poll creates → waits → calculates
- Less configuration needed

## Testing & Quality

- **Test Coverage**: 37 tests, all passing
- **Linting**: None configured yet (future improvement)
- **Type Hints**: Partial (future improvement)
- **Documentation**: Comprehensive user docs
- **Code Comments**: Docstrings on all major functions

## Dependencies

```
discord.py>=2.3.0       # Discord bot framework
python-dotenv>=1.0.0    # Environment variable management
APScheduler>=3.10.0     # Scheduled job execution
pytz>=2024.1            # Timezone handling
```

## Development Notes

- **Python command**: Use `python3` (not `python`) to run scripts and tests
- **Run tests**: `python3 -m unittest discover tests -v`
- **Docker command**: Use `docker compose` (not `docker-compose`) for container management

## Contributing

This bot was developed iteratively with Claude Code. All code is production-ready and tested.

**Development Approach**:
1. Gather requirements through conversation
2. Plan implementation with task breakdown
3. Implement features with tests
4. Refactor based on best practices
5. Document thoroughly
6. Deploy with Docker

## License

MIT License - feel free to use and modify as needed!

---

**Built with Claude Code** - An AI pair programming tool by Anthropic
**Development Sessions**: 6
**Total Commits**: 6
**Lines of Code**: ~1,500 (excluding tests)
**Documentation Pages**: 4
