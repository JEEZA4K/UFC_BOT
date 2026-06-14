import discord
from discord.ext import commands, tasks
import asyncio
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"✅ Bot connecté : {bot.user}")
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ {len(synced)} commandes slash synchronisées")
    except Exception as e:
        logger.error(f"Erreur sync: {e}")
    
    check_upcoming_events.start()

@tasks.loop(hours=6)
async def check_upcoming_events():
    from ufc_scraper import get_next_event
    from database import get_setting
    channel_id = get_setting("prono_channel_id")
    if not channel_id:
        return
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return
    event = await get_next_event()
    if event:
        logger.info(f"Événement trouvé: {event['name']}")

async def load_extensions():
    extensions = ["cogs.pronos", "cogs.admin", "cogs.classement"]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            logger.info(f"✅ {ext} chargé")
        except Exception as e:
            logger.error(f"❌ Erreur chargement {ext}: {e}")

async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN manquant !")
    async with bot:
        await load_extensions()
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
