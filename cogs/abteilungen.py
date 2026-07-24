import discord
from discord.ext import commands
from discord import app_commands
from cogs.listen import ListenCog

ALLOWED_ROLE_ID = 1497905102156206162

# Hier sind alle deine Abteilungen mit den exakten Rollen-IDs verknüpft:
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
    @app_commands.command(name="abteilungs-eintritt", description="Weist einem Mitarbeiter eine Abteilung zu und vergibt die Rolle.")
    @has_allowed_role()
    @app_commands.choices(abteilung=[
        app_commands.Choice(name="SG23 | Dienstaufsicht", value="SG23_DIENSTAUFSICHT"),
        app_commands.Choice(name="SG23 | Azubi", value="SG23_AZUBI"),
        app_commands.Choice(name="SG22 | Aus- und Fortbildung", value="SG22_AUSBILDUNG"),
        app_commands.Choice(name="SG21 | Personalrecht & Einstellung", value="SG21_PERSONAL"),
        app_commands.Choice(name="Spezialeinheiten", value="SPEZIALEINHEITEN")
    ])
    async def abteilung_eintritt(self, interaction: discord.Interaction, mitarbeiter: discord.Member, abteilung: str):
        await interaction.response.defer(ephemeral=True)
        
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

        await interaction.followup.send(f"✅ <@{mitarbeiter.id}> wurde erfolgreich der Abteilung **{abt_info['name']}** zugewiesen und hat die Rolle erhalten.", ephemeral=True)

    # ==========================================
    # ABTEILUNGS-AUSTRITT (BEHEBT DEN FEHLER VOM BILD)
    # ==========================================
    @app_commands.command(name="abteilungs-austritt", description="Entfernt einen Mitarbeiter aus seiner Abteilung.")
    @has_allowed_role()
    async def abteilung_austritt(self, interaction: discord.Interaction, mitarbeiter: discord.Member):
        await interaction.response.defer(ephemeral=True)
        lc = self.get_listen_cog()
        u_id = str(mitarbeiter.id)

        # 1. Prüfen, welche Abteilungs-Rollen der User aktuell hat und entfernen
        entfernte_rollen = []
        for key, abt_info in ABTEILUNGEN.items():
            role = interaction.guild.get_role(abt_info["role_id"])
            if role and role in mitarbeiter.roles:
                try:
                    await mitarbeiter.remove_roles(role)
                    entfernte_rollen.append(abt_info["name"])
                except discord.Forbidden:
                    pass

        # 2. Aus JSON austragen
        hat_json_eintrag = False
        if u_id in lc.daten["mitarbeiter"] and "abteilung" in lc.daten["mitarbeiter"][u_id]:
            del lc.daten["mitarbeiter"][u_id]["abteilung"]
            lc.save_data()
            hat_json_eintrag = True

        # Wenn er weder Rollen noch einen JSON-Eintrag hatte:
        if not entfernte_rollen and not hat_json_eintrag:
            await interaction.followup.send("⚠️ Dieser Mitarbeiter besitzt keine der registrierten Abteilungs-Rollen und war in keiner Abteilung eingetragen.", ephemeral=True)
            return

        msg = f"✅ <@{mitarbeiter.id}> wurde aus der Abteilung entfernt."
        if entfernte_rollen:
            msg += f"\n➔ Rolle(n) entfernt: **{', '.join(entfernte_rollen)}**"
            
        await interaction.followup.send(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Abteilungen(bot))