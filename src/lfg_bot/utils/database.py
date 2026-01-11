"""Database models and helper functions for game result tracking."""

import os
from datetime import datetime, timedelta
from peewee import (
    SqliteDatabase,
    Model,
    CharField,
    TextField,
    DateTimeField,
    DateField,
    IntegerField,
    FloatField,
    BooleanField,
    ForeignKeyField,
)

# Database instance (will be initialized in initialize_database())
db = SqliteDatabase(None)


class BaseModel(Model):
    """Base model for all database tables."""

    class Meta:
        database = db


class League(BaseModel):
    """Represents a season/time period for grouping games."""

    name = CharField(unique=True)
    start_date = DateField()
    end_date = DateField(null=True)  # NULL = currently active
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)


class Player(BaseModel):
    """Central registry of all players."""

    discord_user_id = CharField(primary_key=True)  # Discord user ID
    real_name = CharField(null=True)  # Real name (e.g., "Patrick")
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)


class Poll(BaseModel):
    """Tracks weekly polls that create pods."""

    league = ForeignKeyField(League, backref='polls')
    discord_message_id = CharField(unique=True)
    created_at = DateTimeField(default=datetime.now)
    completed_at = DateTimeField(null=True)
    poll_question = TextField(null=True)
    poll_days = TextField(default='[]')  # JSON array


class Pod(BaseModel):
    """Game assignments (scheduled 4-player games)."""

    poll = ForeignKeyField(Poll, backref='pods')
    day_of_week = CharField()
    scheduled_date = DateField(null=True)
    player1_id = CharField()
    player2_id = CharField()
    player3_id = CharField()
    player4_id = CharField()
    status = CharField(default='scheduled')  # 'scheduled', 'completed', 'cancelled'
    discord_message_id = CharField(null=True)
    created_at = DateTimeField(default=datetime.now)


class GameResult(BaseModel):
    """Completed game outcomes."""

    pod = ForeignKeyField(Pod, backref='results', unique=True)
    winner_id = CharField()
    reported_by_id = CharField()
    reported_at = DateTimeField(default=datetime.now)
    notes = TextField(null=True)


class PlayerStats(BaseModel):
    """Pre-computed statistics cache for performance."""

    league = ForeignKeyField(League, backref='player_stats')
    player_id = CharField()
    games_played = IntegerField(default=0)
    games_won = IntegerField(default=0)
    win_rate = FloatField(default=0.0)
    last_updated = DateTimeField(default=datetime.now)

    class Meta:
        indexes = (
            (('league', 'player_id'), True),  # Unique constraint
        )


def initialize_database(db_path='data/lfg_bot.db'):
    """Initialize database and create tables.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Database instance
    """
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Initialize database
    db.init(db_path)

    # Create tables
    db.create_tables([League, Player, Poll, Pod, GameResult, PlayerStats])

    # Create default league if none exists
    if League.select().count() == 0:
        League.create(
            name=f"Season {datetime.now().year}",
            start_date=datetime.now().date(),
            is_active=True
        )

    return db


def verify_database(database):
    """Verify database connectivity.

    Args:
        database: Database instance to verify
    """
    # Simple connectivity check
    League.select().count()


def get_active_league():
    """Get the currently active league.

    Returns:
        Active League object, or None if no active league
    """
    return League.get_or_none(League.is_active == True)


def get_real_name(discord_user_id):
    """Get a player's real name from Discord user ID.

    Args:
        discord_user_id: Discord user ID (string)

    Returns:
        Real name string, or None if not mapped
    """
    player = Player.get_or_none(Player.discord_user_id == discord_user_id)
    return player.real_name if player else None


def get_discord_id(real_name):
    """Get Discord user ID from real name.

    Args:
        real_name: Player's real name (string)

    Returns:
        Discord user ID string, or None if not found
    """
    player = Player.get_or_none(Player.real_name == real_name)
    return player.discord_user_id if player else None


def format_player_name(discord_user_id):
    """Format player name with real name if available.

    Args:
        discord_user_id: Discord user ID (string)

    Returns:
        Formatted string: "<@user_id> (RealName)" or just "<@user_id>"
    """
    real_name = get_real_name(discord_user_id)
    if real_name:
        return f"<@{discord_user_id}> ({real_name})"
    return f"<@{discord_user_id}>"


def save_poll_and_pods(bot, discord_message_id, result, poll_days):
    """Save poll and pod assignments to database.

    Args:
        bot: Bot instance
        discord_message_id: Discord message ID of the poll
        result: OptimizationResult from pod_optimizer
        poll_days: List of days from config

    Returns:
        Poll object that was created
    """
    import json

    # Get active league
    league = get_active_league()
    if not league:
        raise ValueError("No active league found")

    # Create poll record
    poll = Poll.create(
        league=league,
        discord_message_id=discord_message_id,
        created_at=datetime.now(),
        completed_at=datetime.now(),
        poll_question=bot.config.get('poll_question', 'Weekly availability poll'),
        poll_days=json.dumps(poll_days)
    )

    # Create pod records
    for pod_assignment in result.pods:
        Pod.create(
            poll=poll,
            day_of_week=pod_assignment.day,
            scheduled_date=None,  # Will be set later if needed
            player1_id=pod_assignment.players[0],
            player2_id=pod_assignment.players[1],
            player3_id=pod_assignment.players[2],
            player4_id=pod_assignment.players[3],
            status='scheduled'
        )

        # Auto-create player records if they don't exist
        for player_id in pod_assignment.players:
            Player.get_or_create(discord_user_id=player_id)

    return poll


def record_game_result(pod_id, winner_id, reported_by_id, notes=None):
    """Record a game result.

    Args:
        pod_id: Pod ID
        winner_id: Discord user ID of winner
        reported_by_id: Discord user ID of reporter
        notes: Optional notes about the game

    Returns:
        GameResult object that was created
    """
    # Get pod
    pod = Pod.get_by_id(pod_id)

    # Create game result
    result = GameResult.create(
        pod=pod,
        winner_id=winner_id,
        reported_by_id=reported_by_id,
        reported_at=datetime.now(),
        notes=notes
    )

    # Update pod status
    pod.status = 'completed'
    pod.save()

    # Update player stats
    poll = pod.poll
    league = poll.league
    update_player_stats(league.id)

    return result


def update_player_stats(league_id):
    """Recalculate player statistics for a league.

    Args:
        league_id: League ID to calculate stats for
    """
    # Get all completed pods in this league
    pods = (Pod
            .select()
            .join(Poll)
            .where(Poll.league_id == league_id)
            .where(Pod.status == 'completed'))

    # Build stats dictionary
    stats = {}

    for pod in pods:
        # Get all players in this pod
        players = [pod.player1_id, pod.player2_id, pod.player3_id, pod.player4_id]

        # Get game result (if exists)
        result = GameResult.get_or_none(GameResult.pod == pod)
        if not result:
            continue

        winner_id = result.winner_id

        for player_id in players:
            if player_id not in stats:
                stats[player_id] = {'games_played': 0, 'games_won': 0}

            stats[player_id]['games_played'] += 1
            if player_id == winner_id:
                stats[player_id]['games_won'] += 1

    # Update or create PlayerStats records
    for player_id, player_stats in stats.items():
        games_played = player_stats['games_played']
        games_won = player_stats['games_won']
        win_rate = (games_won / games_played * 100) if games_played > 0 else 0

        # Update or create
        ps, created = PlayerStats.get_or_create(
            league_id=league_id,
            player_id=player_id,
            defaults={
                'games_played': games_played,
                'games_won': games_won,
                'win_rate': win_rate,
                'last_updated': datetime.now()
            }
        )

        if not created:
            ps.games_played = games_played
            ps.games_won = games_won
            ps.win_rate = win_rate
            ps.last_updated = datetime.now()
            ps.save()


def get_leaderboard(league_id, min_games=3, limit=10):
    """Get leaderboard for a league.

    Args:
        league_id: League ID
        min_games: Minimum games played to be included
        limit: Maximum number of entries to return

    Returns:
        List of PlayerStats objects, sorted by win rate
    """
    return (PlayerStats
            .select()
            .where(PlayerStats.league_id == league_id)
            .where(PlayerStats.games_played >= min_games)
            .order_by(PlayerStats.win_rate.desc())
            .limit(limit))


def get_head_to_head(league_id, player1_id, player2_id):
    """Get head-to-head stats for two players.

    Args:
        league_id: League ID
        player1_id: First player's Discord ID
        player2_id: Second player's Discord ID

    Returns:
        Dictionary with head-to-head stats
    """
    # Find all pods where both players played together
    pods = (Pod
            .select()
            .join(Poll)
            .where(Poll.league_id == league_id)
            .where(Pod.status == 'completed'))

    together_pods = []
    for pod in pods:
        players = [pod.player1_id, pod.player2_id, pod.player3_id, pod.player4_id]
        if player1_id in players and player2_id in players:
            together_pods.append(pod)

    # Count wins
    player1_wins = 0
    player2_wins = 0
    other_wins = 0

    for pod in together_pods:
        result = GameResult.get_or_none(GameResult.pod == pod)
        if not result:
            continue

        if result.winner_id == player1_id:
            player1_wins += 1
        elif result.winner_id == player2_id:
            player2_wins += 1
        else:
            other_wins += 1

    total_games = len(together_pods)

    return {
        'total_games': total_games,
        'player1_wins': player1_wins,
        'player2_wins': player2_wins,
        'other_wins': other_wins,
        'player1_win_rate': (player1_wins / total_games * 100) if total_games > 0 else 0,
        'player2_win_rate': (player2_wins / total_games * 100) if total_games > 0 else 0,
        'other_win_rate': (other_wins / total_games * 100) if total_games > 0 else 0,
    }


def get_recent_games(limit=5):
    """Get recent completed games.

    Args:
        limit: Maximum number of games to return

    Returns:
        List of GameResult objects
    """
    return (GameResult
            .select()
            .order_by(GameResult.reported_at.desc())
            .limit(limit))


def get_polls_needing_processing(days_back=7):
    """Get polls that might need processing (created recently but have no pods).

    Args:
        days_back: How many days back to check

    Returns:
        List of Poll objects that have no associated pods
    """
    cutoff_date = datetime.now() - timedelta(days=days_back)

    # Get polls created recently
    recent_polls = (Poll
                    .select()
                    .where(Poll.created_at >= cutoff_date)
                    .order_by(Poll.created_at.desc()))

    # Filter to only polls with no pods
    polls_needing_processing = []
    for poll in recent_polls:
        pod_count = Pod.select().where(Pod.poll == poll).count()
        if pod_count == 0:
            polls_needing_processing.append(poll)

    return polls_needing_processing


def create_new_league(name, start_date):
    """Create a new league and archive the current one.

    Args:
        name: League name
        start_date: Start date (string in YYYY-MM-DD format or date object)

    Returns:
        Newly created League object
    """
    from datetime import date

    # Convert string to date if needed
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    # Archive current active league
    active_league = get_active_league()
    if active_league:
        active_league.is_active = False
        active_league.end_date = date.today()
        active_league.save()

    # Create new league
    league = League.create(
        name=name,
        start_date=start_date,
        is_active=True
    )

    return league


def import_from_google_sheet(sheet_url, league):
    """Import game results from Google Sheets.

    Expected columns: Week, Player 1, Player 2, Player 3, Player 4, Winner

    Args:
        sheet_url: URL to Google Sheet
        league: League object to import games into

    Returns:
        dict with 'games_imported', 'pods_created', 'errors'
    """
    import gspread
    from google.oauth2.service_account import Credentials

    # Authenticate with Google Sheets
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds = Credentials.from_service_account_file('config/google-credentials.json', scopes=scopes)
    client = gspread.authorize(creds)

    # Open sheet
    sheet = client.open_by_url(sheet_url).sheet1

    # Get all records (assumes first row is header)
    records = sheet.get_all_records()

    games_imported = 0
    pods_created = 0
    errors = []

    for idx, row in enumerate(records):
        try:
            # Extract data
            week = row['Week']  # e.g., "W0", "W1"
            player_names = [
                row['Player 1'],
                row['Player 2'],
                row['Player 3'],
                row['Player 4']
            ]
            winner_name = row['Winner']

            # Look up Discord IDs from player names
            player_ids = []
            for name in player_names:
                player = Player.get_or_none(Player.real_name == name)
                if not player:
                    errors.append(f"Row {idx + 2}: Player '{name}' not mapped. Use !mapplayer first.")
                    player_ids = []
                    break
                player_ids.append(player.discord_user_id)

            if len(player_ids) != 4:
                continue  # Skip this row if players not found

            # Look up winner Discord ID
            winner_player = Player.get_or_none(Player.real_name == winner_name)
            if not winner_player:
                errors.append(f"Row {idx + 2}: Winner '{winner_name}' not mapped.")
                continue

            # Calculate date from week number
            week_num = int(week.replace('W', ''))
            game_date = league.start_date + timedelta(weeks=week_num)

            # Create poll record (one per week)
            poll, _ = Poll.get_or_create(
                league=league,
                discord_message_id=f"import_{league.id}_{week}",  # Fake ID for imports
                defaults={
                    'created_at': game_date,
                    'completed_at': game_date,
                    'poll_question': f'Imported from Sheet - {week}',
                    'poll_days': '[]'
                }
            )

            # Create pod
            pod = Pod.create(
                poll=poll,
                day_of_week='Unknown',  # Imported games don't have day info
                scheduled_date=game_date,
                player1_id=player_ids[0],
                player2_id=player_ids[1],
                player3_id=player_ids[2],
                player4_id=player_ids[3],
                status='completed'
            )
            pods_created += 1

            # Create game result
            GameResult.create(
                pod=pod,
                winner_id=winner_player.discord_user_id,
                reported_by_id='import',  # Special marker for imports
                reported_at=game_date,
                notes=f'Imported from Google Sheets ({week})'
            )
            games_imported += 1

        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")
            continue

    # Recalculate player stats for this league
    update_player_stats(league.id)

    return {
        'games_imported': games_imported,
        'pods_created': pods_created,
        'errors': errors
    }
