"""Unit tests for database models and helper functions."""

import unittest
from datetime import datetime, date, timedelta
from peewee import SqliteDatabase
from dataclasses import dataclass
from typing import List

# Import database models and functions
import sys
sys.path.insert(0, '/Users/jamesgale/codebase/lfg-discord-bot/src')

from lfg_bot.utils.database import (
    db, League, Player, Poll, Pod, GameResult, PlayerStats,
    initialize_database, verify_database, get_active_league,
    get_real_name, get_discord_id, format_player_name,
    save_poll_and_pods, record_game_result, update_player_stats,
    get_leaderboard, get_head_to_head, get_recent_games, create_new_league
)


# Mock OptimizationResult for testing
@dataclass
class PodAssignment:
    day: str
    players: List[str]


@dataclass
class OptimizationResult:
    pods: List[PodAssignment]
    players_with_games: set
    players_without_games: set


class TestDatabaseModels(unittest.TestCase):
    """Test database models and basic operations."""

    def setUp(self):
        """Create in-memory test database."""
        # Use in-memory database for tests
        test_db = SqliteDatabase(':memory:')
        db.init(':memory:')

        # Create tables
        db.create_tables([League, Player, Poll, Pod, GameResult, PlayerStats])

        self.db = db

    def tearDown(self):
        """Close database after each test."""
        self.db.close()

    def test_create_league(self):
        """Test creating a league."""
        league = League.create(
            name="Test League",
            start_date=date(2026, 1, 1),
            is_active=True
        )

        assert league.name == "Test League"
        assert league.is_active == True
        assert isinstance(league.created_at, datetime)

    def test_create_player(self):
        """Test creating a player."""
        player = Player.create(
            discord_user_id="123456789",
            real_name="Patrick"
        )

        assert player.discord_user_id == "123456789"
        assert player.real_name == "Patrick"

    def test_create_poll(self):
        """Test creating a poll."""
        league = League.create(name="Test", start_date=date.today())
        poll = Poll.create(
            league=league,
            discord_message_id="999999",
            poll_question="Test poll?"
        )

        assert poll.league == league
        assert poll.discord_message_id == "999999"

    def test_create_pod(self):
        """Test creating a pod."""
        league = League.create(name="Test", start_date=date.today())
        poll = Poll.create(league=league, discord_message_id="111")

        pod = Pod.create(
            poll=poll,
            day_of_week="Monday",
            player1_id="100",
            player2_id="200",
            player3_id="300",
            player4_id="400"
        )

        assert pod.poll == poll
        assert pod.day_of_week == "Monday"
        assert pod.status == "scheduled"
        assert len([pod.player1_id, pod.player2_id, pod.player3_id, pod.player4_id]) == 4


class TestDatabaseHelpers(unittest.TestCase):
    """Test database helper functions."""

    def setUp(self):
        """Create in-memory test database."""
        db.init(':memory:')
        db.create_tables([League, Player, Poll, Pod, GameResult, PlayerStats])
        self.db = db

    def tearDown(self):
        """Close database."""
        self.db.close()

    def test_get_active_league(self):
        """Test getting active league."""
        # Create inactive league
        League.create(name="Old", start_date=date(2025, 1, 1), is_active=False)

        # Create active league
        active = League.create(name="Current", start_date=date(2026, 1, 1), is_active=True)

        # Test
        result = get_active_league()
        assert result.name == "Current"
        assert result.is_active == True

    def test_get_active_league_none(self):
        """Test getting active league when none exists."""
        result = get_active_league()
        assert result is None

    def test_get_real_name(self):
        """Test getting player's real name."""
        Player.create(discord_user_id="123", real_name="Patrick")

        name = get_real_name("123")
        assert name == "Patrick"

    def test_get_real_name_not_found(self):
        """Test getting real name for non-existent player."""
        name = get_real_name("999")
        assert name is None

    def test_get_discord_id(self):
        """Test getting Discord ID from real name."""
        Player.create(discord_user_id="456", real_name="John")

        discord_id = get_discord_id("John")
        assert discord_id == "456"

    def test_get_discord_id_not_found(self):
        """Test getting Discord ID for non-existent name."""
        discord_id = get_discord_id("Unknown")
        assert discord_id is None

    def test_format_player_name_with_real_name(self):
        """Test formatting player name with real name."""
        Player.create(discord_user_id="789", real_name="Matt")

        formatted = format_player_name("789")
        assert formatted == "<@789> (Matt)"

    def test_format_player_name_without_real_name(self):
        """Test formatting player name without real name."""
        formatted = format_player_name("999")
        assert formatted == "<@999>"

    def test_save_poll_and_pods(self):
        """Test saving poll and pods to database."""
        # Create active league
        League.create(name="Test", start_date=date.today(), is_active=True)

        # Create mock bot config
        class MockBot:
            config = {
                'poll_question': 'Test question?',
                'poll_days': ['Monday', 'Tuesday']
            }

        bot = MockBot()

        # Create optimization result
        result = OptimizationResult(
            pods=[
                PodAssignment(day="Monday", players=["100", "200", "300", "400"]),
                PodAssignment(day="Tuesday", players=["500", "600", "700", "800"])
            ],
            players_with_games={"100", "200", "300", "400", "500", "600", "700", "800"},
            players_without_games=set()
        )

        # Save
        poll = save_poll_and_pods(bot, "MSG123", result, ['Monday', 'Tuesday'])

        # Verify poll created
        assert poll.discord_message_id == "MSG123"

        # Verify pods created
        pods = list(Pod.select().where(Pod.poll == poll))
        assert len(pods) == 2

        # Verify players auto-created
        assert Player.select().count() == 8

    def test_record_game_result(self):
        """Test recording a game result."""
        # Setup
        league = League.create(name="Test", start_date=date.today(), is_active=True)
        poll = Poll.create(league=league, discord_message_id="MSG1")
        pod = Pod.create(
            poll=poll,
            day_of_week="Monday",
            player1_id="100",
            player2_id="200",
            player3_id="300",
            player4_id="400"
        )

        # Record result
        result = record_game_result(
            pod_id=pod.id,
            winner_id="100",
            reported_by_id="200",
            notes="Great game!"
        )

        # Verify
        assert result.winner_id == "100"
        assert result.reported_by_id == "200"
        assert result.notes == "Great game!"

        # Verify pod status updated
        pod_updated = Pod.get_by_id(pod.id)
        assert pod_updated.status == "completed"

    def test_update_player_stats(self):
        """Test calculating player statistics."""
        # Setup league and poll
        league = League.create(name="Test", start_date=date.today())
        poll = Poll.create(league=league, discord_message_id="MSG1")

        # Create 3 completed pods
        pod1 = Pod.create(
            poll=poll, day_of_week="Monday",
            player1_id="100", player2_id="200", player3_id="300", player4_id="400",
            status="completed"
        )
        pod2 = Pod.create(
            poll=poll, day_of_week="Tuesday",
            player1_id="100", player2_id="500", player3_id="600", player4_id="700",
            status="completed"
        )
        pod3 = Pod.create(
            poll=poll, day_of_week="Wednesday",
            player1_id="100", player2_id="200", player3_id="800", player4_id="900",
            status="completed"
        )

        # Record results (player 100 wins 2/3 games)
        GameResult.create(pod=pod1, winner_id="100", reported_by_id="100")
        GameResult.create(pod=pod2, winner_id="500", reported_by_id="500")
        GameResult.create(pod=pod3, winner_id="100", reported_by_id="100")

        # Calculate stats
        update_player_stats(league.id)

        # Check player 100's stats (2 wins, 3 games = 66.67%)
        stats = PlayerStats.get(
            (PlayerStats.league_id == league.id) & (PlayerStats.player_id == "100")
        )
        assert stats.games_played == 3
        assert stats.games_won == 2
        assert abs(stats.win_rate - 66.67) < 0.1

        # Check player 200's stats (0 wins, 2 games = 0%)
        stats200 = PlayerStats.get(
            (PlayerStats.league_id == league.id) & (PlayerStats.player_id == "200")
        )
        assert stats200.games_played == 2
        assert stats200.games_won == 0
        assert stats200.win_rate == 0.0

    def test_get_leaderboard(self):
        """Test getting leaderboard."""
        league = League.create(name="Test", start_date=date.today())

        # Create player stats (3 players, different win rates)
        PlayerStats.create(league=league, player_id="100", games_played=10, games_won=8, win_rate=80.0)
        PlayerStats.create(league=league, player_id="200", games_played=10, games_won=5, win_rate=50.0)
        PlayerStats.create(league=league, player_id="300", games_played=2, games_won=2, win_rate=100.0)  # Too few games

        # Get leaderboard (min 3 games)
        leaderboard = get_leaderboard(league.id, min_games=3, limit=10)

        # Should have 2 players (300 excluded due to min games)
        assert len(list(leaderboard)) == 2

        # Should be sorted by win rate (100 first with 80%)
        leaders = list(leaderboard)
        assert leaders[0].player_id == "100"
        assert leaders[0].win_rate == 80.0
        assert leaders[1].player_id == "200"

    def test_get_head_to_head(self):
        """Test head-to-head statistics."""
        league = League.create(name="Test", start_date=date.today())
        poll = Poll.create(league=league, discord_message_id="MSG1")

        # Create pods where player 100 and 200 play together
        pod1 = Pod.create(
            poll=poll, day_of_week="Monday",
            player1_id="100", player2_id="200", player3_id="300", player4_id="400",
            status="completed"
        )
        pod2 = Pod.create(
            poll=poll, day_of_week="Tuesday",
            player1_id="100", player2_id="200", player3_id="500", player4_id="600",
            status="completed"
        )

        # Pod where they don't play together (should be ignored)
        pod3 = Pod.create(
            poll=poll, day_of_week="Wednesday",
            player1_id="100", player2_id="700", player3_id="800", player4_id="900",
            status="completed"
        )

        # Record results (100 wins once, 200 wins once)
        GameResult.create(pod=pod1, winner_id="100", reported_by_id="100")
        GameResult.create(pod=pod2, winner_id="200", reported_by_id="200")
        GameResult.create(pod=pod3, winner_id="100", reported_by_id="100")

        # Get H2H stats
        h2h = get_head_to_head(league.id, "100", "200")

        assert h2h['total_games'] == 2
        assert h2h['player1_wins'] == 1
        assert h2h['player2_wins'] == 1
        assert h2h['other_wins'] == 0
        assert h2h['player1_win_rate'] == 50.0
        assert h2h['player2_win_rate'] == 50.0

    def test_get_recent_games(self):
        """Test getting recent games."""
        league = League.create(name="Test", start_date=date.today())
        poll = Poll.create(league=league, discord_message_id="MSG1")

        # Create multiple pods
        pods = []
        for i in range(5):
            pod = Pod.create(
                poll=poll,
                day_of_week="Monday",
                player1_id="100", player2_id="200", player3_id="300", player4_id="400",
                status="completed"
            )
            pods.append(pod)

        # Create results with different timestamps
        for i, pod in enumerate(pods):
            GameResult.create(
                pod=pod,
                winner_id="100",
                reported_by_id="100",
                reported_at=datetime.now() - timedelta(days=i)
            )

        # Get recent games (limit 3)
        recent = list(get_recent_games(limit=3))

        assert len(recent) == 3
        # Should be sorted by most recent first
        assert recent[0].reported_at > recent[1].reported_at
        assert recent[1].reported_at > recent[2].reported_at

    def test_create_new_league(self):
        """Test creating a new league."""
        # Create initial active league
        old_league = League.create(
            name="Old League",
            start_date=date(2025, 1, 1),
            is_active=True
        )

        # Create new league
        new_league = create_new_league("New League", "2026-01-01")

        # Verify new league is active
        assert new_league.is_active == True
        assert new_league.name == "New League"

        # Verify old league is archived
        old_league_updated = League.get_by_id(old_league.id)
        assert old_league_updated.is_active == False
        assert old_league_updated.end_date is not None


if __name__ == '__main__':
    unittest.main()
