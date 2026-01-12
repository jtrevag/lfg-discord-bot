"""
Pod optimization algorithm for Commander games.
Maximizes the number of players who get to play at least once across the week.
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from itertools import combinations


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


def optimize_pods(availability: Dict[str, List[str]]) -> OptimizationResult:
    """
    Optimize pod creation to maximize players who play at least once.

    Args:
        availability: Dict mapping player_id -> list of available days

    Returns:
        OptimizationResult with pod assignments and statistics
    """
    # Invert the mapping: day -> list of available players
    day_to_players: Dict[str, List[str]] = {}
    all_players = set(availability.keys())

    for player, days in availability.items():
        for day in days:
            if day not in day_to_players:
                day_to_players[day] = []
            day_to_players[day].append(player)

    # Try to find optimal pod assignments
    best_result = _find_best_assignment(day_to_players, all_players, availability)

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

        # If player is critical for one day but not others, assign them there
        if len(days_needing_player) == 1 and len(days_not_needing_player) >= 1:
            critical_day = days_needing_player[0]
            critical_assignments[player] = critical_day

    return critical_assignments


def _find_best_assignment(
    day_to_players: Dict[str, List[str]],
    all_players: Set[str],
    availability: Dict[str, List[str]] = None
) -> OptimizationResult:
    """
    Find the best pod assignment using enhanced greedy approach.

    Strategy:
    1. Detect critical flexible players (must be assigned to specific day)
    2. Pre-assign critical players to their required days
    3. Prioritize "complete" days (exactly 4, 8, 12... players) first
    4. Form pods greedily on sorted days
    5. Allow flexible players to play twice if it enables additional pods
    """
    pods = []
    assigned_players = set()

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
    def day_priority(day_info):
        day, players = day_info
        player_count = len(players)
        unique_count = _count_unique_players(day, day_to_players, availability)
        is_complete = (player_count % 4 == 0 and player_count > 0)
        return (is_complete, unique_count, player_count)

    sorted_days = sorted(
        day_to_players.items(),
        key=day_priority,
        reverse=True
    )

    # STEP 3: Form pods with critical players pre-assigned to their required days
    for day, available in sorted_days:
        # Start with critical players for this day (if any)
        critical_for_day = critical_by_day.get(day, [])

        # Get other players available on this day who aren't assigned or reserved elsewhere
        unassigned_available = [
            p for p in available
            if p not in assigned_players and (p not in reserved_players or p in critical_for_day)
        ]

        # Form pods while we have enough players
        while len(unassigned_available) >= 4:
            pod_players = unassigned_available[:4]
            pods.append(PodAssignment(day=day, players=pod_players))

            for player in pod_players:
                assigned_players.add(player)
                if player in reserved_players:
                    reserved_players.remove(player)  # No longer reserved once assigned

            # Recalculate available players
            unassigned_available = [
                p for p in available
                if p not in assigned_players and (p not in reserved_players or p in critical_for_day)
            ]

    # STEP 4: Second pass - allow double-play for flexible players to form additional pods
    # Check each day again to see if we're 1 player short of forming a pod
    for day, available in sorted_days:
        unassigned_available = [p for p in available if p not in assigned_players]

        # If we have 3 unassigned players, check if a flexible player can play twice
        if len(unassigned_available) == 3:
            # Find flexible players who are already assigned but available this day
            flexible_candidates = [
                p for p in available
                if p in assigned_players and len(availability.get(p, [])) > 1
            ]

            if flexible_candidates:
                # Use the first flexible player to complete the pod
                double_play_player = flexible_candidates[0]
                pod_players = unassigned_available + [double_play_player]
                pods.append(PodAssignment(day=day, players=pod_players))

                # Update assigned players (add the 3 new players, double-play already counted)
                for player in unassigned_available:
                    assigned_players.add(player)

    players_without_games = all_players - assigned_players

    return OptimizationResult(
        pods=pods,
        players_with_games=assigned_players,
        players_without_games=players_without_games
    )


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
