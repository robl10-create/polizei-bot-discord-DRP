import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import re

ALLOWED_ROLE_ID = 1497905102156206162
DATA_FILE = "dienstnummern_data.json"

def has_allowed_role():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.manage_roles or any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
            return True
        await interaction.response.send_message("🚨 **Zugriff verweigert!** Nur die Behördenleitung darf diesen Befehl ausführen.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# Helper-Funktion um den Nickname nach Vorlage anzupassen
async def update_member_nickname(member: discord.Member, ebene: str, dn: int, ic_name: str):
    dn_str = f"{ebene}-{dn:02d}"
    
    # Validiere/Formatiere den Namen zu "M. Mustermann" falls der User es voll ausgeschrieben hat
    name_parts = ic_name.strip().split(" ")
    if len(name_parts) >= 2 and not name_parts[0].endswith("."):
        formatiert_name = f"{name_parts[0][0]}. {' '.join(name_parts[1:])}"
    else:
        formatiert_name = ic_name.strip()

    # Wir prüfen den aktuellen Namen, um bestehende Ränge ("B2 »") oder Zusätze ("| AL-DA") zu erhalten
    current_nick = member.display_name
    
    # Standard-Struktur falls kein altes Muster erkannt wird
    # Muster versucht ein bestehendes "RANG » " und ein hinteres " | ZUSATZ" zu matchen
    prefix = ""
    suffix = ""
    
    if "»" in current_nick:
        prefix = current_nick.split("»")[0].strip() + " » "
        rest = current_nick.split("»")[1]
    else:
        rest = current_nick

    # Falls am Ende noch Zusätze stehen (z.B. nach dem zweiten oder letzten Rohr '|')
    if rest.count("|") >= 2:
        parts = rest.split("|")
        suffix = " | " + parts[-1].strip()

    # Finaler Nickname nach der PPD-Vorlage aus dem Bild
    new_nick = f"{prefix}{formatiert_name} | {dn_str}{suffix}"
    
    # Begrenzung von Discord beachten (max 32 Zeichen)
    if len(new_nick) > 32:
        new_nick = f"{prefix}{formatiert_name} | {dn_str}"[:32]

    try:
        await member.edit(nick=new_nick)
        return f"Nickname erfolgreich geändert zu: `{new_nick}`"
    except discord.Forbidden:
        return "⚠️ Nickname konnte nicht geändert werden (Bot-Hierarchie zu niedrig oder Server-Besitzer)."

# ==========================================
# MODAL FÜR DIENSTNUMMERN-ANTRAG
# ==========================================
class DNAntragModal(discord.ui.Modal, title="Dienstnummer beantragen"):
    ic_name_input = discord.ui.TextInput(
        label="Dein IC Name (Format: M. Mustermann)", 
        placeholder="Z.B. T. Baum", 
        min_length=3, 
        max_length=20
    )
    nummer_input = discord.ui.TextInput(
        label="Gewünschte Dienstnummer (Zahl)", 
        placeholder="Z.B. 20", 
        min_length=1, 
        max_length=3
    )

    def __init__(self, cog, ebene: str):
        super().__init__()
        self.cog = cog
        self.ebene = ebene

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            dn = int(self.nummer_input.value)
        except ValueError:
            await interaction.followup.send("❌ Bitte gib eine gültige Zahl als Dienstnummer ein!", ephemeral=True)
            return

        u_id = str(interaction.user.id)
        
        if u_id in self.cog.daten["nummern"]:
            alte_ebene = self.cog.daten["nummern"][u_id]["ebene"]
            alte_dn = self.cog.daten["nummern"][u_id]["nummer"]
            await interaction.followup.send(f"❌ Du hast bereits eine Dienstnummer: **{alte_ebene}-{alte_dn:02d}**!", ephemeral=True)
            return

        for daten in self.cog.daten["nummern"].values():
            if daten["ebene"] == self.ebene and daten["nummer"] == dn:
                await interaction.followup.send(f"❌ Die Dienstnummer **{self.ebene}-{dn:02d}** ist bereits vergeben!", ephemeral=True)
                return

        # Speichern
        self.cog.daten["nummern"][u_id] = {
            "ebene": self.ebene,
            "nummer": dn,
            "name": self.ic_name_input.value.strip()
        }
        self.cog.speichere_daten()
        
        # Nickname-Änderung triggern
        nick_msg = await update_member_nickname(interaction.user, self.ebene, dn, self.ic_name_input.value)
        
        await self.cog.update_live_embed(interaction.guild)
        await interaction.followup.send(f"✅ Deine Dienstnummer **{self.ebene}-{dn:02d}** wurde registriert!\n➔ {nick_msg}", ephemeral=True)

class DNEbenenSelect(discord.ui.Select):
    def __init__(self, cog):
        options = [
            discord.SelectOption(label="🛡️ Mittlerer Dienst (MD)", value="MD"),
            discord.SelectOption(label="⭐ Gehobener Dienst (GD)", value="GD"),
            discord.SelectOption(label="🦅 Höherer Dienst (HD)", value="HD"),
            discord.SelectOption(label="💼 Behördenleitung (BHL)", value="BHL"),
        ]
        super().__init__(placeholder="Wähle deine Dienstebene aus...", options=options)
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DNAntragModal(self.cog, self.values[0]))

class DNUserView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Beantragen", style=discord.ButtonStyle.blurple, custom_id="dn_beantragen_btn")
    async def beantragen(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View()
        view.add_item(DNEbenenSelect(self.cog))
        await interaction.response.send_message("Bitte wähle deine **Dienstebene**:", view=view, ephemeral=True)

# ==========================================
# COG CLASS
# ==========================================
class Dienstnummern(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daten = {"channel_id": None, "list_msg_id": None, "nummern": {}}
        self.lade_daten()

    def lade_daten(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                try:
                    self.daten = json.load(f)
                except json.JSONDecodeError:
                    self.speichere_daten()
        else:
            self.speichere_daten()

    def speichere_daten(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.daten, f, indent=4, ensure_ascii=False)

    async def cog_load(self):
        self.bot.add_view(DNUserView(self))

    async def update_live_embed(self, guild: discord.Guild):
        if not self.daten.get("channel_id") or not self.daten.get("list_msg_id"):
            return
        channel = guild.get_channel(self.daten["channel_id"])
        if not channel: return

        try:
            msg = await channel.fetch_message(self.daten["list_msg_id"])
        except (discord.NotFound, discord.Forbidden): return

        ebenen_reihenfolge = {"BHL": 0, "HD": 1, "GD": 2, "MD": 3}
        sortierte_nummern = sorted(
            self.daten["nummern"].items(), 
            key=lambda item: (ebenen_reihenfolge.get(item[1]["ebene"], 99), item[1]["nummer"])
        )
        
        embed = discord.Embed(
            title="📋 PPD | OFFIZIELLE DIENSTNUMMERNLISTE",
            color=discord.Color.from_rgb(46, 204, 113),
            description="Hier findest du alle registrierten Dienstnummern nach Dienstebene sortiert.\n\n"
        )
        
        liste_text = ""
        if sortierte_nummern:
            for u_id, info in sortierte_nummern:
                name_str = info.get("name", f"<@{u_id}>")
                liste_text += f"• **{info['ebene']}-{info['nummer']:02d}** ➔ {name_str} (<@{u_id}>)\n"
        else:
            liste_text = "*Aktuell keine Nummern vergeben.*"

        embed.add_field(name="Registrierte Beamte", value=liste_text, inline=False)
        embed.set_footer(text="Automatische Live-Aktualisierung", icon_url=self.bot.user.display_avatar.url if self.bot.user.display_avatar else None)
        await msg.edit(embed=embed)

    # ==========================================
    # COMMANDS
    # ==========================================
    @app_commands.command(name="dn-setup", description="Sendet das interaktive Beantragungs-Panel in diesen Kanal.")
    @has_allowed_role()
    async def dn_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        user_embed = discord.Embed(
            title="Dienstnummer beantragen",
            description="Klicke auf den Button, um deine persönliche Dienstnummer zu generieren.\nDein Nickname wird dabei automatisch angepasst.",
            color=discord.Color.blue()
        )
        user_embed.set_footer(text="NovaRP")
        await channel.send(embed=user_embed, view=DNUserView(self))
        await interaction.followup.send("✅ Beantragungs-Panel wurde gesendet!", ephemeral=True)

    @app_commands.command(name="dn-liste", description="Erstellt die permanente Live-Dienstnummernliste in diesem Kanal.")
    @has_allowed_role()
    async def dn_liste(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        list_embed = discord.Embed(title="📋 PPD | OFFIZIELLE DIENSTNUMMERNLISTE", description="*Wird initialisiert...*", color=discord.Color.green())
        list_msg = await channel.send(embed=list_embed)
        
        self.daten["channel_id"] = channel.id
        self.daten["list_msg_id"] = list_msg.id
        self.speichere_daten()

        await self.update_live_embed(interaction.guild)
        await interaction.followup.send("✅ Live-Liste hier verankert und mit JSON verknüpft!", ephemeral=True)

    @app_commands.command(name="dn-admin", description="Ermöglicht der Behördenleitung das manuelle Verwalten einer Dienstnummer.")
    @app_commands.choices(aktion=[
        app_commands.Choice(name="➕ Zuweisen / Ändern", value="set"),
        app_commands.Choice(name="❌ Löschen", value="delete")
    ])
    @app_commands.choices(ebene=[
        app_commands.Choice(name="🛡️ MD", value="MD"),
        app_commands.Choice(name="⭐ GD", value="GD"),
        app_commands.Choice(name="🦅 HD", value="HD"),
        app_commands.Choice(name="💼 BHL", value="BHL")
    ])
    @has_allowed_role()
    async def dn_admin(
        self, 
        interaction: discord.Interaction, 
        aktion: str, 
        mitarbeiter: discord.Member, 
        ebene: str = None, 
        nummer: int = None,
        ic_name: str = None
    ):
        await interaction.response.defer(ephemeral=True)
        u_id = str(mitarbeiter.id)

        if aktion == "delete":
            if u_id in self.daten["nummern"]:
                del self.daten["nummern"][u_id]
                self.speichere_daten()
                await self.update_live_embed(interaction.guild)
                await interaction.followup.send(f"❌ Dienstnummer von <@{u_id}> gelöscht. Bitte passe seinen Nickname manuell an.", ephemeral=True)
            else:
                await interaction.followup.send("ℹ️ Dieser Mitarbeiter hatte keine Nummer eingetragen.", ephemeral=True)
        
        elif aktion == "set":
            if not ebene or nummer is None or not ic_name:
                await interaction.followup.send("❌ Für das Zuweisen musst du Ebene, Nummer und IC-Name angeben!", ephemeral=True)
                return

            self.daten["nummern"][u_id] = {
                "ebene": ebene,
                "nummer": nummer,
                "name": ic_name.strip()
            }
            self.speichere_daten()
            
            nick_msg = await update_member_nickname(mitarbeiter, ebene, nummer, ic_name)
            await self.update_live_embed(interaction.guild)
            await interaction.followup.send(f"✅ Mitarbeiter auf **{ebene}-{nummer:02d}** gesetzt.\n➔ {nick_msg}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Dienstnummern(bot))