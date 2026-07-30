import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import datetime
import traceback

# ==========================================
# DEBUG-PRINT SETUP
# ==========================================
DEBUG = True  # auf False stellen, um alle [DEBUG]-Ausgaben abzuschalten

def _ts():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def debug(msg):
    if DEBUG:
        print(f"[{_ts()}] [DEBUG] {msg}")

def info(msg):
    print(f"[{_ts()}] [INFO] {msg}")

def warn(msg):
    print(f"[{_ts()}] [WARNUNG] {msg}")

def error(msg):
    print(f"[{_ts()}] [FEHLER] {msg}")

ALLOWED_ROLE_ID = 1497905102156206162
DATA_FILE = "dienstnummern.json"

def has_allowed_role():
    async def predicate(interaction: discord.Interaction) -> bool:
        has_perm = interaction.user.guild_permissions.manage_roles
        has_role = any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles)
        debug(
            f"Berechtigungsprüfung für {interaction.user} (ID: {interaction.user.id}) "
            f"-> manage_roles={has_perm}, hat_rolle={has_role}"
        )
        if has_perm or has_role:
            return True
        warn(
            f"Zugriff verweigert für {interaction.user} (ID: {interaction.user.id}) "
            f"bei Befehl '{interaction.command.name if interaction.command else 'unbekannt'}'"
        )
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
        debug(
            f"Modal übermittelt von {interaction.user} (ID: {interaction.user.id}): "
            f"ebene='{self.ebene.value}', nummer='{self.nummer.value}', name='{self.name.value}'"
        )
        await interaction.response.defer(ephemeral=True)

        ebene_val = self.ebene.value.upper().strip()
        ebenen_mapping = ["BHL", "HD", "GD", "MD"]

        if ebene_val not in ebenen_mapping:
            debug(f"Ungültige Ebene '{ebene_val}' von {interaction.user}")
            await interaction.followup.send("❌ Ungültige Dienstebene! Bitte verwende **BHL**, **HD**, **GD** oder **MD**.", ephemeral=True)
            return

        try:
            num_val = int(self.nummer.value.strip())
        except ValueError:
            debug(f"Ungültige Nummer '{self.nummer.value}' von {interaction.user}")
            await interaction.followup.send("❌ Die Dienstnummer muss eine gültige Zahl sein!", ephemeral=True)
            return

        u_id = str(interaction.user.id)
        self.cog.daten["nummern"][u_id] = {
            "name": self.name.value.strip(),
            "ebene": ebene_val,
            "nummer": num_val
        }
        self.cog.speichere_daten()
        info(
            f"Dienstnummer eingetragen (per Modal): {interaction.user} (ID: {u_id}) "
            f"-> {ebene_val}-{num_val:02d} ({self.name.value.strip()})"
        )

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
        debug(f"Button 'Dienstnummer eintragen' geklickt von {interaction.user} (ID: {interaction.user.id})")
        await interaction.response.send_modal(DNModal(self.cog))

# ==========================================
# MAIN COG
# ==========================================
class Dienstnummern(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        debug("Initialisiere Dienstnummern-Cog...")
        self.daten = self.lade_daten()
        info(f"Cog initialisiert. {len(self.daten.get('nummern', {}))} Dienstnummer(n) geladen.")

    def lade_daten(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    daten = json.load(f)
                    if "nummern" not in daten:
                        daten["nummern"] = {}
                    debug(f"Daten erfolgreich aus '{DATA_FILE}' geladen: {daten}")
                    return daten
            except Exception as e:
                error(f"Fehler beim Laden von {DATA_FILE}: {e}")
                debug(traceback.format_exc())
        else:
            warn(f"'{DATA_FILE}' existiert nicht. Starte mit leeren Daten.")
        return {"channel_id": None, "list_msg_id": None, "nummern": {}}

    def speichere_daten(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.daten, f, indent=4, ensure_ascii=False)
            debug(f"Daten erfolgreich in '{DATA_FILE}' gespeichert.")
        except Exception as e:
            error(f"Fehler beim Speichern von {DATA_FILE}: {e}")
            debug(traceback.format_exc())

    async def cog_load(self):
        debug("cog_load() aufgerufen - registriere persistente View (DNView).")
        self.bot.add_view(DNView(self))

    async def update_live_embed(self, guild: discord.Guild):
        debug(f"update_live_embed() aufgerufen für Guild '{guild.name}' (ID: {guild.id})")

        if not self.daten.get("channel_id") or not self.daten.get("list_msg_id"):
            debug("Kein channel_id/list_msg_id gesetzt - Live-Liste wird nicht aktualisiert.")
            return

        channel = guild.get_channel(self.daten["channel_id"])
        if not channel:
            warn(f"Kanal mit ID {self.daten['channel_id']} nicht gefunden.")
            return

        try:
            msg = await channel.fetch_message(self.daten["list_msg_id"])
        except discord.NotFound:
            error(f"Nachricht mit ID {self.daten['list_msg_id']} nicht gefunden (evtl. gelöscht).")
            return
        except discord.Forbidden:
            error(f"Keine Berechtigung, Nachricht {self.daten['list_msg_id']} in Kanal {channel.id} zu bearbeiten.")
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
        
        try:
            await msg.edit(embed=embed)
            debug(f"Live-Embed erfolgreich aktualisiert ({len(sortierte_nummern)} Einträge).")
        except Exception as e:
            error(f"Fehler beim Bearbeiten der Live-Liste: {e}")
            debug(traceback.format_exc())

    # ==========================================
    # 1. BEFEHL: /dn-setup (NUR DAS ANTRAGS-PANEL)
    # ==========================================
    @app_commands.command(name="dn-setup", description="Erstellt das Antrags-Panel mit Button im Kanal.")
    @has_allowed_role()
    async def dn_setup(self, interaction: discord.Interaction):
        info(f"/dn-setup aufgerufen von {interaction.user} (ID: {interaction.user.id}) in Kanal {interaction.channel_id}")
        await interaction.response.defer(ephemeral=True)

        panel_embed = discord.Embed(
            title="🚔 PPD | DIENSTNUMMERN BEANTRAGEN",
            description="Klicke auf den Button unten, um deine Dienstnummer einzutragen oder zu bearbeiten.",
            color=discord.Color.blue()
        )
        await interaction.channel.send(embed=panel_embed, view=DNView(self))
        debug("Antrags-Panel erfolgreich gesendet.")
        await interaction.followup.send("✅ Antrags-Panel wurde erstellt!", ephemeral=True)

    # ==========================================
    # 2. BEFEHL: /dn-liste (NUR DIE LIVE-LISTE)
    # ==========================================
    @app_commands.command(name="dn-liste", description="Erstellt die permanente Live-Dienstnummernliste im Kanal.")
    @has_allowed_role()
    async def dn_liste(self, interaction: discord.Interaction):
        info(f"/dn-liste aufgerufen von {interaction.user} (ID: {interaction.user.id}) in Kanal {interaction.channel_id}")
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        list_embed = discord.Embed(
            title="📋 PPD | OFFIZIELLE DIENSTNUMMERNLISTE", 
            description="*Wird initialisiert...*", 
            color=discord.Color.from_rgb(46, 204, 113)
        )
        list_msg = await channel.send(embed=list_embed)
        debug(f"Neue Live-Listen-Nachricht erstellt mit ID {list_msg.id} in Kanal {channel.id}")
        
        self.daten["channel_id"] = channel.id
        self.daten["list_msg_id"] = list_msg.id
        self.speichere_daten()

        try:
            await self.update_live_embed(interaction.guild)
        except Exception as e:
            error(f"Fehler beim Initialisieren der Liste: {e}")
            debug(traceback.format_exc())

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
        info(
            f"/dn-admin aufgerufen von {interaction.user} (ID: {interaction.user.id}) "
            f"-> aktion='{aktion}', ziel={mitarbeiter} (ID: {mitarbeiter.id}), ebene={ebene}, nummer={nummer}, name={name}"
        )
        await interaction.response.defer(ephemeral=True)
        u_id = str(mitarbeiter.id)

        if aktion == "add":
            if not ebene or nummer is None or not name:
                debug("Add-Aktion abgebrochen: fehlende Parameter (ebene/nummer/name).")
                await interaction.followup.send("❌ Zum Hinzufügen musst du **Ebene** (Laufbahn), **Nummer** und **Name** angeben!", ephemeral=True)
                return

            self.daten["nummern"][u_id] = {
                "name": name,
                "ebene": ebene,
                "nummer": nummer
            }
            self.speichere_daten()
            info(f"Dienstnummer per Admin gesetzt: {mitarbeiter} (ID: {u_id}) -> {ebene}-{nummer:02d} ({name})")
            await self.update_live_embed(interaction.guild)

            await interaction.followup.send(
                f"✅ Dienstnummer für <@{mitarbeiter.id}> eingetragen: **{ebene}-{nummer:02d}** ({name})",
                ephemeral=True
            )

        elif aktion == "remove":
            if u_id in self.daten["nummern"]:
                entfernt = self.daten["nummern"].pop(u_id)
                self.speichere_daten()
                info(f"Dienstnummer entfernt: {mitarbeiter} (ID: {u_id}) -> war {entfernt.get('ebene')}-{entfernt.get('nummer')}")
                await self.update_live_embed(interaction.guild)

                await interaction.followup.send(
                    f"🗑️ Dienstnummer von <@{mitarbeiter.id}> (**{entfernt.get('ebene')}-{entfernt.get('nummer'):02d}**) wurde gelöscht.",
                    ephemeral=True
                )
            else:
                debug(f"Remove-Aktion: {mitarbeiter} (ID: {u_id}) hatte keine Dienstnummer.")
                await interaction.followup.send("⚠️ Dieser Beamte hat keine eingetragene Dienstnummer.", ephemeral=True)

async def setup(bot):
    debug("setup() aufgerufen - füge Cog zum Bot hinzu.")
    await bot.add_cog(Dienstnummern(bot))