import discord
from discord.ext import commands
from discord import app_commands
import json
import os

ALLOWED_ROLE_ID = 1497905102156206162
DATA_FILE = "dienstnummern_data.json"

def has_allowed_role():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.manage_roles or any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
            return True
        await interaction.response.send_message("🚨 **Zugriff verweigert!** Nur die Behördenleitung darf dieses Panel bedienen.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# ==========================================
# MODAL FÜR DIENSTNUMMERN-EINGABE
# ==========================================
class DNAntragModal(discord.ui.Modal, title="Dienstnummer beantragen"):
    nummer_input = discord.ui.TextInput(
        label="Gewünschte Dienstnummer", 
        placeholder="Z.B. 23", 
        min_length=1, 
        max_length=4
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            dn = int(self.nummer_input.value)
        except ValueError:
            await interaction.followup.send("❌ Bitte gib eine gültige Zahl ein!", ephemeral=True)
            return

        u_id = str(interaction.user.id)
        
        # Prüfen, ob der User schon eine Nummer hat
        if u_id in self.cog.daten["nummern"]:
            await interaction.followup.send(f"❌ Du hast bereits die Dienstnummer **{self.cog.daten['nummern'][u_id]}** registriert!", ephemeral=True)
            return

        # Prüfen, ob die Nummer schon vergeben ist
        if dn in self.cog.daten["nummern"].values():
            await interaction.followup.send(f"❌ Die Dienstnummer **{dn}** ist bereits vergeben! Bitte wähle eine andere.", ephemeral=True)
            return

        # Speichern & Live-Liste updaten
        self.cog.daten["nummern"][u_id] = dn
        self.cog.speichere_daten()
        
        await self.cog.update_live_embed(interaction.guild)
        await interaction.followup.send(f"✅ Deine Dienstnummer **{dn}** wurde erfolgreich eingetragen und der Liste hinzugefügt!", ephemeral=True)

class DNAdminModal(discord.ui.Modal, title="Mitarbeiter-DN bearbeiten"):
    mitarbeiter_id = discord.ui.TextInput(label="User-ID des Mitarbeiters", placeholder="Z.B. 123456789012345678")
    neue_dn = discord.ui.TextInput(label="Neue Dienstnummer (Leerlassen zum Löschen)", required=False, placeholder="Z.B. 45 oder leer")

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        u_id = self.mitarbeiter_id.value.strip()
        dn_val = self.neue_dn.value.strip()

        if not dn_val:
            # Löschen
            if u_id in self.cog.daten["nummern"]:
                del self.cog.daten["nummern"][u_id]
                self.cog.speichere_daten()
                await self.cog.update_live_embed(interaction.guild)
                await interaction.followup.send("❌ Dienstnummer erfolgreich gelöscht.", ephemeral=True)
            else:
                await interaction.followup.send("ℹ️ Dieser User hatte keine Dienstnummer.", ephemeral=True)
        else:
            # Bearbeiten / Hinzufügen
            try:
                dn = int(dn_val)
            except ValueError:
                await interaction.followup.send("❌ Ungültige Dienstnummer.", ephemeral=True)
                return

            self.cog.daten["nummern"][u_id] = dn
            self.cog.speichere_daten()
            await self.cog.update_live_embed(interaction.guild)
            await interaction.followup.send(f"✅ Dienstnummer für <@{u_id}> auf **{dn}** gesetzt.", ephemeral=True)

# ==========================================
# VIEWS (BUTTON PANELS)
# ==========================================
class DNUserView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Beantragen", style=discord.ButtonStyle.blurple, custom_id="dn_beantragen_btn")
    async def beantragen(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DNAntragModal(self.cog))

class DNAdminView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="⚙️ DN Bearbeiten / Löschen", style=discord.ButtonStyle.danger, custom_id="dn_admin_edit_btn")
    async def admin_edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (interaction.user.guild_permissions.manage_roles or any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles)):
            await interaction.response.send_message("🚨 Keine Rechte!", ephemeral=True)
            return
        await interaction.response.send_modal(DNAdminModal(self.cog))

# ==========================================
# COG CLASS
# ==========================================
class DienstnummernCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daten = {"channel_id": None, "list_msg_id": None, "nummern": {}}
        self.lade_daten()

    def lade_daten(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                self.daten = json.load(f)
        else:
            self.speichere_daten()

    def speichere_daten(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.daten, f, indent=4, ensure_utf_8=False)

    async def cog_load(self):
        # Sorgt dafür, dass die Buttons auch nach einem Bot-Neustart funktionieren
        self.bot.add_view(DNUserView(self))
        self.bot.add_view(DNAdminView(self))

    async def update_live_embed(self, guild: discord.Guild):
        if not self.daten["channel_id"] or not self.daten["list_msg_id"]:
            return
            
        channel = guild.get_channel(self.daten["channel_id"])
        if not channel:
            return

        try:
            msg = await channel.fetch_message(self.daten["list_msg_id"])
        except discord.NotFound:
            return

        # Sortieren nach Dienstnummer
        sortierte_nummern = sorted(self.daten["nummern"].items(), key=lambda item: item[1])
        
        embed = discord.Embed(
            title="📋 PPD | OFFIZIELLE DIENSTNUMMERNLISTE",
            color=discord.Color.from_rgb(46, 204, 113),
            description="Hier findest du alle registrierten Dienstnummern der Behörde.\n\n"
        )
        
        liste_text = ""
        if sortierte_nummern:
            for u_id, dn in sortierte_nummern:
                liste_text += f"• **DN {dn:02d}** ➔ <@{u_id}>\n"
        else:
            liste_text = "*Aktuell keine Nummern vergeben.*"

        embed.add_field(name="Registrierte Beamte", value=liste_text, inline=False)
        embed.set_footer(text="Automatische Live-Aktualisierung", icon_url=self.bot.user.display_avatar.url)
        
        await msg.edit(embed=embed)

    @app_commands.command(name="dn-setup", description="Richtet das Dienstnummern-System in diesem Kanal ein.")
    @has_allowed_role()
    async def dn_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        # 1. Das User-Antrag-Panel senden
        user_embed = discord.Embed(
            title="Dienstnummer beantragen",
            description="Klicke auf den Button, um deine persönliche Dienstnummer zu generieren.",
            color=discord.Color.blue()
        )
        user_embed.set_footer(text="NovaRP")
        await channel.send(embed=user_embed, view=DNUserView(self))

        # 2. Die Live-Liste senden und ID speichern
        list_embed = discord.Embed(title="📋 PPD | OFFIZIELLE DIENSTNUMMERNLISTE", description="*Wird geladen...*", color=discord.Color.green())
        list_msg = await channel.send(embed=list_embed)
        
        # 3. Das Admin-Panel (nur für die BHL sichtbar über Ephemeral oder hier als permanenter Button für Admins)
        admin_embed = discord.Embed(
            title="💼 Behördenleitung | Administration",
            description="Nutze diesen Button, um Nummern von Mitarbeitern manuell anzupassen oder zu löschen.",
            color=discord.Color.red()
        )
        await channel.send(embed=admin_embed, view=DNAdminView(self))

        # Konfiguration abspeichern
        self.daten["channel_id"] = channel.id
        self.daten["list_msg_id"] = list_msg.id
        self.speichere_daten()

        # Direkt das erste Mal befüllen
        await self.update_live_embed(interaction.guild)
        await interaction.followup.send("✅ System erfolgreich in diesem Kanal eingerichtet!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(DienstnummernCog(bot))