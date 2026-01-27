"""
Unit tests for pod_optimizer.py
"""

import unittest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from lfg_bot.utils.pod_optimizer import (
    optimize_pods,
    format_pod_results,
    PodAssignment,
    OptimizationResult,
    _find_best_assignment,
    _detect_choice_scenario
)


class TestPodOptimizer(unittest.TestCase):
    """Test cases for pod optimization functions."""

    def test_basic_four_player_pod(self):
        """Test basic scenario with exactly 4 players on one day."""
        availability = {
            'alice': ['Monday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday']
        }

        result = optimize_pods(availability)

        self.assertEqual(len(result.pods), 1)
        self.assertEqual(result.pods[0].day, 'Monday')
        self.assertEqual(len(result.pods[0].players), 4)
        self.assertEqual(len(result.players_with_games), 4)
        self.assertEqual(len(result.players_without_games), 0)

    def test_insufficient_players(self):
        """Test with fewer than 4 players."""
        availability = {
            'alice': ['Monday'],
            'bob': ['Monday'],
            'charlie': ['Monday']
        }

        result = optimize_pods(availability)

        self.assertEqual(len(result.pods), 0)
        self.assertEqual(len(result.players_with_games), 0)
        self.assertEqual(len(result.players_without_games), 3)

    def test_multiple_pods_same_day(self):
        """Test forming multiple pods on the same day."""
        availability = {
            'p1': ['Monday'],
            'p2': ['Monday'],
            'p3': ['Monday'],
            'p4': ['Monday'],
            'p5': ['Monday'],
            'p6': ['Monday'],
            'p7': ['Monday'],
            'p8': ['Monday']
        }

        result = optimize_pods(availability)

        self.assertEqual(len(result.pods), 2)
        self.assertEqual(len(result.players_with_games), 8)
        self.assertEqual(len(result.players_without_games), 0)

    def test_pods_across_multiple_days(self):
        """Test forming pods on different days."""
        availability = {
            'alice': ['Monday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
            'eve': ['Wednesday'],
            'frank': ['Wednesday'],
            'grace': ['Wednesday'],
            'henry': ['Wednesday']
        }

        result = optimize_pods(availability)

        self.assertEqual(len(result.pods), 2)
        self.assertEqual(len(result.players_with_games), 8)

        days = [pod.day for pod in result.pods]
        self.assertIn('Monday', days)
        self.assertIn('Wednesday', days)

    def test_multi_day_player(self):
        """Test player available on multiple days."""
        availability = {
            'alice': ['Monday', 'Wednesday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
            'eve': ['Wednesday'],
            'frank': ['Wednesday'],
            'grace': ['Wednesday']
        }

        result = optimize_pods(availability)

        # Should form at least one pod
        self.assertGreaterEqual(len(result.pods), 1)
        # Alice might be in Monday or Wednesday pod
        # At least 4 players should get games
        self.assertGreaterEqual(len(result.players_with_games), 4)

    def test_five_players_one_left_out(self):
        """Test with 5 players - one should be left out."""
        availability = {
            'p1': ['Monday'],
            'p2': ['Monday'],
            'p3': ['Monday'],
            'p4': ['Monday'],
            'p5': ['Monday']
        }

        result = optimize_pods(availability)

        self.assertEqual(len(result.pods), 1)
        self.assertEqual(len(result.players_with_games), 4)
        self.assertEqual(len(result.players_without_games), 1)

    def test_no_availability(self):
        """Test with no player availability."""
        availability = {}

        result = optimize_pods(availability)

        self.assertEqual(len(result.pods), 0)
        self.assertEqual(len(result.players_with_games), 0)
        self.assertEqual(len(result.players_without_games), 0)

    def test_choice_scenario_detection(self):
        """Test detection of scenario where player must choose."""
        availability = {
            'alice': ['Monday', 'Wednesday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
            'eve': ['Wednesday'],
            'frank': ['Wednesday'],
            'grace': ['Wednesday']
        }

        result = optimize_pods(availability)

        # This might trigger a choice scenario if Alice is critical for both
        # (depending on the algorithm's selection)
        if result.choice_required:
            self.assertEqual(result.choice_required['player'], 'alice')
            self.assertIn('day1', result.choice_required)
            self.assertIn('day2', result.choice_required)

    def test_complete_pod_with_double_play_opportunity(self):
        """
        Test scenario where a complete 4-player pod exists on one day,
        and a flexible player could play twice to enable a second pod.

        Real scenario from user:
        - Monday: 4 players (including Patrick and Eli)
        - Tuesday: 3 players (can't form pod)
        - Wednesday: 5 players (including Patrick and Eli)

        Expected: Monday pod forms, Wednesday prompts Patrick or Eli to play twice.
        """
        availability = {
            'n8': ['Monday'],
            'chris': ['Monday'],
            'patrick': ['Monday', 'Tuesday', 'Wednesday'],
            'eli': ['Monday', 'Wednesday'],
            'chad': ['Tuesday', 'Wednesday'],
            'matt': ['Tuesday', 'Wednesday'],
            'trevor': ['Wednesday']
        }

        result = optimize_pods(availability)

        # Should form 1 pod (Monday) and have a choice scenario for Wednesday
        self.assertEqual(len(result.pods), 1,
            "Should form 1 pod (Monday) and prompt for Wednesday")

        # Monday should be the formed pod
        self.assertEqual(result.pods[0].day, 'Monday',
            "Monday should form a pod (has exactly 4 players)")

        # 4 players should have confirmed games (Monday pod)
        self.assertEqual(len(result.players_with_games), 4,
            "4 players have confirmed games from Monday pod")

        # Should have a choice scenario for double-play
        self.assertIsNotNone(result.choice_required,
            "Should have a choice scenario for Wednesday")
        self.assertEqual(result.choice_required['scenario'], 'double_play_needed',
            "Choice scenario should be for double-play")
        self.assertEqual(result.choice_required['day'], 'Wednesday',
            "Choice should be for Wednesday")

        # Should list the 3 waiting players
        self.assertEqual(len(result.choice_required['waiting_players']), 3,
            "Should have 3 players waiting (trevor, chad, matt)")

        # Should list flexible candidates (patrick and eli)
        self.assertIn('patrick', result.choice_required['flexible_candidates'],
            "Patrick should be a flexible candidate")
        self.assertIn('eli', result.choice_required['flexible_candidates'],
            "Eli should be a flexible candidate")


    def test_eight_flexible_players_one_day_three_on_other_days(self):
        """
        Bug reproduction: 8 flexible players on one day should form 2 pods.

        Scenario that caused bug:
        - Monday: 8 players (all flexible, each also voted for another day)
        - Tuesday: 3 players (p1, p2, p3 - can't form pod alone)
        - Wednesday: 3 players (p4, p5, p6 - can't form pod alone)
        - Thursday: 3 players (p7, p8, plus one person unique to Thursday)

        Expected: Monday forms 2 pods of 4 players each (8 players get games).
        Bug: Only 1 pod was formed because all flexible players were being
             reserved as "critical" for their secondary days, leaving no one
             available to form Monday pods.
        """
        availability = {
            # All 8 available Monday and one other day
            'p1': ['Monday', 'Tuesday'],
            'p2': ['Monday', 'Tuesday'],
            'p3': ['Monday', 'Tuesday'],
            'p4': ['Monday', 'Wednesday'],
            'p5': ['Monday', 'Wednesday'],
            'p6': ['Monday', 'Wednesday'],
            'p7': ['Monday', 'Thursday'],
            'p8': ['Monday', 'Thursday'],
            # One person unique to Thursday to make it 3 people
            'p9': ['Thursday'],
        }

        result = optimize_pods(availability)

        # Monday should form 2 pods with 8 players
        monday_pods = [p for p in result.pods if p.day == 'Monday']
        self.assertEqual(len(monday_pods), 2,
            f"Monday should have 2 pods, got {len(monday_pods)}. All pods: {result.pods}")

        # 8 players should have games (all Monday players)
        self.assertEqual(len(result.players_with_games), 8,
            f"8 players should have games, got {len(result.players_with_games)}: {result.players_with_games}")

        # p9 should not have a game (Thursday only has 3 people after Monday takes players)
        self.assertIn('p9', result.players_without_games,
            "p9 should not have a game (Thursday can't form a pod)")


class TestFormatResults(unittest.TestCase):
    """Test cases for result formatting."""

    def test_format_single_pod(self):
        """Test formatting a single pod result."""
        result = OptimizationResult(
            pods=[PodAssignment(day='Monday', players=['alice', 'bob', 'charlie', 'dave'])],
            players_with_games={'alice', 'bob', 'charlie', 'dave'},
            players_without_games=set()
        )

        formatted = format_pod_results(result)

        self.assertIn('Monday', formatted)
        self.assertIn('alice', formatted)
        self.assertIn('**Total players with games:** 4', formatted)

    def test_format_no_pods(self):
        """Test formatting when no pods can be formed."""
        result = OptimizationResult(
            pods=[],
            players_with_games=set(),
            players_without_games={'alice', 'bob'}
        )

        formatted = format_pod_results(result)

        self.assertIn('No pods could be formed', formatted)
        self.assertIn('Players without games', formatted)

    def test_format_with_leftover_players(self):
        """Test formatting with players who didn't get games."""
        result = OptimizationResult(
            pods=[PodAssignment(day='Monday', players=['p1', 'p2', 'p3', 'p4'])],
            players_with_games={'p1', 'p2', 'p3', 'p4'},
            players_without_games={'p5'}
        )

        formatted = format_pod_results(result)

        self.assertIn('Players without games', formatted)
        self.assertIn('p5', formatted)

    def test_format_choice_scenario(self):
        """Test formatting a choice scenario."""
        result = OptimizationResult(
            pods=[],
            players_with_games=set(),
            players_without_games=set(),
            choice_required={
                'player': 'alice',
                'scenario': 'critical_for_both',
                'day1': 'Monday',
                'day2': 'Wednesday',
                'pod1': ['alice', 'bob', 'charlie', 'dave'],
                'pod2': ['alice', 'eve', 'frank', 'grace'],
                'message': 'Alice must choose'
            }
        )

        formatted = format_pod_results(result)

        self.assertIn('PLAYER CHOICE REQUIRED', formatted)
        self.assertIn('alice', formatted)
        self.assertIn('Monday', formatted)
        self.assertIn('Wednesday', formatted)


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions."""

    def test_find_best_assignment_basic(self):
        """Test basic assignment finding."""
        day_to_players = {
            'Monday': ['alice', 'bob', 'charlie', 'dave']
        }
        all_players = {'alice', 'bob', 'charlie', 'dave'}

        result = _find_best_assignment(day_to_players, all_players)

        self.assertEqual(len(result.pods), 1)
        self.assertEqual(len(result.players_with_games), 4)

    def test_find_best_assignment_prioritizes_more_players(self):
        """Test that days with more players are prioritized."""
        day_to_players = {
            'Monday': ['alice', 'bob', 'charlie', 'dave', 'eve'],
            'Tuesday': ['frank', 'grace', 'henry', 'iris']
        }
        all_players = {'alice', 'bob', 'charlie', 'dave', 'eve', 'frank', 'grace', 'henry', 'iris'}

        result = _find_best_assignment(day_to_players, all_players)

        # Should form pods from both days
        self.assertEqual(len(result.pods), 2)


if __name__ == '__main__':
    unittest.main()
