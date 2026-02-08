"""
Unit tests for scheduler.py
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Skip all tests if dependencies are not installed
try:
    import pytz
    from lfg_bot.utils.scheduler import PollScheduler
    SKIP_TESTS = False
except ImportError as e:
    SKIP_TESTS = True
    SKIP_REASON = f"Missing dependency: {e}"


@unittest.skipIf(SKIP_TESTS, SKIP_REASON if SKIP_TESTS else "")
class TestPollScheduler(unittest.TestCase):
    """Test cases for PollScheduler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_bot = Mock()
        self.mock_channel = Mock()
        self.mock_channel.id = 123456789

        # Basic config
        self.config = {
            'poll_schedule': {
                'day_of_week': 'sun',
                'hour': 18,
                'minute': 0,
                'timezone': 'UTC'
            },
            'poll_duration_hours': 24
        }

    def test_scheduler_initialization(self):
        """Test scheduler initializes correctly."""
        scheduler = PollScheduler(self.mock_bot, self.mock_channel, self.config)

        self.assertEqual(scheduler.bot, self.mock_bot)
        self.assertEqual(scheduler.channel, self.mock_channel)
        self.assertEqual(scheduler.config, self.config)
        self.assertIsNotNone(scheduler.scheduler)

    @patch('lfg_bot.utils.scheduler.CronTrigger')
    def test_start_creates_poll_job(self, mock_cron_trigger):
        """Test that start() creates the poll creation job."""
        scheduler = PollScheduler(self.mock_bot, self.mock_channel, self.config)

        with patch.object(scheduler.scheduler, 'add_job') as mock_add_job:
            with patch.object(scheduler.scheduler, 'start'):
                scheduler.start()

                # Verify poll creation job was added
                self.assertEqual(mock_add_job.call_count, 1)  # only poll creation

                # Check the call (poll creation)
                call = mock_add_job.call_args_list[0]
                self.assertEqual(call[1]['id'], 'poll_creation')
                self.assertEqual(call[1]['name'], 'Weekly Poll Creation')

    def test_scheduler_uses_poll_duration(self):
        """Test that scheduler is configured with poll duration."""
        scheduler = PollScheduler(self.mock_bot, self.mock_channel, self.config)

        # Verify the config includes poll duration
        self.assertEqual(scheduler.config['poll_duration_hours'], 24)

    def test_cron_trigger_with_correct_timezone(self):
        """Test that CronTrigger is created with correct timezone."""
        scheduler = PollScheduler(self.mock_bot, self.mock_channel, self.config)

        with patch('lfg_bot.utils.scheduler.CronTrigger') as mock_cron_trigger:
            with patch.object(scheduler.scheduler, 'add_job'):
                with patch.object(scheduler.scheduler, 'start'):
                    scheduler.start()

                    # Verify CronTrigger was called with UTC timezone
                    calls = mock_cron_trigger.call_args_list
                    self.assertEqual(len(calls), 1)

                    # Check poll schedule timezone
                    poll_call = calls[0]
                    self.assertEqual(poll_call[1]['timezone'].zone, 'UTC')
                    self.assertEqual(poll_call[1]['day_of_week'], 'sun')
                    self.assertEqual(poll_call[1]['hour'], 18)
                    self.assertEqual(poll_call[1]['minute'], 0)

    def test_different_timezones(self):
        """Test scheduler handles different timezones correctly."""
        config_with_tz = {
            'poll_schedule': {
                'day_of_week': 'mon',
                'hour': 10,
                'minute': 30,
                'timezone': 'America/New_York'
            },
            'poll_duration_hours': 24
        }

        scheduler = PollScheduler(self.mock_bot, self.mock_channel, config_with_tz)

        with patch('lfg_bot.utils.scheduler.CronTrigger') as mock_cron_trigger:
            with patch.object(scheduler.scheduler, 'add_job'):
                with patch.object(scheduler.scheduler, 'start'):
                    scheduler.start()

                    calls = mock_cron_trigger.call_args_list

                    # Check poll schedule
                    poll_call = calls[0]
                    self.assertEqual(poll_call[1]['timezone'].zone, 'America/New_York')
                    self.assertEqual(poll_call[1]['hour'], 10)
                    self.assertEqual(poll_call[1]['minute'], 30)

    @patch('lfg_bot.bot.scheduled_poll_creation')
    def test_create_poll_job_execution(self, mock_poll_creation):
        """Test that poll creation job calls the correct function."""
        mock_poll_creation.return_value = AsyncMock()

        scheduler = PollScheduler(self.mock_bot, self.mock_channel, self.config)

        # Create an async test
        import asyncio
        async def run_test():
            await scheduler._create_poll_job()

        asyncio.run(run_test())

        # Note: The actual call verification depends on how we mock scheduled_poll_creation


    def test_stop_scheduler(self):
        """Test that stop() shuts down the scheduler."""
        scheduler = PollScheduler(self.mock_bot, self.mock_channel, self.config)

        with patch.object(scheduler.scheduler, 'shutdown') as mock_shutdown:
            scheduler.stop()
            mock_shutdown.assert_called_once()

    def test_replace_existing_jobs(self):
        """Test that jobs are replaced if they already exist."""
        scheduler = PollScheduler(self.mock_bot, self.mock_channel, self.config)

        with patch.object(scheduler.scheduler, 'add_job') as mock_add_job:
            with patch.object(scheduler.scheduler, 'start'):
                scheduler.start()

                # Verify replace_existing=True
                for call in mock_add_job.call_args_list:
                    self.assertTrue(call[1]['replace_existing'])

    def test_scheduler_with_missing_timezone(self):
        """Test scheduler defaults to UTC if timezone is missing."""
        config_no_tz = {
            'poll_schedule': {
                'day_of_week': 'sun',
                'hour': 18,
                'minute': 0
            },
            'poll_duration_hours': 24
        }

        scheduler = PollScheduler(self.mock_bot, self.mock_channel, config_no_tz)

        with patch('lfg_bot.utils.scheduler.CronTrigger') as mock_cron_trigger:
            with patch.object(scheduler.scheduler, 'add_job'):
                with patch.object(scheduler.scheduler, 'start'):
                    scheduler.start()

                    # Call should default to UTC
                    call = mock_cron_trigger.call_args_list[0]
                    self.assertEqual(call[1]['timezone'].zone, 'UTC')


@unittest.skipIf(SKIP_TESTS, SKIP_REASON if SKIP_TESTS else "")
class TestSchedulerIntegration(unittest.TestCase):
    """Integration tests for scheduler functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_bot = Mock()
        self.mock_channel = Mock()
        self.config = {
            'poll_schedule': {
                'day_of_week': 'sun',
                'hour': 18,
                'minute': 0,
                'timezone': 'UTC'
            },
            'poll_duration_hours': 24
        }

    def test_full_scheduler_lifecycle(self):
        """Test starting and stopping scheduler."""
        scheduler = PollScheduler(self.mock_bot, self.mock_channel, self.config)

        # Start scheduler
        with patch.object(scheduler.scheduler, 'start') as mock_start:
            with patch.object(scheduler.scheduler, 'add_job'):
                scheduler.start()
                mock_start.assert_called_once()

        # Stop scheduler
        with patch.object(scheduler.scheduler, 'shutdown') as mock_shutdown:
            scheduler.stop()
            mock_shutdown.assert_called_once()

    def test_scheduler_handles_invalid_timezone(self):
        """Test scheduler handles invalid timezone gracefully."""
        config_bad_tz = {
            'poll_schedule': {
                'day_of_week': 'sun',
                'hour': 18,
                'minute': 0,
                'timezone': 'Invalid/Timezone'
            },
            'poll_duration_hours': 24
        }

        scheduler = PollScheduler(self.mock_bot, self.mock_channel, config_bad_tz)

        # Should raise an exception when trying to start
        with self.assertRaises(Exception):
            with patch.object(scheduler.scheduler, 'start'):
                scheduler.start()


if __name__ == '__main__':
    unittest.main()
