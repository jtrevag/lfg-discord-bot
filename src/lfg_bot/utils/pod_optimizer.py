"""
Pod optimization algorithm for Commander games.
Maximizes the number of players who get to play at least once across the week.
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from itertools import combinations


# Preference constants
PREF_ONE_GAME_ONLY = "one_game_only"
PREF_NO_CONSECUTIVE = "no_consecutive"

# Day adjacency map (includes Sunday-Monday wrap)
ADJACENT_DAYS = {
    'Monday': ['Sunday', 'Tuesday'],
    'Tuesday': ['Monday', 'Wednesday'],
    'Wednesday': ['Tuesday', 'Thursday'],
    'Thursday': ['Wednesday', 'Friday'],
    'Friday': ['Thursday', 'Saturday'],
    'Saturday': ['Friday', 'Sunday'],
    'Sunday': ['Saturday', 'Monday'],
}


@dataclass
class PodAssignment:
    """Represents a pod assignment for a specific day."""
    day: str
    players: List[str]

    def __repr__(self):
        return f"{self.day}: {', '.join(self.players)}"


@dataclass
class OptimizationResult:
    """Result of pod optimization."""
    pods: List[PodAssignment]
    players_with_games: Set[str]
    players_without_games: Set[str]
    choice_required: Optional[Dict] = None  # For cases where player must choose


def _can_assign_to_day(
    player: str,
    day: str,
    player_assigned_days: Dict[str, List[str]],
    preferences: Dict[str, Set[str]]
) -> bool:
    """
    Check if assigning a player to a day respects their preferences.

    Args:
        player: Player ID
        day: Day to potentially assign
        player_assigned_days: Dict mapping player_id -> list of days already assigned
        preferences: Dict mapping player_id -> set of preference flags

    Returns:
        True if assignment is allowed, False if it violates preferences
    """
    player_prefs = preferences.get(player, set())
    assigned_days = player_assigned_days.get(player, [])

    # Check "one game only" preference
    if PREF_ONE_GAME_ONLY in player_prefs:
        if len(assigned_days) >= 1:
            return False

    # Check "no consecutive nights" preference
    if PREF_NO_CONSECUTIVE in player_prefs:
        adjacent = ADJACENT_DAYS.get(day, [])
        for assigned_day in assigned_days:
            if assigned_day in adjacent:
                return False

    return True


def optimize_pods(
    availability: Dict[str, List[str]],
    preferences: Dict[str, Set[str]] = None
) -> OptimizationResult:
    """
    Optimize pod creation to maximize players who play at least once.

    Args:
        availability: Dict mapping player_id -> list of available days
        preferences: Dict mapping player_id -> set of preference flags
                    (e.g., PREF_ONE_GAME_ONLY, PREF_NO_CONSECUTIVE)

    Returns:
        OptimizationResult with pod assignments and statistics
    """
    # Default to empty preferences if not provided
    if preferences is None:
        preferences = {}

    # Invert the mapping: day -> list of available players
    day_to_players: Dict[str, List[str]] = {}
    all_players = set(availability.keys())

    for player, days in availability.items():
        for day in days:
            if day not in day_to_players:
                day_to_players[day] = []
            day_to_players[day].append(player)

    # Try to find optimal pod assignments
    best_result = _find_best_assignment(day_to_players, all_players, availability, preferences)

    # Check for scenarios where a multi-day player enables multiple pods
    choice_scenario = _detect_choice_scenario(availability, day_to_players, best_result)

    if choice_scenario:
        best_result.choice_required = choice_scenario

    return best_result


def _count_unique_players(day: str, day_to_players: Dict[str, List[str]], availability: Dict[str, List[str]]) -> int:
    """
    Count players who are available ONLY on this day (not flexible).
    These players are "trapped" on this day and should be prioritized.
    """
    players_on_day = day_to_players.get(day, [])
    unique_count = sum(1 for player in players_on_day if len(availability[player]) == 1)
    return unique_count


def _detect_critical_flexible_players(
    day_to_players: Dict[str, List[str]],
    availability: Dict[str, List[str]]
) -> Dict[str, str]:
    """
    Detect flexible players who are critical for a specific day.

    A flexible player (available 2+ days) is "critical" for Day A if:
    - Day A would have < 4 players without them
    - At least one other day they're available on would still have >= 4 players without them
    - Reserving them wouldn't reduce the number of complete pods on their other days

    Returns:
        Dict mapping player_id -> day they must be assigned to
    """
    critical_assignments = {}

    # Find all flexible players (available on 2+ days)
    flexible_players = {
        player: days
        for player, days in availability.items()
        if len(days) >= 2
    }

    # Track how many players we're reserving away from each day
    reserved_from_day: Dict[str, int] = {}

    for player, player_days in flexible_players.items():
        # Count how many players each day would have WITHOUT this player
        days_remaining = {}
        for day in player_days:
            players_on_day = day_to_players.get(day, [])
            remaining_count = len([p for p in players_on_day if p != player])
            days_remaining[day] = remaining_count

        # Check if player is critical for exactly one day
        days_needing_player = [day for day, count in days_remaining.items() if count < 4]
        days_not_needing_player = [day for day, count in days_remaining.items() if count >= 4]

        # If player is critical for one day but not others, consider assigning them there
        if len(days_needing_player) == 1 and len(days_not_needing_player) >= 1:
            critical_day = days_needing_player[0]

            # Check if reserving this player would reduce complete pods on other days
            can_reserve = True
            for other_day in days_not_needing_player:
                total_on_day = len(day_to_players.get(other_day, []))
                already_reserved = reserved_from_day.get(other_day, 0)
                effective_count = total_on_day - already_reserved

                # Current pods possible vs pods after reserving this player
                current_pods = effective_count // 4
                new_pods = (effective_count - 1) // 4

                # Don't reserve if it would reduce the number of complete pods
                if new_pods < current_pods:
                    can_reserve = False
                    break

            if can_reserve:
                critical_assignments[player] = critical_day
                # Track that we're reserving this player away from their other days
                for other_day in days_not_needing_player:
                    reserved_from_day[other_day] = reserved_from_day.get(other_day, 0) + 1

    return critical_assignments


def _find_best_assignment(
    day_to_players: Dict[str, List[str]],
    all_players: Set[str],
    availability: Dict[str, List[str]] = None,
    preferences: Dict[str, Set[str]] = None
) -> OptimizationResult:
    """
    Find the best pod assignment using enhanced greedy approach.

    Strategy:
    1. Detect critical flexible players (must be assigned to specific day)
    2. Pre-assign critical players to their required days
    3. Prioritize "complete" days (exactly 4, 8, 12... players) first
    4. Form pods greedily on sorted days
    5. Allow flexible players to play twice if it enables additional pods
    6. Respect player preferences (one game only, no consecutive nights)
    """
    pods = []
    assigned_players = set()
    player_assigned_days: Dict[str, List[str]] = {}  # Track which days each player is assigned to

    # Default to empty preferences if not provided
    if preferences is None:
        preferences = {}

    # If availability not provided, reconstruct it (for backwards compatibility)
    if availability is None:
        availability = {}
        for day, players in day_to_players.items():
            for player in players:
                if player not in availability:
                    availability[player] = []
                availability[player].append(day)

    # STEP 1: Detect and pre-assign critical flexible players
    critical_assignments = _detect_critical_flexible_players(day_to_players, availability)

    # Group critical players by their required day
    critical_by_day: Dict[str, List[str]] = {}
    for player, day in critical_assignments.items():
        if day not in critical_by_day:
            critical_by_day[day] = []
        critical_by_day[day].append(player)

    # Mark critical players as reserved (can't be used on other days)
    reserved_players = set(critical_assignments.keys())

    # STEP 2: Sort days prioritizing complete pods
    # Sort by:
    # 1. Whether day has exact multiple of 4 players (complete pods)
    # 2. Unique player count (players only available that day)
    # 3. Total player count
    # 4. Earlier in the week (tiebreaker - players prefer games sooner)
    day_order = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
                 'Friday': 4, 'Saturday': 5, 'Sunday': 6}

    def day_priority(day_info):
        day, players = day_info
        player_count = len(players)
        unique_count = _count_unique_players(day, day_to_players, availability)
        is_complete = (player_count % 4 == 0 and player_count > 0)
        # Negate day_order so earlier days sort higher (since we sort descending)
        earlier_in_week = -day_order.get(day, 99)
        return (is_complete, unique_count, player_count, earlier_in_week)

    sorted_days = sorted(
        day_to_players.items(),
        key=day_priority,
        reverse=True
    )

    # STEP 3: Form pods with critical players pre-assigned to their required days
    for day, available in sorted_days:
        # Start with critical players for this day (if any)
        critical_for_day = critical_by_day.get(day, [])

        # Get players available on this day who:
        # - Are not yet assigned OR can play multiple times based on preferences
        # - Are not reserved for another day (unless critical for this day)
        # - Can be assigned to this day per their preferences
        def is_eligible(p):
            # Already assigned and preferences block this day
            if p in assigned_players:
                return False
            # Reserved for another day (unless critical for this day)
            if p in reserved_players and p not in critical_for_day:
                return False
            # Preferences would be violated (check consecutive nights for first assignment)
            if not _can_assign_to_day(p, day, player_assigned_days, preferences):
                return False
            return True

        unassigned_available = [p for p in available if is_eligible(p)]

        # Form pods while we have enough players
        while len(unassigned_available) >= 4:
            pod_players = unassigned_available[:4]
            pods.append(PodAssignment(day=day, players=pod_players))

            for player in pod_players:
                assigned_players.add(player)
                # Track which day(s) each player is assigned to
                if player not in player_assigned_days:
                    player_assigned_days[player] = []
                player_assigned_days[player].append(day)
                if player in reserved_players:
                    reserved_players.remove(player)  # No longer reserved once assigned

            # Recalculate available players
            unassigned_available = [p for p in available if is_eligible(p)]

        # After processing this day, release reserved players whose target days
        # can no longer form a pod (because other players were assigned)
        players_to_release = []
        for reserved_player in reserved_players:
            required_day = critical_assignments.get(reserved_player)
            if required_day:
                # Count available unassigned players for that day
                available_on_required_day = [
                    p for p in day_to_players.get(required_day, [])
                    if p not in assigned_players
                ]
                # If < 4 players available, the day can't form a pod - release this player
                if len(available_on_required_day) < 4:
                    players_to_release.append(reserved_player)

        for player in players_to_release:
            reserved_players.remove(player)

    # STEP 4: Second pass - detect double-play opportunities
    # Check each day to see if we're 1 player short of forming a pod
    double_play_opportunity = None

    for day, available in sorted_days:
        unassigned_available = [p for p in available if p not in assigned_players]

        # If we have 3 unassigned players, check if a flexible player can play twice
        if len(unassigned_available) == 3:
            # Find flexible players who are already assigned but available this day
            # Exclude players with "one game only" preference
            # Exclude players who would violate "no consecutive nights" preference
            flexible_candidates = [
                p for p in available
                if p in assigned_players
                and len(availability.get(p, [])) > 1
                and PREF_ONE_GAME_ONLY not in preferences.get(p, set())
                and _can_assign_to_day(p, day, player_assigned_days, preferences)
            ]

            if flexible_candidates:
                # Create a choice scenario asking which player can volunteer
                double_play_opportunity = {
                    'scenario': 'double_play_needed',
                    'day': day,
                    'waiting_players': unassigned_available,
                    'flexible_candidates': flexible_candidates,
                    'message': (
                        f"**Need 1 more player for {day}!**\n\n"
                        f"Waiting to play: {', '.join([f'<@{p}>' for p in unassigned_available])}\n\n"
                        f"Can any of these players join for a 2nd game?\n"
                        f"{', '.join([f'<@{p}>' for p in flexible_candidates])}\n\n"
                        f"React or reply if you can play twice this week! 🎲"
                    )
                }
                break  # Only show one opportunity at a time

    players_without_games = all_players - assigned_players

    result = OptimizationResult(
        pods=pods,
        players_with_games=assigned_players,
        players_without_games=players_without_games
    )

    # Set choice_required if there's a double-play opportunity
    if double_play_opportunity:
        result.choice_required = double_play_opportunity

    return result


def _detect_choice_scenario(
    availability: Dict[str, List[str]],
    day_to_players: Dict[str, List[str]],
    current_result: OptimizationResult
) -> Optional[Dict]:
    """
    Detect if a player voting for multiple days is critical for forming two pods.

    Returns a dict with choice scenario details if found, None otherwise.
    """
    # Find players who voted for multiple days
    multi_day_players = {
        player: days for player, days in availability.items()
        if len(days) > 1
    }

    for player, days in multi_day_players.items():
        # Check each pair of days this player is available
        for day1, day2 in combinations(days, 2):
            if day1 not in day_to_players or day2 not in day_to_players:
                continue

            players_day1 = day_to_players[day1]
            players_day2 = day_to_players[day2]

            # Check if removing this player from one day prevents a pod
            # while keeping them on both days enables two pods

            # Scenario: day1 has exactly 4 with player, day2 has exactly 4 with player
            if len(players_day1) == 4 and len(players_day2) == 4:
                if player in players_day1 and player in players_day2:
                    # This player is critical for both pods
                    return {
                        "player": player,
                        "scenario": "critical_for_both",
                        "day1": day1,
                        "day2": day2,
                        "pod1": players_day1,
                        "pod2": players_day2,
                        "message": (
                            f"<@{player}> is needed for pods on both {day1} and {day2}. "
                            f"Please choose which day you prefer to play, or if you can attend both!"
                        )
                    }

    return None


def format_pod_results(result: OptimizationResult) -> str:
    """
    Format the optimization result into a human-readable Discord message.
    """
    lines = ["**Pod Assignments for This Week**\n"]

    if result.choice_required:
        scenario_type = result.choice_required.get("scenario", "unknown")

        if scenario_type == "double_play_needed":
            # Show completed pods first
            if result.pods:
                pods_by_day = {}
                for pod in result.pods:
                    if pod.day not in pods_by_day:
                        pods_by_day[pod.day] = []
                    pods_by_day[pod.day].append(pod)

                for day in sorted(pods_by_day.keys()):
                    lines.append(f"**{day}:**")
                    for i, pod in enumerate(pods_by_day[day], 1):
                        player_mentions = ", ".join([f"<@{p}>" for p in pod.players])
                        lines.append(f"  Pod {i}: {player_mentions}")
                    lines.append("")

            # Then show the choice prompt
            lines.append("---")
            lines.append(result.choice_required["message"])
            return "\n".join(lines)

        elif scenario_type == "critical_for_both":
            # Original choice scenario formatting
            lines.append(f"**PLAYER CHOICE REQUIRED**")
            lines.append(result.choice_required["message"])
            lines.append(f"\n**Potential Pods:**")
            lines.append(f"**{result.choice_required['day1']}:** {', '.join([f'<@{p}>' for p in result.choice_required['pod1']])}")
            lines.append(f"**{result.choice_required['day2']}:** {', '.join([f'<@{p}>' for p in result.choice_required['pod2']])}")
            lines.append("\nPlease react or respond with your choice!")
            return "\n".join(lines)

    if not result.pods:
        lines.append("No pods could be formed this week. Need at least 4 players for one day.")
        if result.players_without_games:
            lines.append(f"\n**Players without games:** {', '.join([f'<@{p}>' for p in result.players_without_games])}")
        return "\n".join(lines)

    # Group pods by day
    pods_by_day = {}
    for pod in result.pods:
        if pod.day not in pods_by_day:
            pods_by_day[pod.day] = []
        pods_by_day[pod.day].append(pod)

    for day in sorted(pods_by_day.keys()):
        lines.append(f"**{day}:**")
        for i, pod in enumerate(pods_by_day[day], 1):
            player_mentions = ", ".join([f"<@{p}>" for p in pod.players])
            lines.append(f"  Pod {i}: {player_mentions}")
        lines.append("")

    lines.append(f"**Total players with games:** {len(result.players_with_games)}")

    if result.players_without_games:
        lines.append(f"\n**Players without games this week:** {', '.join([f'<@{p}>' for p in result.players_without_games])}")

    return "\n".join(lines)
