import discord
from discord.ext import commands
from discord import app_commands
import json
import os

ALLOWED_ROLE_ID = 1497905102156206162
DATA_FILE = "dienstnummern.json"

def has_allowed_role():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.manage_roles or any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
            return True
        await interaction.response.send_message("🚨 **Zugriff verweigert!** Du hast keine Berechtigung für diesen Befehl.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# ==========================================
# MODALS & BUTTONS FÜR BENUTZER-EINGABE
# ==========================================
class DNModal(discord.ui.Modal, title="Dienstnummer beantragen / eintragen"):
    ebene = discord.ui.TextInput(
        label="Dienstebene (BHL, HD, GD, MD)",
        placeholder="z.B. GD",
        min_length=2,
        max_length=3,
        required=True
    )
    nummer = discord.ui.TextInput(
        label="Dienstnummer (Zahl)",
        placeholder="z.B. 01 oder 15",
        min_length=1,
        max_length=3,
        required=True
    )
    name = discord.ui.TextInput(
        label="Dein Name / Dienstbezeichnung",
        placeholder="z.B. A. Hupferl",
        min_length=2,
        max_length=32,
        required=True
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        ebene_val = self.ebene.value.upper().strip()
        if ebene_val not in ["BHL", "HD", "GD", "MD"]:
            await interaction.followup.send("❌ Ungültige Dienstebene! Bitte verwende **BHL**, **HD**, **GD** oder **MD**.", ephemeral=True)
            return

        try:
            num_val = int(self.nummer.value.strip())
        except ValueError:
            await interaction.followup.send("❌ Die Dienstnummer muss eine reine Zahl sein!", ephemeral=True)
            return

        u_id = str(interaction.user.id)
        self.cog.daten["nummern"][u_id] = {
            "name": self.name.value.strip(),
            "ebene": ebene_val,
            "nummer": num_val
        }
        self.cog.speichere_daten()

        # Live-Liste aktualisieren
        await self.cog.update_live_embed(interaction.guild)

        await interaction.followup.send(
            f"✅ Deine Dienstnummer **{ebene_val}-{num_val:02d}** ({self.name.value.strip()}) wurde erfolgreich eingetragen!",
            ephemeral=True
        )

class DNView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None) # Persistent View
        self.cog = cog

    @discord.ui.button(label="Dienstnummer eintragen", style=discord.ButtonStyle.primary, custom_id="dn_eintragen_btn", emoji="📝")
    async def eintragen_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DNModal(self.cog))

# ==========================================
# MAIN COG
# ==========================================
class Dienstnummern(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daten = self.lade_daten()

    def lade_daten(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    daten = json.load(f)
                    if "nummern" not in daten:
                        daten["nummern"] = {}
                    return daten
            except Exception as e:
                print(f"Fehler beim Laden von {DATA_FILE}: {e}")
        return {"channel_id": None, "list_msg_id": None, "nummern": {}}

    def speichere_daten(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.daten, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern von {DATA_FILE}: {e}")

    async def cog_load(self):
        # View beim Bot-Start registrieren, damit der Button dauerhaft funktioniert
        self.bot.add_view(DNView(self))

    async def update_live_embed(self, guild: discord.Guild):
        if not self.daten.get("channel_id") or not self.daten.get("list_msg_id"):
            return
            
        channel = guild.get_channel(self.daten["channel_id"])
        if not channel:
            return

        try:
            msg = await channel.fetch_message(self.daten["list_msg_id"])
        except (discord.NotFound, discord.Forbidden):
            return

        nummern_dict = self.daten.get("nummern", {})

        ebenen_reihenfolge = {"BHL": 0, "HD": 1, "GD": 2, "MD": 3}
        sortierte_nummern = sorted(
            nummern_dict.items(), 
            key=lambda item: (ebenen_reihenfolge.get(item[1].get("ebene", "MD"), 99), int(item[1].get("nummer", 0)))
        )
        
        embed = discord.Embed(
            title="📋 PPD | OFFIZIELLE DIENSTNUMMERNLISTE",
            color=discord.Color.from_rgb(46, 204, 113),
            description="Hier findest du alle registrierten Dienstnummern des Polizeipräsidiums Deutschland.\n\n"
        )
        
        liste_text = ""
        if sortierte_nummern:
            for u_id, info in sortierte_nummern:
                name_str = info.get("name", f"<@{u_id}>")
                ebene_str = info.get("ebene", "MD")
                num_val = int(info.get("nummer", 0))
                liste_text += f"• **{ebene_str}-{num_val:02d}** ➔ {name_str} (<@{u_id}>)\n"
        else:
            liste_text = "*Aktuell keine Dienstnummern registriert.*"

        embed.add_field(name="Registrierte Beamte", value=liste_text, inline=False)
        
        avatar_url = self.bot.user.display_avatar.url if self.bot.user and self.bot.user.display_avatar else None
        embed.set_footer(text="PPD Dienstnummernkartei • Automatische Live-Aktualisierung", icon_url=avatar_url)
        
        await msg.edit(embed=embed)

    # ==========================================
    # BEFEHL: SETUP (BUTTON PANEL & LIVE LISTE)
    # ==========================================
    @app_commands.command(name="dn-setup", description="Erstellt das Antrags-Panel und die Live-Dienstnummernliste im Kanal.")
    @has_allowed_role()
    async def dn_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        # 1. Panel-Embed mit Button senden
        panel_embed = discord.Embed(
            title="🚔 PPD | DIENSTNUMMERN BEANTRAGEN",
            description="Klicke auf den Button unten, um deine Dienstnummer in das System einzutragen oder zu aktualisieren.",
            color=discord.Color.blue()
        )
        await channel.send(embed=panel_embed, view=DNView(self))

        # 2. Live-Listen-Embed senden und IDs speichern
        list_embed = discord.Embed(
            title="📋 PPD | OFFIZIELLE DIENSTNUMMERNLISTE", 
            description="*Wird initialisiert...*", 
            color=discord.Color.from_rgb(46, 204, 113)
        )
        list_msg = await channel.send(embed=list_embed)
        
        self.daten["channel_id"] = channel.id
        self.daten["list_msg_id"] = list_msg.id
        self.speichere_daten()

        try:
            await self.update_live_embed(interaction.guild)
        except Exception as e:
            print(f"Fehler beim Initialisieren des Live-Embeds: {e}")

        await interaction.followup.send("✅ Dienstnummern-Setup erfolgreich eingerichtet!", ephemeral=True)

    # ==========================================
    # BEFEHL: ADMIN MANAGEMENT
    # ==========================================
    @app_commands.command(name="dn-admin", description="Verwalte Dienstnummern von Mitgliedern (Hinzufügen / Entfernen).")
    @has_allowed_role()
    @app_commands.choices(aktion=[
        app_commands.Choice(name="Hinzufügen / Bearbeiten", value="add"),
        app_commands.Choice(name="Löschen / Entfernen", value="remove")
    ])
    @app_commands.choices(ebene=[
        app_commands.Choice(name="Behördenleitung (BHL)", value="BHL"),
        app_commands.Choice(name="Höherer Dienst (HD)", value="HD"),
        app_commands.Choice(name="Gehobener Dienst (GD)", value="GD"),
        app_commands.Choice(name="Mittlerer Dienst (MD)", value="MD")
    ])
    async def dn_admin(
        self, 
        interaction: discord.Interaction, 
        aktion: str, 
        mitarbeiter: discord.Member, 
        ebene: str = None, 
        nummer: int = None, 
        name: str = None
    ):
        await interaction.response.defer(ephemeral=True)
        u_id = str(mitarbeiter.id)

        if aktion == "add":
            if not ebene or nummer is None or not name:
                await interaction.followup.send("❌ Zum Hinzufügen musst du **Ebene**, **Nummer** und **Name** angeben!", ephemeral=True)
                return

            self.daten["nummern"][u_id] = {
                "name": name,
                "ebene": ebene,
                "nummer": nummer
            }
            self.speichere_daten()
            await self.update_live_embed(interaction.guild)

            await interaction.followup.send(
                f"✅ Dienstnummer für <@{mitarbeiter.id}> eingetragen: **{ebene}-{nummer:02d}** ({name})",
                ephemeral=True
            )

        elif aktion == "remove":
            if u_id in self.daten["nummern"]:
                entfernt = self.daten["nummern"].pop(u_id)
                self.speichere_daten()
                await self.update_live_embed(interaction.guild)

                await interaction.followup.send(
                    f"🗑️ Dienstnummer von <@{mitarbeiter.id}> (**{entfernt.get('ebene')}-{entfernt.get('nummer'):02d}**) wurde gelöscht.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("⚠️ Dieser Beamte hat keine eingetragene Dienstnummer.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Dienstnummern(bot))