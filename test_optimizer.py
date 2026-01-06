"""
Test script for pod optimizer.
Run this to test the optimization algorithm without needing Discord.
"""

from pod_optimizer import optimize_pods, format_pod_results


def test_basic_scenario():
    """Test basic 4-player pod formation."""
    print("=" * 60)
    print("TEST 1: Basic scenario - 4 players on Monday")
    print("=" * 60)

    availability = {
        "123": ["Monday"],      # Alice
        "456": ["Monday"],      # Bob
        "789": ["Monday"],      # Charlie
        "012": ["Monday"],      # Dave
    }

    result = optimize_pods(availability)
    print(format_pod_results(result))
    print()


def test_multiple_days():
    """Test multiple pods across different days."""
    print("=" * 60)
    print("TEST 2: Multiple days - pods on Monday and Wednesday")
    print("=" * 60)

    availability = {
        "123": ["Monday"],
        "456": ["Monday"],
        "789": ["Monday"],
        "012": ["Monday"],
        "345": ["Wednesday"],
        "678": ["Wednesday"],
        "901": ["Wednesday"],
        "234": ["Wednesday"],
    }

    result = optimize_pods(availability)
    print(format_pod_results(result))
    print()


def test_multi_day_player():
    """Test player available multiple days."""
    print("=" * 60)
    print("TEST 3: Player available multiple days")
    print("=" * 60)

    availability = {
        "123": ["Monday", "Wednesday"],  # Alice - multi-day
        "456": ["Monday"],
        "789": ["Monday"],
        "012": ["Monday"],
        "345": ["Wednesday"],
        "678": ["Wednesday"],
        "901": ["Wednesday"],
    }

    result = optimize_pods(availability)
    print(format_pod_results(result))
    print()


def test_choice_scenario():
    """Test scenario where player choice is required."""
    print("=" * 60)
    print("TEST 4: Choice scenario - player needed for both pods")
    print("=" * 60)

    availability = {
        "alice": ["Monday", "Wednesday"],  # Alice critical for both
        "bob": ["Monday"],
        "charlie": ["Monday"],
        "dave": ["Monday"],
        "eve": ["Wednesday"],
        "frank": ["Wednesday"],
        "grace": ["Wednesday"],
    }

    result = optimize_pods(availability)
    print(format_pod_results(result))
    print()


def test_insufficient_players():
    """Test with insufficient players."""
    print("=" * 60)
    print("TEST 5: Insufficient players - only 3 available")
    print("=" * 60)

    availability = {
        "123": ["Monday"],
        "456": ["Monday"],
        "789": ["Monday"],
    }

    result = optimize_pods(availability)
    print(format_pod_results(result))
    print()


def test_partial_pods():
    """Test with 5 players (can only form 1 pod)."""
    print("=" * 60)
    print("TEST 6: Partial pods - 5 players, only 4 get to play")
    print("=" * 60)

    availability = {
        "123": ["Monday"],
        "456": ["Monday"],
        "789": ["Monday"],
        "012": ["Monday"],
        "345": ["Monday"],  # This player won't get a game
    }

    result = optimize_pods(availability)
    print(format_pod_results(result))
    print()


if __name__ == "__main__":
    print("\nPod Optimizer Test Suite")
    print("=" * 60)
    print()

    test_basic_scenario()
    test_multiple_days()
    test_multi_day_player()
    test_choice_scenario()
    test_insufficient_players()
    test_partial_pods()

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)
