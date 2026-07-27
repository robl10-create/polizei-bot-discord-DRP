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
# MODAL FÜR MITGLIEDER (FORMULAR)
# ==========================================
class DNModal(discord.ui.Modal, title="Dienstnummer eintragen"):
    ebene = discord.ui.TextInput(
        label="Dienstebene (BHL, HD, GD, MD)",
        placeholder="Gib BHL, HD, GD oder MD ein",
        min_length=2,
        max_length=3,
        required=True
    )
    nummer = discord.ui.TextInput(
        label="Dienstnummer (nur die Zahl)",
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
        ebenen_mapping = ["BHL", "HD", "GD", "MD"]

        if ebene_val not in ebenen_mapping:
            await interaction.followup.send("❌ Ungültige Dienstebene! Bitte verwende **BHL**, **HD**, **GD** oder **MD**.", ephemeral=True)
            return

        try:
            num_val = int(self.nummer.value.strip())
        except ValueError:
            await interaction.followup.send("❌ Die Dienstnummer muss eine gültige Zahl sein!", ephemeral=True)
            return

        u_id = str(interaction.user.id)
        self.cog.daten["nummern"][u_id] = {
            "name": self.name.value.strip(),
            "ebene": ebene_val,
            "nummer": num_val
        }
        self.cog.speichere_daten()

        # Live-Liste im Kanal aktualisieren
        await self.cog.update_live_embed(interaction.guild)

        await interaction.followup.send(
            f"✅ Deine Dienstnummer **{ebene_val}-{num_val:02d}** ({self.name.value.strip()}) wurde erfolgreich eingetragen!",
            ephemeral=True
        )

# ==========================================
# BUTTON VIEW FÜR ANTRAGS-PANEL
# ==========================================
class DNView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None) # Dauerhafte View
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
    # 1. BEFEHL: /dn-setup (NUR DAS ANTRAGS-PANEL)
    # ==========================================
    @app_commands.command(name="dn-setup", description="Erstellt das Antrags-Panel mit Button im Kanal.")
    @has_allowed_role()
    async def dn_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        panel_embed = discord.Embed(
            title="🚔 PPD | DIENSTNUMMERN BEANTRAGEN",
            description="Klicke auf den Button unten, um deine Dienstnummer einzutragen oder zu bearbeiten.",
            color=discord.Color.blue()
        )
        await interaction.channel.send(embed=panel_embed, view=DNView(self))
        await interaction.followup.send("✅ Antrags-Panel wurde erstellt!", ephemeral=True)

    # ==========================================
    # 2. BEFEHL: /dn-liste (NUR DIE LIVE-LISTE)
    # ==========================================
    @app_commands.command(name="dn-liste", description="Erstellt die permanente Live-Dienstnummernliste im Kanal.")
    @has_allowed_role()
    async def dn_liste(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

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
            print(f"Fehler beim Initialisieren der Liste: {e}")

        await interaction.followup.send("✅ Live-Dienstnummernliste wurde verankert!", ephemeral=True)

    # ==========================================
    # 3. BEFEHL: /dn-admin (ADMIN-VERWALTUNG)
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
                await interaction.followup.send("❌ Zum Hinzufügen musst du **Ebene** (Laufbahn), **Nummer** und **Name** angeben!", ephemeral=True)
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