import discord
from discord.ext import commands
import json
import os

class ListenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daten_pfad = "daten/personal.json"
        self.daten = self.load_data()

    def load_data(self):
        if not os.path.exists("daten"):
            os.makedirs("daten")
        if not os.path.exists(self.daten_pfad):
            return {"mitarbeiter": {}}
        try:
            with open(self.daten_pfad, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"mitarbeiter": {}}

    def save_data(self):
        with open(self.daten_pfad, "w", encoding="utf-8") as f:
            json.dump(self.daten, f, ensure_ascii=False, indent=4)

async def setup(bot):
    await bot.add_cog(ListenCog(bot))