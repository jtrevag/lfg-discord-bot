"""
Unit tests for cEDH pod labeling in pod_optimizer.py.

Covers:
- Base case: no cedh_players → all casual
- All-cEDH pod → "cEDH league" label
- Mixed pod (< 4 cEDH) → "casual" label
- Priority grouping: cEDH players packed into their own pod first
- Overflow: 5 cEDH + 3 casual → one cEDH pod + one casual pod
- Insufficient cEDH to fill a pod → all casual
- Two full cEDH pods
- format_pod_results includes game type labels
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from lfg_bot.utils.pod_optimizer import (
    optimize_pods,
    format_pod_results,
    PodAssignment,
)


class TestCedhPodLabeling(unittest.TestCase):

    # ------------------------------------------------------------------
    # Base cases
    # ------------------------------------------------------------------

    def test_no_cedh_players_arg_defaults_to_casual(self):
        """When cedh_players is not provided, all pods are casual."""
        availability = {
            'p1': ['Monday'], 'p2': ['Monday'],
            'p3': ['Monday'], 'p4': ['Monday'],
        }
        result = optimize_pods(availability)
        self.assertEqual(len(result.pods), 1)
        self.assertEqual(result.pods[0].game_type, 'casual')

    def test_empty_cedh_set_defaults_to_casual(self):
        """When cedh_players is an empty set, all pods are casual."""
        availability = {
            'p1': ['Monday'], 'p2': ['Monday'],
            'p3': ['Monday'], 'p4': ['Monday'],
        }
        result = optimize_pods(availability, cedh_players=set())
        self.assertEqual(len(result.pods), 1)
        self.assertEqual(result.pods[0].game_type, 'casual')

    # ------------------------------------------------------------------
    # All-cEDH pod
    # ------------------------------------------------------------------

    def test_all_four_cedh_players_labeled_cedh_league(self):
        """Four cEDH players on the same day → cEDH league pod."""
        availability = {
            'p1': ['Monday'], 'p2': ['Monday'],
            'p3': ['Monday'], 'p4': ['Monday'],
        }
        cedh = {'p1', 'p2', 'p3', 'p4'}
        result = optimize_pods(availability, cedh_players=cedh)
        self.assertEqual(len(result.pods), 1)
        self.assertEqual(result.pods[0].game_type, 'cEDH league')

    # ------------------------------------------------------------------
    # Mixed pod (< 4 cEDH → casual)
    # ------------------------------------------------------------------

    def test_three_cedh_one_casual_is_casual(self):
        """3 cEDH + 1 casual in a pod → casual."""
        availability = {
            'c1': ['Monday'], 'c2': ['Monday'], 'c3': ['Monday'],
            'casual1': ['Monday'],
        }
        cedh = {'c1', 'c2', 'c3'}
        result = optimize_pods(availability, cedh_players=cedh)
        self.assertEqual(len(result.pods), 1)
        self.assertEqual(result.pods[0].game_type, 'casual')

    def test_two_cedh_two_casual_is_casual(self):
        """2 cEDH + 2 casual in a pod → casual."""
        availability = {
            'c1': ['Monday'], 'c2': ['Monday'],
            'casual1': ['Monday'], 'casual2': ['Monday'],
        }
        cedh = {'c1', 'c2'}
        result = optimize_pods(availability, cedh_players=cedh)
        self.assertEqual(len(result.pods), 1)
        self.assertEqual(result.pods[0].game_type, 'casual')

    # ------------------------------------------------------------------
    # Priority grouping
    # ------------------------------------------------------------------

    def test_four_cedh_four_casual_same_day_forms_one_cedh_one_casual(self):
        """4 cEDH + 4 casual on same day → one cEDH pod and one casual pod."""
        availability = {
            'c1': ['Monday'], 'c2': ['Monday'], 'c3': ['Monday'], 'c4': ['Monday'],
            'casual1': ['Monday'], 'casual2': ['Monday'],
            'casual3': ['Monday'], 'casual4': ['Monday'],
        }
        cedh = {'c1', 'c2', 'c3', 'c4'}
        result = optimize_pods(availability, cedh_players=cedh)
        self.assertEqual(len(result.pods), 2)
        game_types = {pod.game_type for pod in result.pods}
        self.assertIn('cEDH league', game_types)
        self.assertIn('casual', game_types)

        cedh_pod = next(p for p in result.pods if p.game_type == 'cEDH league')
        self.assertEqual(set(cedh_pod.players), cedh)

    def test_five_cedh_three_casual_forms_one_cedh_one_casual(self):
        """5 cEDH + 3 casual → one cEDH pod (4 cEDH) + one casual pod (1 cEDH + 3 casual)."""
        availability = {
            'c1': ['Monday'], 'c2': ['Monday'], 'c3': ['Monday'],
            'c4': ['Monday'], 'c5': ['Monday'],
            'casual1': ['Monday'], 'casual2': ['Monday'], 'casual3': ['Monday'],
        }
        cedh = {'c1', 'c2', 'c3', 'c4', 'c5'}
        result = optimize_pods(availability, cedh_players=cedh)
        self.assertEqual(len(result.pods), 2)

        cedh_pods = [p for p in result.pods if p.game_type == 'cEDH league']
        casual_pods = [p for p in result.pods if p.game_type == 'casual']
        self.assertEqual(len(cedh_pods), 1)
        self.assertEqual(len(casual_pods), 1)

        # The cEDH pod must be exactly 4 cEDH players
        self.assertEqual(len(cedh_pods[0].players), 4)
        self.assertTrue(all(p in cedh for p in cedh_pods[0].players))

    def test_insufficient_cedh_to_fill_pod_all_casual(self):
        """Only 2 cEDH players among 8 total → neither pod is cEDH league."""
        availability = {
            'c1': ['Monday'], 'c2': ['Monday'],
            'casual1': ['Monday'], 'casual2': ['Monday'],
            'casual3': ['Monday'], 'casual4': ['Monday'],
            'casual5': ['Monday'], 'casual6': ['Monday'],
        }
        cedh = {'c1', 'c2'}
        result = optimize_pods(availability, cedh_players=cedh)
        self.assertEqual(len(result.pods), 2)
        for pod in result.pods:
            self.assertEqual(pod.game_type, 'casual')

    # ------------------------------------------------------------------
    # Two cEDH pods
    # ------------------------------------------------------------------

    def test_eight_cedh_players_forms_two_cedh_pods(self):
        """8 cEDH players → 2 cEDH league pods."""
        availability = {p: ['Monday'] for p in ['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8']}
        cedh = set(availability.keys())
        result = optimize_pods(availability, cedh_players=cedh)
        self.assertEqual(len(result.pods), 2)
        for pod in result.pods:
            self.assertEqual(pod.game_type, 'cEDH league')

    # ------------------------------------------------------------------
    # Multi-day: cEDH grouping works per-day
    # ------------------------------------------------------------------

    def test_cedh_pod_on_one_day_casual_on_another(self):
        """cEDH players on Monday (all cEDH), casual players on Wednesday."""
        availability = {
            'c1': ['Monday'], 'c2': ['Monday'], 'c3': ['Monday'], 'c4': ['Monday'],
            'casual1': ['Wednesday'], 'casual2': ['Wednesday'],
            'casual3': ['Wednesday'], 'casual4': ['Wednesday'],
        }
        cedh = {'c1', 'c2', 'c3', 'c4'}
        result = optimize_pods(availability, cedh_players=cedh)
        self.assertEqual(len(result.pods), 2)

        monday_pod = next(p for p in result.pods if p.day == 'Monday')
        wednesday_pod = next(p for p in result.pods if p.day == 'Wednesday')
        self.assertEqual(monday_pod.game_type, 'cEDH league')
        self.assertEqual(wednesday_pod.game_type, 'casual')

    # ------------------------------------------------------------------
    # format_pod_results includes game type
    # ------------------------------------------------------------------

    def test_format_pod_results_shows_cedh_label(self):
        """format_pod_results includes 'cEDH league' in output for cEDH pods."""
        availability = {
            'p1': ['Monday'], 'p2': ['Monday'],
            'p3': ['Monday'], 'p4': ['Monday'],
        }
        cedh = {'p1', 'p2', 'p3', 'p4'}
        result = optimize_pods(availability, cedh_players=cedh)
        output = format_pod_results(result)
        self.assertIn('cEDH league', output)

    def test_format_pod_results_shows_casual_label(self):
        """format_pod_results includes 'casual' in output for casual pods."""
        availability = {
            'p1': ['Monday'], 'p2': ['Monday'],
            'p3': ['Monday'], 'p4': ['Monday'],
        }
        result = optimize_pods(availability)
        output = format_pod_results(result)
        self.assertIn('casual', output)

    def test_format_pod_results_mixed_labels(self):
        """format_pod_results shows both labels when both pod types exist."""
        availability = {
            'c1': ['Monday'], 'c2': ['Monday'], 'c3': ['Monday'], 'c4': ['Monday'],
            'casual1': ['Monday'], 'casual2': ['Monday'],
            'casual3': ['Monday'], 'casual4': ['Monday'],
        }
        cedh = {'c1', 'c2', 'c3', 'c4'}
        result = optimize_pods(availability, cedh_players=cedh)
        output = format_pod_results(result)
        self.assertIn('cEDH league', output)
        self.assertIn('casual', output)


if __name__ == '__main__':
    unittest.main()
