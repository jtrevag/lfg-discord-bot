"""
Poll management commands cog.
"""

import discord
from discord.ext import commands


class PollsCog(commands.Cog, name="Polls"):
    """Commands for managing Commander game polls."""

    def __init__(self, bot):
        """Initialize the cog."""
        self.bot = bot

    @commands.command(name='lfgping')
    async def ping_command(self, ctx):
        """Check if the bot is online and responsive."""
        from lfg_bot.bot import get_version
        latency_ms = round(self.bot.latency * 1000)
        version = get_version()
        await ctx.send(f"🏓 Pong! Bot is online.\nLatency: {latency_ms}ms\nVersion: {version}")

    @commands.command(name='createpoll')
    @commands.has_permissions(administrator=True)
    async def create_poll_command(self, ctx):
        """Manually create a poll (admin only)."""
        from lfg_bot.bot import create_poll
        await create_poll(ctx.channel, self.bot.config)

    @commands.command(name='calculatepods')
    @commands.has_permissions(administrator=True)
    async def calculate_pods_command(self, ctx):
        """Manually trigger pod calculation from the latest poll (admin only)."""
        from lfg_bot.bot import process_poll_results
        from lfg_bot.utils.database import get_most_recent_poll

        # Try to find the most recent poll from the database
        poll_record = get_most_recent_poll(days_back=7)

        if not poll_record:
            await ctx.send("No recent poll found in the database. Create a poll first with !createpoll")
            return

        poll_message_id = int(poll_record.discord_message_id)

        # Fetch the poll message from Discord
        try:
            message = await ctx.channel.fetch_message(poll_message_id)
            if message.poll:
                await ctx.send("**Calculating pods from the latest poll...**")
                await process_poll_results(message.poll, ctx.channel, self.bot)
            else:
                await ctx.send("The message doesn't contain a poll.")
        except discord.NotFound:
            await ctx.send(f"Poll message (ID: {poll_message_id}) not found in this channel.")
        except Exception as e:
            await ctx.send(f"Error fetching poll: {e}")


async def setup(bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(PollsCog(bot))
