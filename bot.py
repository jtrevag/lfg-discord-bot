"""
Discord bot for Commander game pod management.
"""

import os
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv
from typing import Dict, List
from datetime import timedelta
import asyncio

from pod_optimizer import optimize_pods, format_pod_results
from scheduler import PollScheduler

# Load environment variables
load_dotenv()

# Configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.polls = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Global state
active_poll_id = None
poll_scheduler = None


@bot.event
async def on_ready():
    """Called when bot is ready."""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')

    # Start the scheduler
    global poll_scheduler
    channel = bot.get_channel(int(os.getenv('POLL_CHANNEL_ID')))
    if channel:
        poll_scheduler = PollScheduler(bot, channel, config)
        poll_scheduler.start()
        print('Poll scheduler started!')
    else:
        print('Warning: Poll channel not found. Check POLL_CHANNEL_ID in .env')


@bot.command(name='createpoll')
@commands.has_permissions(administrator=True)
async def create_poll_command(ctx):
    """Manually create a poll (admin only)."""
    await create_poll(ctx.channel)


@bot.command(name='calculatepods')
@commands.has_permissions(administrator=True)
async def calculate_pods_command(ctx):
    """Manually trigger pod calculation from the latest poll (admin only)."""
    global active_poll_id

    if not active_poll_id:
        await ctx.send("No active poll found. Create a poll first with !createpoll")
        return

    # Fetch the poll message
    try:
        message = await ctx.channel.fetch_message(active_poll_id)
        if message.poll:
            await process_poll_results(message.poll, ctx.channel)
        else:
            await ctx.send("The message doesn't contain a poll.")
    except discord.NotFound:
        await ctx.send("Poll message not found.")
    except Exception as e:
        await ctx.send(f"Error fetching poll: {e}")


async def create_poll(channel: discord.TextChannel) -> discord.Message:
    """
    Create a poll in the specified channel.

    Args:
        channel: Discord channel to post the poll in

    Returns:
        The message containing the poll
    """
    global active_poll_id

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

    active_poll_id = message.id
    print(f'Poll created with ID: {active_poll_id}')

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


async def process_poll_results(poll: discord.Poll, channel: discord.TextChannel):
    """
    Process poll results and calculate optimal pods.

    Args:
        poll: The Discord poll object
        channel: Channel to send results to
    """
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

    # Format and send results
    message = format_pod_results(result)
    await channel.send(message)

    print(f'Pods calculated: {len(result.pods)} pods formed')
    print(f'Players with games: {len(result.players_with_games)}')
    print(f'Players without games: {len(result.players_without_games)}')


async def scheduled_poll_creation(channel: discord.TextChannel):
    """Called by scheduler to create a poll."""
    print('Creating scheduled poll...')
    await create_poll(channel)


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        print(f'Error: {error}')


def main():
    """Run the bot."""
    token = os.getenv('DISCORD_BOT_TOKEN')

    if not token:
        print("Error: DISCORD_BOT_TOKEN not found in .env file")
        print("Please copy .env.example to .env and add your bot token")
        return

    bot.run(token)


if __name__ == '__main__':
    main()
