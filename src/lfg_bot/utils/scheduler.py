"""
Scheduler for automated poll creation.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import discord
from typing import Dict, Any
import pytz


class PollScheduler:
    """Manages scheduled poll creation."""

    def __init__(self, bot, channel: discord.TextChannel, config: Dict[str, Any]):
        """
        Initialize the scheduler.

        Args:
            bot: Discord bot instance
            channel: Channel to post polls in
            config: Configuration dictionary
        """
        self.bot = bot
        self.channel = channel
        self.config = config
        self.scheduler = AsyncIOScheduler()

        # Store config for poll creation
        self.config = config

    def start(self):
        """Start the scheduler with configured jobs."""
        # Parse poll creation schedule
        poll_schedule = self.config['poll_schedule']
        timezone = pytz.timezone(poll_schedule.get('timezone', 'UTC'))

        # Add poll creation job
        poll_trigger = CronTrigger(
            day_of_week=poll_schedule['day_of_week'],
            hour=poll_schedule['hour'],
            minute=poll_schedule['minute'],
            timezone=timezone
        )

        self.scheduler.add_job(
            self._create_poll_job,
            trigger=poll_trigger,
            id='poll_creation',
            name='Weekly Poll Creation',
            replace_existing=True
        )

        self.scheduler.start()
        print(f'Scheduler started with poll creation on {poll_schedule["day_of_week"]} at {poll_schedule["hour"]:02d}:{poll_schedule["minute"]:02d} {timezone}')
        print(f'Use !calculatepods to manually calculate pods from poll results')

    async def _create_poll_job(self):
        """Job wrapper for poll creation."""
        from lfg_bot.bot import scheduled_poll_creation
        await scheduled_poll_creation(self.channel, self.config)

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        print('Scheduler stopped')
