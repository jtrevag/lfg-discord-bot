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


def _find_best_assignment(
    day_to_players: Dict[str, List[str]],
    all_players: Set[str],
    availability: Dict[str, List[str]] = None
) -> OptimizationResult:
    """
    Find the best pod assignment using a greedy approach prioritizing unique players.

    Strategy: Prioritize days with more "unique" players (available only on that day)
    to avoid stranding inflexible players while flexible players fill other days.
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

    # Sort days by unique player count first, then total count (both descending)
    sorted_days = sorted(
        day_to_players.items(),
        key=lambda x: (_count_unique_players(x[0], day_to_players, availability), len(x[1])),
        reverse=True
    )

    for day, available in sorted_days:
        # Get players who are available and not yet assigned
        unassigned_available = [p for p in available if p not in assigned_players]

        # If we have exactly 4 or more players, form pods
        while len(unassigned_available) >= 4:
            # Take first 4 players (could be optimized further)
            pod_players = unassigned_available[:4]
            pods.append(PodAssignment(day=day, players=pod_players))

            for player in pod_players:
                assigned_players.add(player)

            unassigned_available = [p for p in available if p not in assigned_players]

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
