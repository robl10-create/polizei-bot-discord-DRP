import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

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
        # Liste aller Cogs
        cogs = [
            'cogs.listen',
            'cogs.help',
            'cogs.sanktionen',
            'cogs.verwaltung',
            'cogs.ausbildung',
            'cogs.abteilungen',
            'cogs.dienstnummern'
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(str(f"✅ {cog} erfolgreich geladen."))
            except Exception as e:
                print(str(f"❌ FEHLER beim Laden von {cog}: {e}"))
                
        # Slash Commands mit Discord synchronisieren
        print("Synchronisiere Commands...")
        await self.tree.sync()
        print("Commands erfolgreich synchronisiert!")

    async def on_ready(self):
        print(f'Eingeloggt als {self.user.name} (ID: {self.user.id})')
        print('Bot ist startklar!')

bot = RoleplayBot()

if __name__ == "__main__":
    bot.run(TOKEN)