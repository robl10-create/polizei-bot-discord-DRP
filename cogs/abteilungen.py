import discord
from discord.ext import commands
from discord import app_commands
from cogs.listen import ListenCog

ALLOWED_ROLE_ID = 1497905102156206162

ABTEILUNGEN = {
    "SG23_DIENSTAUFSICHT": {
        "name": "SG23 | Dienstaufsicht",
        "role_id": 1497905102156206162
    },
    "SG23_AZUBI": {
        "name": "SG23 | Azubi",
        "role_id": 1527040334981369887
    },
    "SG22_AUSBILDUNG": {
        "name": "SG22 | Aus- und Fortbildung",
        "role_id": 1497905103397457991
    },
    "SG21_PERSONAL": {
        "name": "SG21 | Personalrecht & Einstellung",
        "role_id": 1497905104181788762
    },
    "SPEZIALEINHEITEN": {
        "name": "Spezialeinheiten",
        "role_id": 1460003190656467116
    }
}

def has_allowed_role():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.manage_roles or any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
            return True
        await interaction.response.send_message("🚨 **Zugriff verweigert!** Du hast keine Berechtigung für diesen Befehl.", ephemeral=True)
        return False
    return app_commands.check(predicate)

class Abteilungen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_listen_cog(self) -> ListenCog:
        return self.bot.get_cog("ListenCog")

    # ==========================================
    # ABTEILUNGS-EINTRITT
    # ==========================================
    @app_commands.command(name="abteilungs-eintritt", description="Weist einem Mitarbeiter eine bestimmte Abteilung zu.")
    @has_allowed_role()
    @app_commands.choices(abteilung=[
        app_commands.Choice(name="SG23 | Dienstaufsicht", value="SG23_DIENSTAUFSICHT"),
        app_commands.Choice(name="SG23 | Azubi", value="SG23_AZUBI"),
        app_commands.Choice(name="SG22 | Aus- und Fortbildung", value="SG22_AUSBILDUNG"),
        app_commands.Choice(name="SG21 | Personalrecht & Einstellung", value="SG21_PERSONAL"),
        app_commands.Choice(name="Spezialeinheiten", value="SPEZIALEINHEITEN")
    ])
    async def abteilung_eintritt(self, interaction: discord.Interaction, mitarbeiter: discord.Member, abteilung: str):
        await interaction.response.defer() # Kein ephemeral mehr, damit es öffentlich gepostet wird
        
        abt_info = ABTEILUNGEN.get(abteilung)
        if not abt_info:
            await interaction.followup.send("❌ Ungültige Abteilung ausgewählt.", ephemeral=True)
            return

        role = interaction.guild.get_role(abt_info["role_id"])
        if role:
            try:
                await mitarbeiter.add_roles(role)
            except discord.Forbidden:
                await interaction.followup.send("⚠️ Konnte Rolle nicht vergeben (Fehlende Bot-Rechte).", ephemeral=True)
                return

        # In JSON speichern
        lc = self.get_listen_cog()
        u_id = str(mitarbeiter.id)
        
        if u_id not in lc.daten["mitarbeiter"]:
            lc.daten["mitarbeiter"][u_id] = {"dienstgrad": "Unbekannt", "sanktionen": []}
            
        lc.daten["mitarbeiter"][u_id]["abteilung"] = abt_info["name"]
        lc.save_data()

        # Öffentliches Bekanntmachungs-Embed
        embed = discord.Embed(
            title="🏢 Personalversetzung | Abteilungseintritt",
            color=discord.Color.green(),
            description=f"Hiermit wird die Versetzung von <@{mitarbeiter.id}> bekanntgegeben."
        )
        embed.add_field(name="Mitarbeiter", value=f"<@{mitarbeiter.id}>", inline=True)
        embed.add_field(name="Neue Abteilung", value=f"**{abt_info['name']}**", inline=True)
        embed.set_footer(text="PPD Personalabteilung", icon_url=self.bot.user.display_avatar.url if self.bot.user.display_avatar else None)

        await interaction.followup.send(content=f"<@{mitarbeiter.id}>", embed=embed)

    # ==========================================
    # ABTEILUNGS-AUSTRITT (NUR SPEZIFISCHE ABTEILUNG)
    # ==========================================
    @app_commands.command(name="abteilungs-austritt", description="Entfernt einen Mitarbeiter aus einer spezifischen Abteilung.")
    @has_allowed_role()
    @app_commands.choices(abteilung=[
        app_commands.Choice(name="SG23 | Dienstaufsicht", value="SG23_DIENSTAUFSICHT"),
        app_commands.Choice(name="SG23 | Azubi", value="SG23_AZUBI"),
        app_commands.Choice(name="SG22 | Aus- und Fortbildung", value="SG22_AUSBILDUNG"),
        app_commands.Choice(name="SG21 | Personalrecht & Einstellung", value="SG21_PERSONAL"),
        app_commands.Choice(name="Spezialeinheiten", value="SPEZIALEINHEITEN")
    ])
    async def abteilung_austritt(self, interaction: discord.Interaction, mitarbeiter: discord.Member, abteilung: str):
        await interaction.response.defer() # Öffentliche Nachricht im Kanal

        abt_info = ABTEILUNGEN.get(abteilung)
        if not abt_info:
            await interaction.followup.send("❌ Ungültige Abteilung ausgewählt.", ephemeral=True)
            return

        role = interaction.guild.get_role(abt_info["role_id"])
        hat_rolle = False

        if role and role in mitarbeiter.roles:
            try:
                await mitarbeiter.remove_roles(role)
                hat_rolle = True
            except discord.Forbidden:
                await interaction.followup.send("⚠️ Rolle konnte wegen fehlender Rechte nicht entfernt werden.", ephemeral=True)
                return

        # Aus JSON entfernen
        lc = self.get_listen_cog()
        u_id = str(mitarbeiter.id)
        if u_id in lc.daten["mitarbeiter"] and lc.daten["mitarbeiter"][u_id].get("abteilung") == abt_info["name"]:
            del lc.daten["mitarbeiter"][u_id]["abteilung"]
            lc.save_data()

        if not hat_rolle:
            await interaction.followup.send(f"⚠️ <@{mitarbeiter.id}> besitzt die Rolle für **{abt_info['name']}** gar nicht.", ephemeral=True)
            return

        # Öffentliche Bekanntmachung im Kanal
        embed = discord.Embed(
            title="🏢 Personalversetzung | Abteilungsaustritt",
            color=discord.Color.red(),
            description=f"Hiermit wird der Austritt von <@{mitarbeiter.id}> bekanntgegeben."
        )
        embed.add_field(name="Mitarbeiter", value=f"<@{mitarbeiter.id}>", inline=True)
        embed.add_field(name="Entfernte Abteilung", value=f"**{abt_info['name']}**", inline=True)
        embed.set_footer(text="PPD Personalabteilung", icon_url=self.bot.user.display_avatar.url if self.bot.user.display_avatar else None)

        await interaction.followup.send(content=f"<@{mitarbeiter.id}>", embed=embed)

async def setup(bot):
    await bot.add_cog(Abteilungen(bot))