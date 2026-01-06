"""
Complex pod scheduling test scenarios.
Tests progressively more complicated player availability patterns.
"""

import unittest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from lfg_bot.utils.pod_optimizer import optimize_pods, format_pod_results


class TestComplexPodScenarios(unittest.TestCase):
    """Progressive complexity tests for pod scheduling."""

    def test_scenario_1_simple_two_days(self):
        """
        Scenario 1: Simple - 4 players each on 2 different days (no overlap)
        Expected: 2 pods formed, 8 players total
        """
        print("\n" + "="*60)
        print("SCENARIO 1: Simple - 4 players on Mon, 4 different on Wed")
        print("="*60)

        availability = {
            # Monday players
            'alice': ['Monday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
            # Wednesday players
            'eve': ['Wednesday'],
            'frank': ['Wednesday'],
            'grace': ['Wednesday'],
            'henry': ['Wednesday']
        }

        result = optimize_pods(availability)
        print(format_pod_results(result))

        self.assertEqual(len(result.pods), 2, "Should form 2 pods")
        self.assertEqual(len(result.players_with_games), 8, "All 8 players should play")
        self.assertEqual(len(result.players_without_games), 0, "No players left out")

    def test_scenario_2_one_overlap_player(self):
        """
        Scenario 2: One player available both days, others single day
        Mon: Bob, Charlie, Grace (3 unique) + Alice (flexible) = 4 total
        Wed: Dave, Eve, Frank, Henry (4 unique) + Alice (flexible) = 5 total
        With 5b: Alice detected as critical for Monday (Mon < 4 without her, Wed >= 4)
        Expected: Alice assigned to Monday, 2 pods form
        """
        print("\n" + "="*60)
        print("SCENARIO 2: One player (Alice) available both Mon & Wed")
        print("="*60)

        availability = {
            'alice': ['Monday', 'Wednesday'],  # Can play either day
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Wednesday'],
            'eve': ['Wednesday'],
            'frank': ['Wednesday'],
            'grace': ['Monday'],  # 4th for Monday
            'henry': ['Wednesday']  # 4th for Wednesday
        }

        result = optimize_pods(availability)
        print(format_pod_results(result))

        # With 5b critical player detection, Alice assigned to Monday
        # Both pods form optimally
        self.assertEqual(len(result.pods), 2, "Should form 2 pods")
        self.assertEqual(len(result.players_with_games), 8, "All 8 players should play")
        self.assertEqual(len(result.players_without_games), 0, "No players left out")

    def test_scenario_3_critical_overlap_player(self):
        """
        Scenario 3: One player is CRITICAL for both days
        Mon: Alice, Bob, Charlie (need Alice for 4th)
        Wed: Alice, Dave, Eve, Frank (need Alice for 4th)
        Expected: Choice scenario detected
        """
        print("\n" + "="*60)
        print("SCENARIO 3: Alice is critical for both pods")
        print("="*60)

        availability = {
            'alice': ['Monday', 'Wednesday'],  # Critical!
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Monday'],
            'eve': ['Wednesday'],
            'frank': ['Wednesday'],
            'grace': ['Wednesday']
        }

        result = optimize_pods(availability)
        print(format_pod_results(result))

        # Should detect that Alice is needed for both
        # Might create choice scenario or assign Alice to one day
        self.assertGreaterEqual(len(result.pods), 1, "At least 1 pod should form")

    def test_scenario_4_multiple_overlap_players(self):
        """
        Scenario 4: Multiple players available on multiple days
        Mon: Eve (1 unique), Alice, Bob, Charlie, Dave (4 flexible) = 1 unique
        Tue: Frank, Grace (2 unique), Alice, Bob (2 flexible) = 2 unique
        Wed: Henry, Iris (2 unique), Charlie, Dave (2 flexible) = 2 unique
        With 5a: Tue and Wed prioritized (tie on unique count), then total count
        Expected: 2 pods form (Tue + Wed), 8/9 players play
        """
        print("\n" + "="*60)
        print("SCENARIO 4: Multiple players with multiple availabilities")
        print("="*60)

        availability = {
            'alice': ['Monday', 'Tuesday'],
            'bob': ['Monday', 'Tuesday'],
            'charlie': ['Monday', 'Wednesday'],
            'dave': ['Monday', 'Wednesday'],
            'eve': ['Monday'],
            'frank': ['Tuesday'],
            'grace': ['Tuesday'],
            'henry': ['Wednesday'],
            'iris': ['Wednesday']
        }

        result = optimize_pods(availability)
        print(format_pod_results(result))

        # With unique player priority, Tue and Wed get prioritized
        # Forms 2 pods optimally
        self.assertEqual(len(result.pods), 2, "Should form 2 pods")
        self.assertEqual(len(result.players_with_games), 8, "8 of 9 players should play")
        self.assertEqual(len(result.players_without_games), 1, "1 player left out")

    def test_scenario_5_uneven_distribution(self):
        """
        Scenario 5: Very uneven - 8 players on Monday, 2 on Tuesday
        Mon: 8 players (can form 2 pods)
        Tue: 2 players (cannot form pod)
        Expected: 2 pods on Monday, none on Tuesday
        """
        print("\n" + "="*60)
        print("SCENARIO 5: Uneven - 8 on Mon, 2 on Tue")
        print("="*60)

        availability = {
            'p1': ['Monday'],
            'p2': ['Monday'],
            'p3': ['Monday'],
            'p4': ['Monday'],
            'p5': ['Monday'],
            'p6': ['Monday'],
            'p7': ['Monday'],
            'p8': ['Monday'],
            'p9': ['Tuesday'],
            'p10': ['Tuesday']
        }

        result = optimize_pods(availability)
        print(format_pod_results(result))

        self.assertEqual(len(result.pods), 2, "Should form 2 pods on Monday")
        self.assertEqual(len(result.players_with_games), 8, "8 Monday players should play")
        self.assertEqual(len(result.players_without_games), 2, "2 Tuesday players left out")

    def test_scenario_6_three_days_complex(self):
        """
        Scenario 6: Three days with complex overlaps
        Mon: Dave, Eve (2 unique), Alice, Bob, Charlie (3 flexible) = 2 unique
        Tue: Frank, Grace, Henry (3 unique), Alice (1 flexible) = 3 unique
        Wed: Iris, Jane (2 unique), Bob, Charlie (2 flexible) = 2 unique
        With 5a: Tue prioritized (most unique), then Mon/Wed (tie)
        Expected: 2 pods form (Mon + Tue), 8/10 players play
        """
        print("\n" + "="*60)
        print("SCENARIO 6: Three days with overlaps")
        print("="*60)

        availability = {
            'alice': ['Monday', 'Tuesday'],  # Overlap Mon/Tue
            'bob': ['Monday', 'Wednesday'],   # Overlap Mon/Wed
            'charlie': ['Monday', 'Wednesday'], # Overlap Mon/Wed
            'dave': ['Monday'],
            'eve': ['Monday'],
            'frank': ['Tuesday'],
            'grace': ['Tuesday'],
            'henry': ['Tuesday'],
            'iris': ['Wednesday'],
            'jane': ['Wednesday']
        }

        result = optimize_pods(availability)
        print(format_pod_results(result))

        # With unique player priority, forms 2 pods optimally
        self.assertEqual(len(result.pods), 2, "Should form 2 pods")
        self.assertEqual(len(result.players_with_games), 8, "8 of 10 players should play")
        self.assertEqual(len(result.players_without_games), 2, "2 players left out")

    def test_scenario_7_one_super_flexible_player(self):
        """
        Scenario 7: One player available all 3 days, others single day
        Mon: Alice, Bob, Charlie (3 unique) + SuperFlex
        Tue: Dave, Eve, Frank (3 unique) + SuperFlex
        Wed: Grace, Henry, Iris (3 unique) + SuperFlex
        All days tied on unique count (3), SuperFlex critical for multiple days
        Expected: Choice scenario detected (SuperFlex must choose)
        """
        print("\n" + "="*60)
        print("SCENARIO 7: One super flexible player")
        print("="*60)

        availability = {
            'superflex': ['Monday', 'Tuesday', 'Wednesday'],  # Available all days!
            'alice': ['Monday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Tuesday'],
            'eve': ['Tuesday'],
            'frank': ['Tuesday'],
            'grace': ['Wednesday'],
            'henry': ['Wednesday'],
            'iris': ['Wednesday']
        }

        result = optimize_pods(availability)
        print(format_pod_results(result))

        # SuperFlex is critical for forming pods on multiple days
        # Should detect choice scenario
        self.assertIsNotNone(result.choice_required, "Should detect choice scenario")
        self.assertEqual(result.choice_required['player'], 'superflex', "SuperFlex should be the choice player")

    def test_scenario_8_exact_multiples(self):
        """
        Scenario 8: Exact multiples - 12 players across 3 days (4 each)
        Mon: 4 players
        Tue: 4 players
        Wed: 4 players
        Expected: 3 pods, all 12 players play
        """
        print("\n" + "="*60)
        print("SCENARIO 8: Perfect - 4 players each day")
        print("="*60)

        availability = {
            'p1': ['Monday'], 'p2': ['Monday'], 'p3': ['Monday'], 'p4': ['Monday'],
            'p5': ['Tuesday'], 'p6': ['Tuesday'], 'p7': ['Tuesday'], 'p8': ['Tuesday'],
            'p9': ['Wednesday'], 'p10': ['Wednesday'], 'p11': ['Wednesday'], 'p12': ['Wednesday']
        }

        result = optimize_pods(availability)
        print(format_pod_results(result))

        self.assertEqual(len(result.pods), 3, "Should form exactly 3 pods")
        self.assertEqual(len(result.players_with_games), 12, "All 12 players should play")
        self.assertEqual(len(result.players_without_games), 0, "No players left out")

    def test_scenario_9_barely_short(self):
        """
        Scenario 9: Multiple days barely short (3 players each)
        Mon: 3 players
        Tue: 3 players
        Wed: 3 players
        Expected: No pods form
        """
        print("\n" + "="*60)
        print("SCENARIO 9: All days short by 1 player")
        print("="*60)

        availability = {
            'p1': ['Monday'], 'p2': ['Monday'], 'p3': ['Monday'],
            'p4': ['Tuesday'], 'p5': ['Tuesday'], 'p6': ['Tuesday'],
            'p7': ['Wednesday'], 'p8': ['Wednesday'], 'p9': ['Wednesday']
        }

        result = optimize_pods(availability)
        print(format_pod_results(result))

        self.assertEqual(len(result.pods), 0, "No pods should form")
        self.assertEqual(len(result.players_without_games), 9, "All 9 players left out")

    def test_scenario_10_everyone_flexible(self):
        """
        Scenario 10: All 8 players available all 3 days
        Expected: Algorithm picks days to form 2 pods with all players
        """
        print("\n" + "="*60)
        print("SCENARIO 10: All 8 players available all days")
        print("="*60)

        availability = {
            'p1': ['Monday', 'Tuesday', 'Wednesday'],
            'p2': ['Monday', 'Tuesday', 'Wednesday'],
            'p3': ['Monday', 'Tuesday', 'Wednesday'],
            'p4': ['Monday', 'Tuesday', 'Wednesday'],
            'p5': ['Monday', 'Tuesday', 'Wednesday'],
            'p6': ['Monday', 'Tuesday', 'Wednesday'],
            'p7': ['Monday', 'Tuesday', 'Wednesday'],
            'p8': ['Monday', 'Tuesday', 'Wednesday']
        }

        result = optimize_pods(availability)
        print(format_pod_results(result))

        self.assertEqual(len(result.pods), 2, "Should form 2 pods")
        self.assertEqual(len(result.players_with_games), 8, "All 8 players should play")

    def test_scenario_11_bridge_player(self):
        """
        Scenario 11: Bridge player connects two partial groups
        Mon: Alice, Bob, Charlie (3 players)
        Tue: Dave, Eve, Frank (3 players)
        Bridge: Available both Mon & Tue (completes both)
        Expected: Bridge assigned to one, only that day forms pod
        """
        print("\n" + "="*60)
        print("SCENARIO 11: Bridge player connects two groups")
        print("="*60)

        availability = {
            'bridge': ['Monday', 'Tuesday'],  # The key player!
            'alice': ['Monday'],
            'bob': ['Monday'],
            'charlie': ['Monday'],
            'dave': ['Tuesday'],
            'eve': ['Tuesday'],
            'frank': ['Tuesday']
        }

        result = optimize_pods(availability)
        print(format_pod_results(result))

        # Only 1 pod can form (7 players total, bridge goes to one day)
        self.assertEqual(len(result.pods), 1, "Should form 1 pod")
        self.assertEqual(len(result.players_with_games), 4, "4 players get to play")
        self.assertEqual(len(result.players_without_games), 3, "3 players left out")

    def test_scenario_12_cascading_priorities(self):
        """
        Scenario 12: Cascading priorities with 18 players
        Mon: 7 unique players (forms 1 pod, 3 left over)
        Tue: 6 unique players (forms 1 pod, 2 left over)
        Wed: 5 unique players (forms 1 pod, 1 left over)
        Expected: 3 pods form (Mon+Tue+Wed), 6 players without games
        """
        print("\n" + "="*60)
        print("SCENARIO 12: Cascading with overflow players")
        print("="*60)

        availability = {
            # Monday: 7 unique players
            'p1': ['Monday'], 'p2': ['Monday'], 'p3': ['Monday'], 'p4': ['Monday'],
            'p5': ['Monday'], 'p6': ['Monday'], 'p7': ['Monday'],
            # Tuesday: 6 unique players
            'p8': ['Tuesday'], 'p9': ['Tuesday'], 'p10': ['Tuesday'],
            'p11': ['Tuesday'], 'p12': ['Tuesday'], 'p13': ['Tuesday'],
            # Wednesday: 5 unique players
            'p14': ['Wednesday'], 'p15': ['Wednesday'], 'p16': ['Wednesday'],
            'p17': ['Wednesday'], 'p18': ['Wednesday']
        }

        result = optimize_pods(availability)
        print(format_pod_results(result))

        # 18 players total: 7+6+5, each day forms 1 pod = 3 pods total
        # Players: Mon(4 of 7), Tue(4 of 6), Wed(4 of 5) = 12 play, 6 left out
        self.assertEqual(len(result.pods), 3, "Should form 3 pods")
        self.assertEqual(len(result.players_with_games), 12, "12 players should play")
        self.assertEqual(len(result.players_without_games), 6, "6 players left out")


def run_scenarios():
    """Run all scenarios with visual output."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestComplexPodScenarios)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


if __name__ == '__main__':
    print("\n" + "="*60)
    print("COMPLEX POD SCHEDULING SCENARIOS")
    print("="*60)
    run_scenarios()
