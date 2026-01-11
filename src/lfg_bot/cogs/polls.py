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

        active_poll_id = getattr(self.bot, 'active_poll_id', None)

        if not active_poll_id:
            await ctx.send("No active poll found. Create a poll first with !createpoll")
            return

        # Fetch the poll message
        try:
            message = await ctx.channel.fetch_message(active_poll_id)
            if message.poll:
                await process_poll_results(message.poll, ctx.channel)
            else:
                await ctx.send("The message doesn't contain a poll.")
        except discord.NotFound:
            await ctx.send("Poll message not found.")
        except Exception as e:
            await ctx.send(f"Error fetching poll: {e}")


async def setup(bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(PollsCog(bot))
