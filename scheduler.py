"""
Scheduler for automated poll creation and cutoff handling.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import discord
from typing import Dict, Any
import pytz


class PollScheduler:
    """Manages scheduled poll creation and cutoff processing."""

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

        # Import here to avoid circular dependency
        from bot import scheduled_poll_creation, scheduled_cutoff
        self.poll_creation_func = scheduled_poll_creation
        self.cutoff_func = scheduled_cutoff

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

        # Parse cutoff schedule
        cutoff_schedule = self.config['cutoff_schedule']
        cutoff_timezone = pytz.timezone(cutoff_schedule.get('timezone', 'UTC'))

        # Add cutoff job
        cutoff_trigger = CronTrigger(
            day_of_week=cutoff_schedule['day_of_week'],
            hour=cutoff_schedule['hour'],
            minute=cutoff_schedule['minute'],
            timezone=cutoff_timezone
        )

        self.scheduler.add_job(
            self._cutoff_job,
            trigger=cutoff_trigger,
            id='poll_cutoff',
            name='Poll Cutoff and Pod Calculation',
            replace_existing=True
        )

        self.scheduler.start()
        print(f'Scheduler started with poll creation on {poll_schedule["day_of_week"]} at {poll_schedule["hour"]:02d}:{poll_schedule["minute"]:02d} {timezone}')
        print(f'Cutoff scheduled for {cutoff_schedule["day_of_week"]} at {cutoff_schedule["hour"]:02d}:{cutoff_schedule["minute"]:02d} {cutoff_timezone}')

    async def _create_poll_job(self):
        """Job wrapper for poll creation."""
        await self.poll_creation_func(self.channel)

    async def _cutoff_job(self):
        """Job wrapper for cutoff processing."""
        await self.cutoff_func(self.channel)

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        print('Scheduler stopped')
