"""
Discord bot for Commander game pod management.
"""

import os
import json
import discord
from discord.ext import commands
from typing import Dict, List
from datetime import timedelta
import asyncio
import subprocess

from lfg_bot.utils.pod_optimizer import optimize_pods, format_pod_results
from lfg_bot.utils.scheduler import PollScheduler


def get_version():
    """Get the current version from git commit hash."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return 'unknown'


def load_config():
    """Load configuration from config/config.json."""
    config_path = 'config/config.json'
    with open(config_path, 'r') as f:
        return json.load(f)


def create_bot():
    """
    Create and configure the Discord bot.

    Returns:
        Configured Discord bot instance
    """
    # Bot setup
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.polls = True

    bot = commands.Bot(command_prefix='!', intents=intents)

    # Load configuration
    bot.config = load_config()

    # Global state
    bot.active_poll_id = None
    bot.poll_scheduler = None

    # Initialize database
    from lfg_bot.utils.database import initialize_database
    bot.db = initialize_database()

    # Register event handlers
    @bot.event
    async def on_ready():
        """Called when bot is ready."""
        version = get_version()
        print(f'{bot.user} has connected to Discord!')
        print(f'Bot version: {version}')
        print(f'Bot is in {len(bot.guilds)} guild(s)')

        # Verify database connectivity
        from lfg_bot.utils.database import verify_database
        verify_database(bot.db)
        print('Database initialized and verified')

        # Load cogs
        await bot.load_extension('lfg_bot.cogs.polls')
        print('Loaded cogs: polls')

        # Start the scheduler
        channel = bot.get_channel(int(os.getenv('POLL_CHANNEL_ID')))
        if channel:
            bot.poll_scheduler = PollScheduler(bot, channel, bot.config)
            bot.poll_scheduler.start()
            print('Poll scheduler started!')
        else:
            print('Warning: Poll channel not found. Check POLL_CHANNEL_ID in config/.env')

    @bot.event
    async def on_command_error(ctx, error):
        """Handle command errors."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
        elif isinstance(error, commands.CommandNotFound):
            pass  # Ignore unknown commands
        else:
            print(f'Error: {error}')

    return bot


async def create_poll(channel: discord.TextChannel, config: dict) -> discord.Message:
    """
    Create a poll in the specified channel.

    Args:
        channel: Discord channel to post the poll in
        config: Configuration dictionary

    Returns:
        The message containing the poll
    """
    # Get bot instance from channel
    bot = channel.guild.get_member(channel.guild.me.id).bot if hasattr(channel.guild, 'me') else None

    # Create poll with day options
    duration_hours = config.get('poll_duration_hours', 168)  # Default 7 days
    poll = discord.Poll(
        question=config['poll_question'],
        duration=timedelta(hours=duration_hours),
        multiple=True  # Allow multiple selections
    )

    # Add day options
    for day in config['poll_days']:
        poll.add_answer(text=day)

    # Send the poll
    message = await channel.send(
        content="**Weekly Commander Game Poll**\nSelect all days you're available to play!",
        poll=poll
    )

    # Store active poll ID on bot instance if available
    if hasattr(channel, '_state') and hasattr(channel._state, '_get_client'):
        bot_instance = channel._state._get_client()
        if hasattr(bot_instance, 'active_poll_id'):
            bot_instance.active_poll_id = message.id

    print(f'Poll created with ID: {message.id}')

    # Schedule automatic pod calculation when poll ends
    asyncio.create_task(schedule_poll_completion(message.id, channel, duration_hours))

    return message


async def schedule_poll_completion(poll_message_id: int, channel: discord.TextChannel, duration_hours: int):
    """
    Schedule automatic pod calculation when poll completes.

    Args:
        poll_message_id: ID of the poll message
        channel: Channel containing the poll
        duration_hours: How long the poll lasts
    """
    # Wait for the poll to complete
    wait_seconds = duration_hours * 3600
    print(f'Scheduled pod calculation in {duration_hours} hours (poll ID: {poll_message_id})')

    await asyncio.sleep(wait_seconds)

    # Poll has ended, calculate pods
    print(f'Poll {poll_message_id} completed, calculating pods...')
    try:
        message = await channel.fetch_message(poll_message_id)
        if message.poll:
            await channel.send("**Poll has ended! Calculating optimal pods...**")
            await process_poll_results(message.poll, channel)
        else:
            await channel.send("Error: Could not find poll data.")
    except discord.NotFound:
        print(f'Poll message {poll_message_id} not found')
    except Exception as e:
        print(f'Error processing poll completion: {e}')
        await channel.send(f"Error calculating pods: {e}")


async def process_poll_results(poll: discord.Poll, channel: discord.TextChannel, bot=None):
    """
    Process poll results and calculate optimal pods.

    Args:
        poll: The Discord poll object
        channel: Channel to send results to
        bot: Bot instance (optional, will fetch from channel if not provided)
    """
    # Get bot instance if not provided
    if bot is None:
        bot = channel.guild.me._state._get_client()

    # Extract votes from poll
    availability: Dict[str, List[str]] = {}

    # Get the answer for each day
    day_to_answer = {answer.text: answer for answer in poll.answers}

    # Process each answer's voters
    for day_name, answer in day_to_answer.items():
        # Note: answer.voters is an async iterator
        async for user in answer.voters():
            if user.bot:
                continue  # Skip bot votes

            user_id = str(user.id)
            if user_id not in availability:
                availability[user_id] = []
            availability[user_id].append(day_name)

    if not availability:
        await channel.send("No votes recorded yet. Waiting for players to vote!")
        return

    # Optimize pods
    result = optimize_pods(availability)

    # Save to database
    from lfg_bot.utils.database import save_poll_and_pods
    try:
        # Get poll message ID from poll context (it's from a message)
        poll_message_id = str(poll.message.id) if hasattr(poll, 'message') else "unknown"
        poll_record = save_poll_and_pods(
            bot=bot,
            discord_message_id=poll_message_id,
            result=result,
            poll_days=bot.config.get('poll_days', [])
        )
        print(f'Saved {len(result.pods)} pods to database (poll ID: {poll_record.id})')
    except Exception as e:
        print(f'Warning: Failed to save pods to database: {e}')
        # Continue anyway - don't break existing functionality

    # Format and send results
    message = format_pod_results(result)
    await channel.send(message)

    print(f'Pods calculated: {len(result.pods)} pods formed')
    print(f'Players with games: {len(result.players_with_games)}')
    print(f'Players without games: {len(result.players_without_games)}')


async def scheduled_poll_creation(channel: discord.TextChannel, config: dict):
    """
    Called by scheduler to create a poll.

    Args:
        channel: Channel to post poll in
        config: Configuration dictionary
    """
    print('Creating scheduled poll...')
    await create_poll(channel, config)
