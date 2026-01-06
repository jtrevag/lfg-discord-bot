"""
Main entry point for the LFG Discord bot.
"""

import os
from dotenv import load_dotenv
from lfg_bot.bot import create_bot


def main():
    """Run the Discord bot."""
    # Load environment variables from config/.env
    load_dotenv('config/.env')

    token = os.getenv('DISCORD_BOT_TOKEN')

    if not token:
        print("Error: DISCORD_BOT_TOKEN not found in config/.env file")
        print("Please copy config/.env.example to config/.env and add your bot token")
        return 1

    # Create and run the bot
    bot = create_bot()
    bot.run(token)

    return 0


if __name__ == '__main__':
    exit(main())
