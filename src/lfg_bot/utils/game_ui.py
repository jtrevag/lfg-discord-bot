"""
Discord UI components for game result reporting.

Provides buttons, modals, and views for players to report game winners
after pods are formed and games are played.
"""

import discord
from discord import ui
from datetime import datetime


async def post_pods_with_buttons(channel: discord.TextChannel, result, poll_record):
    """
    Post pod assignments without interactive buttons (buttons disabled for now).

    Args:
        channel: Discord channel to post in
        result: OptimizationResult from pod_optimizer
        poll_record: Database Poll record
    """
    from lfg_bot.utils.database import Pod, format_player_name

    # Group pods by day
    pods_by_day = {}
    for assignment in result.pods:
        if assignment.day not in pods_by_day:
            pods_by_day[assignment.day] = []
        pods_by_day[assignment.day].append(assignment)

    # Post each day's pods
    for day, assignments in pods_by_day.items():
        day_message = f"**{day}:**\n"

        for idx, assignment in enumerate(assignments, 1):
            # Get pod from database
            pods = list(Pod.select().where(
                (Pod.poll == poll_record) &
                (Pod.day_of_week == day)
            ))

            if idx <= len(pods):
                pod = pods[idx - 1]

                # Format player list with real names
                players = [
                    format_player_name(pod.player1_id),
                    format_player_name(pod.player2_id),
                    format_player_name(pod.player3_id),
                    format_player_name(pod.player4_id)
                ]

                pod_text = f"Pod {idx}: {', '.join(players)}\n"
                day_message += pod_text

        # Post all pods for this day in a single message
        await channel.send(day_message.strip())

    # Post players without games (if any)
    if result.players_without_games:
        from lfg_bot.utils.database import format_player_name
        players_str = ", ".join([format_player_name(pid) for pid in result.players_without_games])
        await channel.send(f"\n**Players without games this week:**\n{players_str}")


class WinnerSelectionModal(ui.Modal, title="Report Game Result"):
    """Modal form for selecting the winner of a game."""

    def __init__(self, pod, bot):
        super().__init__()
        self.pod = pod
        self.bot = bot

        # Get player names for dropdown options
        from lfg_bot.utils.database import get_real_name

        players = [
            (pod.player1_id, get_real_name(pod.player1_id) or f"Player {pod.player1_id}"),
            (pod.player2_id, get_real_name(pod.player2_id) or f"Player {pod.player2_id}"),
            (pod.player3_id, get_real_name(pod.player3_id) or f"Player {pod.player3_id}"),
            (pod.player4_id, get_real_name(pod.player4_id) or f"Player {pod.player4_id}")
        ]

        # Create winner select dropdown
        self.winner_select = ui.Select(
            placeholder="Select the winner",
            options=[
                discord.SelectOption(
                    label=real_name,
                    value=pid,
                    description=f"Discord ID: {pid}"
                )
                for pid, real_name in players
            ]
        )
        self.add_item(self.winner_select)

        # Optional notes field
        self.notes_input = ui.TextInput(
            label="Game Notes (optional)",
            style=discord.TextStyle.paragraph,
            placeholder="Any notes about the game...",
            required=False,
            max_length=500
        )
        self.add_item(self.notes_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission - show confirmation dialog."""
        winner_id = self.winner_select.values[0]

        # Get winner display name
        from lfg_bot.utils.database import get_real_name
        winner_name = get_real_name(winner_id) or f"<@{winner_id}>"

        # Show confirmation dialog
        confirm_view = ConfirmWinnerView(
            pod=self.pod,
            winner_id=winner_id,
            winner_name=winner_name,
            notes=self.notes_input.value,
            reported_by_id=str(interaction.user.id)
        )

        await interaction.response.send_message(
            f"⚠️ **Confirm winner:** {winner_name}\nIs this correct?",
            view=confirm_view,
            ephemeral=True  # Only reporter sees this
        )


class ConfirmWinnerView(ui.View):
    """Confirmation dialog for game result submission."""

    def __init__(self, pod, winner_id, winner_name, notes, reported_by_id):
        super().__init__(timeout=180)  # 3 minute timeout for confirmation
        self.pod = pod
        self.winner_id = winner_id
        self.winner_name = winner_name
        self.notes = notes
        self.reported_by_id = reported_by_id

    @ui.button(label="✅ Yes, Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        """Confirm and save the game result."""
        from lfg_bot.utils.database import record_game_result, format_player_name

        try:
            # Save to database
            record_game_result(
                pod_id=self.pod.id,
                winner_id=self.winner_id,
                reported_by_id=self.reported_by_id,
                notes=self.notes
            )

            # Update original pod message
            channel = interaction.channel
            try:
                pod_message = await channel.fetch_message(int(self.pod.discord_message_id))

                winner_display = format_player_name(self.winner_id)
                reporter_display = format_player_name(self.reported_by_id)

                # Update message with completion status
                new_content = f"{pod_message.content}\n\n✅ **Completed** - Winner: {winner_display}\n"
                new_content += f"_Reported by {reporter_display} on {datetime.now().strftime('%b %d, %I:%M %p')}_"

                if self.notes:
                    new_content += f"\n_Notes: {self.notes}_"

                await pod_message.edit(
                    content=new_content,
                    view=None  # Remove button
                )
            except discord.NotFound:
                # Message not found, but result was saved
                pass

            await interaction.response.edit_message(
                content=f"✅ Game result recorded! Winner: {winner_display}",
                view=None
            )

        except Exception as e:
            await interaction.response.edit_message(
                content=f"❌ Error recording result: {str(e)}",
                view=None
            )

    @ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        """Cancel the submission."""
        await interaction.response.edit_message(
            content="❌ Cancelled. Click the 'Game Completed' button to try again.",
            view=None
        )
