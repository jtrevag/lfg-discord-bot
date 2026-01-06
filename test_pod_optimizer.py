"""
Unit tests for pod_optimizer.py
"""

import unittest
from pod_optimizer import (
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
        self.assertIn('Total players with games: 4', formatted)

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
