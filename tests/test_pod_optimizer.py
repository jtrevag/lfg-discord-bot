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
    group_pods_by_day,
    PodAssignment,
    OptimizationResult,
    IncompletePod,
    _find_best_assignment,
    PREF_ONE_GAME_ONLY,
    PREF_NO_CONSECUTIVE,
    _can_assign_to_day
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
        # Incomplete pod with 1 player who couldn't form a game
        self.assertEqual(len(result.incomplete_pods), 1)
        self.assertEqual(result.incomplete_pods[0].day, 'Monday')
        self.assertEqual(result.incomplete_pods[0].needed, 3)

    def test_incomplete_pods_multiple_days(self):
        """Test incomplete pods are tracked per day."""
        availability = {
            'p1': ['Monday'],
            'p2': ['Monday'],
            'p3': ['Monday'],
            'p4': ['Monday'],
            'p5': ['Tuesday'],
            'p6': ['Tuesday'],
            'p7': ['Wednesday'],
        }

        result = optimize_pods(availability)

        self.assertEqual(len(result.pods), 1)  # One full pod on Monday
        self.assertEqual(len(result.incomplete_pods), 2)  # Tuesday (2) and Wednesday (1)

        # Find incomplete pods by day
        incomplete_by_day = {ip.day: ip for ip in result.incomplete_pods}
        self.assertIn('Tuesday', incomplete_by_day)
        self.assertIn('Wednesday', incomplete_by_day)
        self.assertEqual(incomplete_by_day['Tuesday'].needed, 2)  # 2 players, need 2 more
        self.assertEqual(incomplete_by_day['Wednesday'].needed, 3)  # 1 player, need 3 more

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

    def test_multi_day_players_auto_fill_pods(self):
        """
        Test that multi-day players automatically fill pods on their available days.
        Players without 'one game only' preference play on all viable days.

        Scenario:
        - Monday: 4 players (n8, chris, patrick, eli)
        - Tuesday: 3 players (patrick, chad, matt) - can't form pod
        - Wednesday: 5 players (patrick, eli, chad, matt, trevor)

        Expected: Monday pod forms, Wednesday pod forms with multi-day players
        auto-filling. Gameless players (chad, matt, trevor) get priority in
        Wednesday pod.
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

        # Should form 2 pods (Monday + Wednesday auto-filled)
        self.assertEqual(len(result.pods), 2,
            f"Should form 2 pods. Got: {result.pods}")

        # Monday pod
        monday_pods = [p for p in result.pods if p.day == 'Monday']
        self.assertEqual(len(monday_pods), 1, "Should have 1 Monday pod")

        # Wednesday pod forms with multi-day players auto-assigned
        wednesday_pods = [p for p in result.pods if p.day == 'Wednesday']
        self.assertEqual(len(wednesday_pods), 1, "Should have 1 Wednesday pod")

        # Gameless players should be prioritized in Wednesday pod
        wed_players = wednesday_pods[0].players
        self.assertIn('chad', wed_players, "Chad (gameless) should be in Wednesday pod")
        self.assertIn('matt', wed_players, "Matt (gameless) should be in Wednesday pod")
        self.assertIn('trevor', wed_players, "Trevor (gameless) should be in Wednesday pod")

        # All 7 players should have games
        self.assertEqual(len(result.players_with_games), 7,
            f"All 7 players should have games, got {len(result.players_with_games)}")
        self.assertEqual(len(result.players_without_games), 0,
            "No players without games")

        # No choice scenario needed (pods form automatically)
        self.assertIsNone(result.choice_required,
            "No choice scenario needed - pods form automatically")


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


    def test_earlier_day_preferred_as_tiebreaker(self):
        """
        When two days are equally viable (same priority), prefer the earlier
        day so players get their game sooner in the week.

        Scenario:
        - Monday: A, B, C, D (4 players)
        - Wednesday: E, F, G, H (4 players)
        Both days are "complete" with 4 players each. Monday should process
        first because it's earlier in the week.
        """
        availability = {
            'A': ['Monday'],
            'B': ['Monday'],
            'C': ['Monday'],
            'D': ['Monday'],
            'E': ['Wednesday'],
            'F': ['Wednesday'],
            'G': ['Wednesday'],
            'H': ['Wednesday'],
        }

        result = optimize_pods(availability)

        # Both pods should form
        self.assertEqual(len(result.pods), 2)

        # Check that Monday pod is listed first (processed first)
        self.assertEqual(result.pods[0].day, 'Monday',
            "Monday should be processed first as it's earlier in the week")
        self.assertEqual(result.pods[1].day, 'Wednesday')

    def test_flexible_player_fills_both_days(self):
        """
        A flexible player without 'one game only' preference plays on all
        their available days, enabling pods that would otherwise fail.

        Scenario:
        - Monday: A, B, C + Flex (4 with Flex)
        - Wednesday: D, E, F + Flex (4 with Flex)
        Flex plays both days since no preference limits them.
        """
        availability = {
            'Flex': ['Monday', 'Wednesday'],
            'A': ['Monday'],
            'B': ['Monday'],
            'C': ['Monday'],
            'D': ['Wednesday'],
            'E': ['Wednesday'],
            'F': ['Wednesday'],
        }

        result = optimize_pods(availability)

        # Both pods form (Flex plays twice)
        self.assertEqual(len(result.pods), 2,
            f"Both pods should form. Got: {result.pods}")

        # Monday pod with Flex
        monday_pods = [p for p in result.pods if p.day == 'Monday']
        self.assertEqual(len(monday_pods), 1)
        self.assertIn('Flex', monday_pods[0].players)

        # Wednesday pod with Flex
        wednesday_pods = [p for p in result.pods if p.day == 'Wednesday']
        self.assertEqual(len(wednesday_pods), 1)
        self.assertIn('Flex', wednesday_pods[0].players)

        # All 7 players have games
        self.assertEqual(len(result.players_with_games), 7)
        self.assertEqual(len(result.players_without_games), 0)

    def test_multi_day_players_fill_all_viable_days(self):
        """
        Multi-day players fill pods on all their available days.

        Scenario:
        - Monday: Patrick, N8, Eli, M@ (4 players, complete pod)
        - Tuesday: Patrick, Chad, Eli, M@ (4 players, 3 overlap with Monday)
        - Wednesday: Patrick, Zaq, Trevor, Chad, Eli, M@, John (7 players)

        With multi-day play enabled, Patrick/Eli/M@ play Monday AND Tuesday,
        Chad fills Tuesday, and Wednesday forms with gameless players prioritized.

        Expected: 3 pods (Monday + Tuesday + Wednesday), all 8 players get games.
        """
        availability = {
            'Patrick': ['Monday', 'Tuesday', 'Wednesday'],
            'N8': ['Monday'],
            'Eli': ['Monday', 'Tuesday', 'Wednesday'],
            'M@': ['Monday', 'Tuesday', 'Wednesday'],
            'Chad': ['Tuesday', 'Wednesday'],
            'Zaq': ['Wednesday'],
            'Trevor': ['Wednesday'],
            'John': ['Wednesday'],
        }

        result = optimize_pods(availability)

        # Should form 3 pods (multi-day players fill all viable days)
        self.assertEqual(len(result.pods), 3,
            f"Should form 3 pods, got {len(result.pods)}. Pods: {result.pods}")

        # Monday pod
        monday_pods = [p for p in result.pods if p.day == 'Monday']
        self.assertEqual(len(monday_pods), 1, "Should have 1 Monday pod")
        self.assertIn('N8', monday_pods[0].players)

        # Tuesday pod (multi-day players + Chad)
        tuesday_pods = [p for p in result.pods if p.day == 'Tuesday']
        self.assertEqual(len(tuesday_pods), 1, "Should have 1 Tuesday pod")
        self.assertIn('Chad', tuesday_pods[0].players,
            "Chad (gameless) should be prioritized in Tuesday pod")

        # Wednesday pod (gameless players prioritized)
        wednesday_pods = [p for p in result.pods if p.day == 'Wednesday']
        self.assertEqual(len(wednesday_pods), 1, "Should have 1 Wednesday pod")
        self.assertIn('Zaq', wednesday_pods[0].players)
        self.assertIn('Trevor', wednesday_pods[0].players)
        self.assertIn('John', wednesday_pods[0].players)

        # All 8 players should have games
        self.assertEqual(len(result.players_with_games), 8,
            f"8 players should have games, got {len(result.players_with_games)}")

        # No players without games
        self.assertEqual(len(result.players_without_games), 0,
            f"No players should be without games, got: {result.players_without_games}")


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
            players_without_games={'alice', 'bob'},
            incomplete_pods=[IncompletePod(day='Monday', players=['alice', 'bob'], needed=2)]
        )

        formatted = format_pod_results(result)

        self.assertIn('No pods could be formed', formatted)
        self.assertIn('Almost made it', formatted)
        self.assertIn('Monday', formatted)
        self.assertIn('need 2 more', formatted)

    def test_format_with_leftover_players(self):
        """Test formatting with players who didn't get games."""
        result = OptimizationResult(
            pods=[PodAssignment(day='Monday', players=['p1', 'p2', 'p3', 'p4'])],
            players_with_games={'p1', 'p2', 'p3', 'p4'},
            players_without_games={'p5'},
            incomplete_pods=[IncompletePod(day='Tuesday', players=['p5'], needed=3)]
        )

        formatted = format_pod_results(result)

        self.assertIn('Almost made it', formatted)
        self.assertIn('Tuesday', formatted)
        self.assertIn('p5', formatted)
        self.assertIn('need 3 more', formatted)

    def test_format_incomplete_with_volunteers(self):
        """Test formatting incomplete pods that show eligible volunteers."""
        result = OptimizationResult(
            pods=[PodAssignment(day='Wednesday', players=['justin', 'chad', 'zach', 'trevor'])],
            players_with_games={'justin', 'chad', 'zach', 'trevor'},
            players_without_games={'kyle', 'eli'},
            incomplete_pods=[
                IncompletePod(day='Monday', players=['kyle', 'eli'], needed=1, eligible_volunteers=['justin']),
                IncompletePod(day='Thursday', players=['eli'], needed=1, eligible_volunteers=['zach']),
            ]
        )

        formatted = format_pod_results(result)

        self.assertIn('Almost made it', formatted)
        self.assertIn('Could play', formatted)
        self.assertIn('justin', formatted)
        self.assertIn('zach', formatted)

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


class TestPlayerPreferences(unittest.TestCase):
    """Test cases for player preference handling."""

    def test_one_game_only_respected(self):
        """Player with 'one game only' preference is assigned to only one pod."""
        availability = {
            'alice': ['Monday', 'Wednesday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
            'eve': ['Wednesday'],
            'frank': ['Wednesday'],
            'grace': ['Wednesday'],
        }
        preferences = {
            'alice': {PREF_ONE_GAME_ONLY}
        }

        result = optimize_pods(availability, preferences)

        # Alice should only be in one pod
        alice_pods = [pod for pod in result.pods if 'alice' in pod.players]
        self.assertEqual(len(alice_pods), 1,
            "Alice should only be in one pod due to 'one game only' preference")

    def test_no_consecutive_nights_respected(self):
        """Player with 'no consecutive' preference doesn't get Mon+Tue."""
        availability = {
            'alice': ['Monday', 'Tuesday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
            'eve': ['Tuesday'],
            'frank': ['Tuesday'],
            'grace': ['Tuesday'],
        }
        preferences = {
            'alice': {PREF_NO_CONSECUTIVE}
        }

        result = optimize_pods(availability, preferences)

        # Alice should only be in one pod (Mon and Tue are consecutive)
        alice_pods = [pod for pod in result.pods if 'alice' in pod.players]
        self.assertLessEqual(len(alice_pods), 1,
            "Alice should not be in both Monday and Tuesday pods (consecutive)")

    def test_no_consecutive_allows_non_adjacent(self):
        """Player with 'no consecutive' CAN get Mon+Wed (not adjacent)."""
        availability = {
            'alice': ['Monday', 'Wednesday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
            'eve': ['Wednesday'],
            'frank': ['Wednesday'],
            'grace': ['Wednesday'],
        }
        preferences = {
            'alice': {PREF_NO_CONSECUTIVE}
        }

        result = optimize_pods(availability, preferences)

        # Alice can be in both Monday and Wednesday pods (not consecutive)
        # This depends on the algorithm choosing to use Alice on both days
        # At minimum, Alice should be in at least one pod
        alice_pods = [pod for pod in result.pods if 'alice' in pod.players]
        self.assertGreaterEqual(len(alice_pods), 1,
            "Alice should be in at least one pod")

    def test_combined_preferences(self):
        """Both preferences honored together."""
        availability = {
            'alice': ['Monday', 'Tuesday', 'Wednesday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
            'eve': ['Tuesday'],
            'frank': ['Tuesday'],
            'grace': ['Tuesday'],
            'henry': ['Wednesday'],
            'iris': ['Wednesday'],
            'jack': ['Wednesday'],
        }
        preferences = {
            'alice': {PREF_ONE_GAME_ONLY, PREF_NO_CONSECUTIVE}
        }

        result = optimize_pods(availability, preferences)

        # Alice should only be in one pod (one game only takes precedence)
        alice_pods = [pod for pod in result.pods if 'alice' in pod.players]
        self.assertEqual(len(alice_pods), 1,
            "Alice should only be in one pod due to 'one game only' preference")

    def test_preference_prevents_critical_double(self):
        """Critical player with 'one game' stays in one pod only."""
        # Alice is critical for both Monday and Wednesday, but has "one game only"
        availability = {
            'alice': ['Monday', 'Wednesday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
            'eve': ['Wednesday'],
            'frank': ['Wednesday'],
            'grace': ['Wednesday'],
        }
        preferences = {
            'alice': {PREF_ONE_GAME_ONLY}
        }

        result = optimize_pods(availability, preferences)

        # Alice should only be in one pod, even if critical for both
        alice_pods = [pod for pod in result.pods if 'alice' in pod.players]
        self.assertEqual(len(alice_pods), 1,
            "Alice should stay in one pod despite being critical")

    def test_one_game_excluded_from_double_play(self):
        """'One game' players are NOT in flexible_candidates for double-play."""
        availability = {
            # Monday has 4 players - will form a pod
            'alice': ['Monday', 'Wednesday'],  # Flexible but wants one game only
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
            # Wednesday has only 3 players - needs 1 more
            'eve': ['Wednesday'],
            'frank': ['Wednesday'],
            'grace': ['Wednesday'],
        }
        preferences = {
            'alice': {PREF_ONE_GAME_ONLY}
        }

        result = optimize_pods(availability, preferences)

        # If there's a double-play opportunity, Alice should NOT be a candidate
        if result.choice_required and result.choice_required.get('scenario') == 'double_play_needed':
            self.assertNotIn('alice', result.choice_required.get('flexible_candidates', []),
                "Alice should not be a double-play candidate due to 'one game only'")

    def test_backward_compatible_no_preferences(self):
        """Works when preferences parameter is omitted."""
        availability = {
            'alice': ['Monday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
        }

        # Call without preferences parameter
        result = optimize_pods(availability)

        self.assertEqual(len(result.pods), 1)
        self.assertEqual(len(result.players_with_games), 4)

    def test_empty_preferences_dict(self):
        """Empty dict behaves same as None."""
        availability = {
            'alice': ['Monday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
        }

        result = optimize_pods(availability, {})

        self.assertEqual(len(result.pods), 1)
        self.assertEqual(len(result.players_with_games), 4)

    def test_sunday_monday_consecutive(self):
        """Sunday and Monday are treated as consecutive (week wraps)."""
        availability = {
            'alice': ['Sunday', 'Monday'],
            'bob': ['Sunday'],
            'charlie': ['Sunday'],
            'dave': ['Sunday'],
            'eve': ['Monday'],
            'frank': ['Monday'],
            'grace': ['Monday'],
        }
        preferences = {
            'alice': {PREF_NO_CONSECUTIVE}
        }

        result = optimize_pods(availability, preferences)

        # Alice should only be in one pod (Sun and Mon are consecutive)
        alice_pods = [pod for pod in result.pods if 'alice' in pod.players]
        self.assertLessEqual(len(alice_pods), 1,
            "Alice should not be in both Sunday and Monday pods (consecutive wrap)")

    def test_all_players_one_game_only(self):
        """Maximize unique players when everyone wants one game."""
        availability = {
            'alice': ['Monday', 'Tuesday'],
            'bob': ['Monday', 'Tuesday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
            'eve': ['Tuesday'],
            'frank': ['Tuesday'],
        }
        preferences = {
            'alice': {PREF_ONE_GAME_ONLY},
            'bob': {PREF_ONE_GAME_ONLY},
        }

        result = optimize_pods(availability, preferences)

        # Alice and Bob should each be in at most one pod
        alice_pods = [pod for pod in result.pods if 'alice' in pod.players]
        bob_pods = [pod for pod in result.pods if 'bob' in pod.players]

        self.assertLessEqual(len(alice_pods), 1)
        self.assertLessEqual(len(bob_pods), 1)

    def test_can_assign_to_day_helper(self):
        """Test the _can_assign_to_day helper function directly."""
        # Test one game only
        player_assigned_days = {'alice': ['Monday']}
        preferences = {'alice': {PREF_ONE_GAME_ONLY}}

        # Alice already has a game, can't assign to Tuesday
        self.assertFalse(_can_assign_to_day('alice', 'Tuesday', player_assigned_days, preferences))

        # Bob has no assignments and no prefs - can assign
        self.assertTrue(_can_assign_to_day('bob', 'Tuesday', {}, {}))

        # Test no consecutive
        player_assigned_days = {'charlie': ['Monday']}
        preferences = {'charlie': {PREF_NO_CONSECUTIVE}}

        # Charlie on Monday, can't do Tuesday (consecutive)
        self.assertFalse(_can_assign_to_day('charlie', 'Tuesday', player_assigned_days, preferences))

        # Charlie on Monday, CAN do Wednesday (not consecutive)
        self.assertTrue(_can_assign_to_day('charlie', 'Wednesday', player_assigned_days, preferences))

    def test_no_consecutive_wednesday_thursday(self):
        """Verify Wednesday-Thursday are treated as consecutive."""
        availability = {
            'alice': ['Wednesday', 'Thursday'],
            'bob': ['Wednesday'],
            'charlie': ['Wednesday'],
            'dave': ['Wednesday'],
            'eve': ['Thursday'],
            'frank': ['Thursday'],
            'grace': ['Thursday'],
        }
        preferences = {
            'alice': {PREF_NO_CONSECUTIVE}
        }

        result = optimize_pods(availability, preferences)

        # Alice should only be in one pod
        alice_pods = [pod for pod in result.pods if 'alice' in pod.players]
        self.assertLessEqual(len(alice_pods), 1,
            "Alice should not be in both Wednesday and Thursday pods")


if __name__ == '__main__':
    unittest.main()
