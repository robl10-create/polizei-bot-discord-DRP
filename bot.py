import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive  # Importiert deinen Mini-Webserver

# Laden der .env Datei
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Bot-Setup mit allen nötigen Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # WICHTIG: Im Discord Developer Portal unter "Intents" aktivieren!

class RoleplayBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Cogs laden
        await self.load_extension('cogs.listen')
        await self.load_extension('cogs.help')
        await self.load_extension('cogs.sanktionen')
        await self.load_extension('cogs.verwaltung')
        await self.load_extension('cogs.abteilungen')
        await self.load_extension('cogs.dienstnummern')
        
        # Slash Commands mit Discord synchronisieren
        print("Synchronisiere Commands...")
        await self.tree.sync()
        print("Commands erfolgreich synchronisiert!")

    async def on_ready(self):
        print(f'Eingeloggt als {self.user.name} (ID: {self.user.id})')
        print('Bot ist startklar!')

bot = RoleplayBot()

if __name__ == "__main__":
    # 1. Startet den Webserver für UptimeRobot im Hintergrund
    keep_alive()

    bot.run(TOKEN)