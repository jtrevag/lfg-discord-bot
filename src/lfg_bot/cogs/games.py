"""
Game result tracking and statistics commands.

Provides commands for:
- Reporting game results
- Viewing statistics and leaderboards
- Managing player mappings
- League management
- Importing historical data
"""

import discord
from discord.ext import commands
from datetime import datetime

from lfg_bot.utils.game_ui import WinnerSelectionModal
from lfg_bot.utils.database import (
    Pod, Player, League, Poll, GameResult, PlayerStats,
    get_active_league, record_game_result, update_player_stats,
    get_leaderboard, get_head_to_head, get_recent_games,
    create_new_league, get_real_name, get_discord_id, format_player_name
)


class GamesCog(commands.Cog, name="Games"):
    """Commands for managing game results and statistics."""

    def __init__(self, bot):
        self.bot = bot

    # === Button Interaction Handler ===

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button clicks on pod messages."""
        if not interaction.data:
            return

        custom_id = interaction.data.get('custom_id', '')

        if custom_id.startswith('game_complete_'):
            # Extract pod ID from button
            pod_id = int(custom_id.split('_')[-1])

            try:
                pod = Pod.get_by_id(pod_id)

                # Check if game already completed
                existing_result = GameResult.get_or_none(GameResult.pod == pod)
                if existing_result:
                    await interaction.response.send_message(
                        "❌ This game has already been reported!",
                        ephemeral=True
                    )
                    return

                # Show winner selection modal
                modal = WinnerSelectionModal(pod, self.bot)
                await interaction.response.send_modal(modal)

            except Pod.DoesNotExist:
                await interaction.response.send_message(
                    "❌ Pod not found in database.",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Error: {str(e)}",
                    ephemeral=True
                )

    # === Manual Result Entry ===

    @commands.command(name='completegame')
    @commands.has_permissions(administrator=True)
    async def complete_game(self, ctx, pod_id: int, winner: discord.Member):
        """
        Manually report game result (admin only).

        Usage: !completegame <pod_id> @winner
        """
        try:
            pod = Pod.get_by_id(pod_id)

            # Check if already completed
            existing_result = GameResult.get_or_none(GameResult.pod == pod)
            if existing_result:
                await ctx.send("❌ This game has already been reported!")
                return

            record_game_result(
                pod_id=pod_id,
                winner_id=str(winner.id),
                reported_by_id=str(ctx.author.id),
                notes="Manually entered by admin"
            )

            winner_display = format_player_name(str(winner.id))
            await ctx.send(f"✅ Game {pod_id} marked complete. Winner: {winner_display}")

        except Pod.DoesNotExist:
            await ctx.send(f"❌ Pod {pod_id} not found.")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

    @commands.command(name='editgame')
    @commands.has_permissions(administrator=True)
    async def edit_game(self, ctx, pod_id: int, winner: discord.Member):
        """
        Edit/correct game result (admin only).

        Usage: !editgame <pod_id> @winner
        """
        try:
            pod = Pod.get_by_id(pod_id)
            game_result = GameResult.get(GameResult.pod == pod)

            old_winner_id = game_result.winner_id
            game_result.winner_id = str(winner.id)
            game_result.reported_by_id = str(ctx.author.id)
            game_result.reported_at = datetime.now()
            game_result.notes = (game_result.notes or "") + f"\n[Edited by admin on {datetime.now().strftime('%Y-%m-%d')}]"
            game_result.save()

            # Recalculate stats
            league = get_active_league()
            if league:
                update_player_stats(league.id)

            old_winner_display = format_player_name(old_winner_id)
            new_winner_display = format_player_name(str(winner.id))
            await ctx.send(
                f"✅ Game {pod_id} updated.\n"
                f"New winner: {new_winner_display}\n"
                f"Previous winner: {old_winner_display}"
            )

        except Pod.DoesNotExist:
            await ctx.send(f"❌ Pod {pod_id} not found.")
        except GameResult.DoesNotExist:
            await ctx.send(f"❌ No game result found for pod {pod_id}. Use `!completegame` instead.")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

    # === Player Name Mapping ===

    @commands.command(name='mapplayer')
    @commands.has_permissions(administrator=True)
    async def map_player(self, ctx, member: discord.Member, *, real_name: str):
        """
        Map a Discord user to their real name.

        Usage: !mapplayer @user Real Name
        Example: !mapplayer @Patrick Patrick
        """
        player, created = Player.get_or_create(
            discord_user_id=str(member.id),
            defaults={'real_name': real_name}
        )

        if not created:
            old_name = player.real_name
            player.real_name = real_name
            player.updated_at = datetime.now()
            player.save()
            await ctx.send(f"✅ Updated {member.mention}: **{old_name}** → **{real_name}**")
        else:
            await ctx.send(f"✅ Mapped {member.mention} → **{real_name}**")

    @commands.command(name='listmappings')
    async def list_mappings(self, ctx):
        """Show all player name mappings."""
        players = Player.select().order_by(Player.real_name)

        if not players:
            await ctx.send(
                "No player mappings found.\n"
                "Use `!mapplayer @user \"Real Name\"` to create mappings."
            )
            return

        message = "👥 **Player Name Mappings**\n\n"
        for player in players:
            message += f"<@{player.discord_user_id}> → **{player.real_name}**\n"

        await ctx.send(message)

    # === Statistics Commands ===

    @commands.command(name='leaderboard')
    async def leaderboard(self, ctx, *, league_name: str = None):
        """
        Show top 10 players by win rate (minimum 3 games).

        Usage: !leaderboard [league name]
        Example: !leaderboard
        Example: !leaderboard Historical Games
        """
        try:
            if league_name:
                league = League.get(League.name == league_name)
            else:
                league = get_active_league()

            if not league:
                await ctx.send("❌ No active league found.")
                return

            leaderboard = list(get_leaderboard(league.id, min_games=3, limit=10))

            if not leaderboard:
                await ctx.send(f"No statistics yet for **{league.name}**.\nPlay some games first!")
                return

            message = f"🏆 **{league.name} Leaderboard**\n"
            message += f"_(Minimum 3 games)_\n\n"

            for rank, stats in enumerate(leaderboard, 1):
                player_display = format_player_name(stats.player_id)
                message += f"{rank}. {player_display} - {stats.win_rate:.1f}% "
                message += f"({stats.games_won}W / {stats.games_played}G)\n"

            await ctx.send(message)

        except League.DoesNotExist:
            await ctx.send(f"❌ League '{league_name}' not found.")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

    @commands.command(name='stats')
    async def player_stats(self, ctx, player: discord.Member = None, *, league_name: str = None):
        """
        Show detailed player statistics.

        Usage: !stats [@player] [league name]
        Example: !stats
        Example: !stats @Patrick
        Example: !stats @Patrick Historical Games
        """
        player = player or ctx.author

        try:
            if league_name:
                league = League.get(League.name == league_name)
            else:
                league = get_active_league()

            if not league:
                await ctx.send("❌ No active league found.")
                return

            stats = PlayerStats.get_or_none(
                (PlayerStats.league == league) &
                (PlayerStats.player_id == str(player.id))
            )

            if not stats:
                await ctx.send(
                    f"No stats found for {player.mention} in **{league.name}**.\n"
                    f"They haven't played any games yet!"
                )
                return

            player_display = format_player_name(str(player.id))
            message = f"📊 **Stats for {player_display}**\n"
            message += f"_League: {league.name}_\n\n"
            message += f"Games Played: {stats.games_played}\n"
            message += f"Games Won: {stats.games_won}\n"
            message += f"Win Rate: {stats.win_rate:.1f}%\n"

            await ctx.send(message)

        except League.DoesNotExist:
            await ctx.send(f"❌ League '{league_name}' not found.")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

    @commands.command(name='headtohead')
    async def head_to_head(self, ctx, player1: discord.Member, player2: discord.Member, *, league_name: str = None):
        """
        Compare two players' records in games they played together.

        Usage: !headtohead @player1 @player2 [league name]
        Example: !headtohead @Patrick @John
        """
        try:
            if league_name:
                league = League.get(League.name == league_name)
            else:
                league = get_active_league()

            if not league:
                await ctx.send("❌ No active league found.")
                return

            h2h = get_head_to_head(league.id, str(player1.id), str(player2.id))

            if h2h['total_games'] == 0:
                await ctx.send(f"{player1.mention} and {player2.mention} haven't played together yet!")
                return

            player1_display = format_player_name(str(player1.id))
            player2_display = format_player_name(str(player2.id))

            message = f"⚔️ **{player1_display} vs {player2_display}**\n"
            message += f"_League: {league.name}_\n\n"
            message += f"Games Together: {h2h['total_games']}\n"
            message += f"{player1_display} Wins: {h2h['player1_wins']} ({h2h['player1_win_rate']:.1f}%)\n"
            message += f"{player2_display} Wins: {h2h['player2_wins']} ({h2h['player2_win_rate']:.1f}%)\n"
            message += f"Other Wins: {h2h['other_wins']} ({h2h['other_win_rate']:.1f}%)\n"

            await ctx.send(message)

        except League.DoesNotExist:
            await ctx.send(f"❌ League '{league_name}' not found.")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

    @commands.command(name='recentgames')
    async def recent_games(self, ctx, count: int = 5):
        """
        Show last N completed games.

        Usage: !recentgames [count]
        Example: !recentgames 10
        """
        try:
            if count < 1 or count > 20:
                await ctx.send("❌ Count must be between 1 and 20.")
                return

            games = list(get_recent_games(limit=count))

            if not games:
                await ctx.send("No completed games found!")
                return

            message = f"🎮 **Recent Games (Last {len(games)})**\n\n"

            for game in games:
                winner_display = format_player_name(game.winner_id)

                # Get all players in the pod
                players = [
                    game.pod.player1_id,
                    game.pod.player2_id,
                    game.pod.player3_id,
                    game.pod.player4_id
                ]
                players_str = ", ".join([
                    format_player_name(pid)
                    for pid in players
                    if pid != game.winner_id
                ])

                message += f"{game.reported_at.strftime('%b %d')} - {game.pod.day_of_week}: "
                message += f"{winner_display} won\n"
                message += f"  _(vs {players_str})_\n"

            await ctx.send(message)

        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

    # === League Management ===

    @commands.command(name='createleague')
    @commands.has_permissions(administrator=True)
    async def create_league(self, ctx, start_date: str, *, name: str):
        """
        Create new league (auto-archives current league).

        Usage: !createleague YYYY-MM-DD League Name
        Example: !createleague 2026-02-01 Spring Season
        """
        try:
            league = create_new_league(name, start_date)
            await ctx.send(
                f"✅ Created new league: **{name}**\n"
                f"Start date: {league.start_date.strftime('%b %d, %Y')}\n"
                f"Previous league archived."
            )
        except ValueError as e:
            await ctx.send(f"❌ Invalid date format. Use YYYY-MM-DD (e.g., 2026-02-01)")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

    @commands.command(name='currentleague')
    async def current_league(self, ctx):
        """Show active league info."""
        league = get_active_league()

        if not league:
            await ctx.send("❌ No active league found.")
            return

        # Count games in this league
        games_count = (GameResult
                      .select()
                      .join(Pod)
                      .join(Poll)
                      .where(Poll.league == league)
                      .count())

        message = f"📅 **Current League: {league.name}**\n\n"
        message += f"Started: {league.start_date.strftime('%b %d, %Y')}\n"
        message += f"Games Played: {games_count}\n"

        await ctx.send(message)

    @commands.command(name='leagues')
    async def list_leagues(self, ctx):
        """List all leagues."""
        leagues = League.select().order_by(League.start_date.desc())

        if not leagues:
            await ctx.send("No leagues found.")
            return

        message = "📚 **All Leagues**\n\n"

        for league in leagues:
            status = "🟢" if league.is_active else "⚪"
            end = "Present" if not league.end_date else league.end_date.strftime('%b %d, %Y')

            # Count games in this league
            games_count = (GameResult
                          .select()
                          .join(Pod)
                          .join(Poll)
                          .where(Poll.league == league)
                          .count())

            message += f"{status} **{league.name}** "
            message += f"({league.start_date.strftime('%b %d, %Y')} - {end}) "
            message += f"- {games_count} games\n"

        await ctx.send(message)

    # === Google Sheets Import ===

    @commands.command(name='importsheet')
    @commands.has_permissions(administrator=True)
    async def import_sheet(self, ctx, sheet_url: str, *, league_name: str = None):
        """
        Import game results from Google Sheets (ADMIN ONLY).

        Sheet must have columns: Week, Player 1, Player 2, Player 3, Player 4, Winner
        Players must be mapped first using !mapplayer command.

        Usage: !importsheet <sheet_url> [league name]
        Example: !importsheet https://docs.google.com/spreadsheets/d/... Historical Games
        """
        from lfg_bot.utils.database import import_from_google_sheet

        await ctx.send("📥 Starting import... This may take a moment.")

        try:
            # Get or create league
            if league_name:
                league, created = League.get_or_create(
                    name=league_name,
                    defaults={
                        'start_date': datetime.now().date(),
                        'is_active': False
                    }
                )
                if created:
                    await ctx.send(f"Created new league: **{league_name}**")
            else:
                league = get_active_league()
                if not league:
                    await ctx.send("❌ No active league found. Specify a league name.")
                    return

            # Import games
            result = import_from_google_sheet(sheet_url, league)

            message = f"✅ **Import Complete!**\n\n"
            message += f"League: {league.name}\n"
            message += f"Games Imported: {result['games_imported']}\n"
            message += f"Pods Created: {result['pods_created']}\n"

            if result.get('errors'):
                message += f"\n⚠️ **Warnings:**\n"
                for error in result['errors'][:5]:  # Show first 5 errors
                    message += f"- {error}\n"
                if len(result['errors']) > 5:
                    message += f"... and {len(result['errors']) - 5} more\n"

            await ctx.send(message)

        except Exception as e:
            await ctx.send(
                f"❌ Import failed: {str(e)}\n\n"
                f"**Make sure:**\n"
                f"1. All players are mapped (`!mapplayer`)\n"
                f"2. Sheet is publicly readable\n"
                f"3. Sheet has correct columns: Week, Player 1, Player 2, Player 3, Player 4, Winner\n"
                f"4. Google credentials file exists at config/google-credentials.json"
            )


async def setup(bot):
    """Load the Games cog."""
    await bot.add_cog(GamesCog(bot))
