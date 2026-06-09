import discord
from discord.ext import commands
from discord import app_commands
import json
import os

DATA_FILE = "dienstnummern.json"

class ListenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daten = self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"channel_id": None, "mitarbeiter": {}}

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.daten, f, indent=4, ensure_ascii=False)

    async def update_list_channel(self, guild: discord.Guild):
        channel_id = self.daten.get("channel_id")
        if not channel_id:
            return
        
        channel = guild.get_channel(int(channel_id))
        if not channel:
            return

        embed = discord.Embed(
            title="🚔 Polizeipräsidium Deutschland - Dienstnummern & Mitarbeiterliste",
            color=discord.Color.blue()
        )

        # Ränge aufteilen
        raenge = {"BHL": [], "HD": [], "GD": [], "MD": []}
        
        for user_id, info in self.daten["mitarbeiter"].items():
            member = guild.get_member(int(user_id))
            username = member.mention if member else info.get("name", "Unbekannt")
            
            dn = info["nummer"]
            rang = info["rang"] # MD, GD, HD, BHL
            abteilung = f" [{info['abteilung']}]" if info.get("abteilung") else ""
            
            if rang in raenge:
                raenge[rang].append(f"• {username} ➔ **{rang}-{dn}**{abteilung}")

        embed.add_field(name="💼 Behördenleitung (BHL)", value="\n".join(raenge["BHL"]) or "Keine Einträge", inline=False)
        embed.add_field(name="🦅 Höherer Dienst (HD)", value="\n".join(raenge["HD"]) or "Keine Einträge", inline=False)
        embed.add_field(name="⭐ Gehobener Dienst (GD)", value="\n".join(raenge["GD"]) or "Keine Einträge", inline=False)
        embed.add_field(name="🛡️ Mittlerer Dienst (MD)", value="\n".join(raenge["MD"]) or "Keine Einträge", inline=False)

        # Alten Inhalt löschen oder neue Nachricht senden
        # Um es einfach zu halten, löschen wir alte Nachrichten des Bots im Channel und senden ein neues Embed
        async for message in channel.history(limit=10):
            if message.author == self.bot.user:
                await message.delete()

        await channel.send(embed=embed)

    @app_commands.command(name="setup-liste", description="Legt den Channel für die Dienstnummernliste fest.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_liste(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.daten["channel_id"] = str(channel.id)
        self.save_data()
        await interaction.response.send_message(f"Dienstnummern-Channel wurde auf {channel.mention} gesetzt!", ephemeral=True)
        await self.update_list_channel(interaction.guild)

    @app_commands.command(name="dienstnummern-einsicht", description="Sieh deine eigene Dienstnummer oder die eines Kollegen ein.")
    async def dn_einsicht(self, interaction: discord.Interaction, mitarbeiter: discord.Member = None):
        target = mitarbeiter or interaction.user
        user_id = str(target.id)

        if user_id in self.daten["mitarbeiter"]:
            info = self.daten["mitarbeiter"][user_id]
            abt = f"\n**Abteilung:** {info['abteilung']}" if info.get('abteilung') else ""
            await interaction.response.send_message(
                f"**Mitarbeiter:** {target.mention}\n**Dienstnummer:** {info['rang']}-{info['nummer']}{abt}", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(f"{target.mention} ist nicht in der Dienstnummernliste eingetragen.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ListenCog(bot))