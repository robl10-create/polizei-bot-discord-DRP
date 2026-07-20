import discord
from discord.ext import commands
from discord import app_commands

# ID der erlaubten Dienstaufsichts-Rolle
ALLOWED_ROLE_ID = 1497905102156206162

def has_allowed_role():
    """Checkt, ob der User die manage_roles Berechtigung ODER die spezifische Rolle hat."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.manage_roles:
            return True
        
        if any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
            return True
            
        await interaction.response.send_message(
            "🚨 **Zugriff verweigert!** Du benötigst die Rolle **SG23 | Dienstaufsicht** oder die Berechtigung 'Rollen verwalten', um diesen Befehl zu nutzen.", 
            ephemeral=True
        )
        return False
    return app_commands.check(predicate)


# --- INTERAKTIVE BUTTON-ANSICHT (PAGINATOR) ---
class HelpPaginator(discord.ui.View):
    def __init__(self, pages: list, bot_avatar: str, guild_icon: str):
        super().__init__(timeout=180)  # Buttons deaktivieren sich nach 3 Minuten Inaktivität
        self.pages = pages
        self.bot_avatar = bot_avatar
        self.guild_icon = guild_icon
        self.current_page = 0

    def create_embed(self) -> discord.Embed:
        page_data = self.pages[self.current_page]
        
        embed = discord.Embed(
            title="📚 PPD Verwaltungssystem | Handbuch",
            description="Nutze die Buttons unten, um durch die Kategorien zu blättern.\n═" * 15,
            color=discord.Color.blue()
        )
        embed.set_author(name=f"Kategorie: {page_data['kategorie']}", icon_url=self.guild_icon)
        
        # Befehle der aktuellen Seite hinzufügen
        for cmd in page_data["befehle"]:
            embed.add_field(
                name=f"🔹 {cmd['name']}",
                value=f"**Beschreibung:** {cmd['desc']}\n**Verwendung:** {cmd['usage']}\n",
                inline=False
            )
            
        embed.set_footer(
            text=f"Seite {self.current_page + 1} von {len(self.pages)} • Zugriff nur für Dienstaufsicht", 
            icon_url=self.bot_avatar
        )
        return embed

    async def update_view(self, interaction: discord.Interaction):
        # Buttons je nach Seitenzahl aktivieren/deaktivieren
        self.btn_prev.disabled = self.current_page == 0
        self.btn_next.disabled = self.current_page == len(self.pages) - 1
        
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="◀ Zurück", style=discord.ButtonStyle.gray, disabled=True)
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_view(interaction)

    @discord.ui.button(label="Weiter ▶", style=discord.ButtonStyle.primary)
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_view(interaction)


# --- DIE COG ---
class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Hier sind deine strukturierten Seiten (immer max. 3 detailreiche Befehle pro Seite)
        self.help_pages = [
            {
                "kategorie": "Sanktionen (Teil 1)",
                "befehle": [
                    {
                        "name": "/mv [Nutzer] [Grund]",
                        "desc": "Erteilt eine Mündliche Dienstverwarnung. Wird in der Personalakte vermerkt und erlegt dem Beamten eine erhöhte Beweispflicht für zukünftiges Verhalten auf.",
                        "usage": "`/mv @MaxMustermann Unangemessener Ton im Funk`"
                    },
                    {
                        "name": "/sv [Nutzer] [Grund]",
                        "desc": "Erteilt eine Schriftliche Dienstverwarnung. Dies ist die finale Vorstufe vor einer Suspendierung oder Entlassung. Der Beamte wird offiziell abgemahnt.",
                        "usage": "`/sv @MaxMustermann Missachtung einer direkten Weisung`"
                    },
                    {
                        "name": "/su [Nutzer] [Dauer] [Grund]",
                        "desc": "Suspendiert einen Beamten temporär vom Dienst oder friert den Status bis zur offiziellen Gerichtsanhörung (GA) ein. Sämtliche Dienstrechte ruhen.",
                        "usage": "`/su @MaxMustermann 7 Tage Korruptionsverdacht`"
                    }
                ]
            },
            {
                "kategorie": "Personalverwaltung (Teil 1)",
                "befehle": [
                    {
                        "name": "/beförderung [Nutzer] [Neuer Rang]",
                        "desc": "Befördert den ausgewählten Beamten in den nächsthöheren Dienstgrad. Die Discord-Rollen werden vollautomatisch im Hintergrund angepasst.",
                        "usage": "`/beförderung @MaxMustermann Prüfer GD-21`"
                    },
                    {
                        "name": "/degradierung [Nutzer] [Neuer Rang]",
                        "desc": "Stuft den Beamten aufgrund von Fehlverhalten oder Degradierungsbeschluss auf einen niedrigeren Dienstgrad zurück. Rollen-Update erfolgt automatisch.",
                        "usage": "`/degradierung @MaxMustermann Anwärter GD-19`"
                    },
                    {
                        "name": "/kündigung [Nutzer] [Grund]",
                        "desc": "Entlässt den Mitarbeiter mit sofortiger Wirkung aus der Bundeskartei. Entzieht dem Nutzer vollautomatisch alle PPD-Dienstrollen.",
                        "usage": "`/kündigung @MaxMustermann Inaktivität / Fraktionsbeschluss`"
                    }
                ]
            },
            {
                "kategorie": "Abteilungsmanagement",
                "befehle": [
                    {
                        "name": "/abteilungs-betritt [Nutzer] [Abteilung]",
                        "desc": "Weist einen Beamten einer der Sonderdivisionen (z.B. SEK, Kriminalpolizei, Autobahnpolizei) zu und teilt ihm die entsprechende Abteilungsrolle zu.",
                        "usage": "`/abteilungs-betritt @MaxMustermann SEK`"
                    },
                    {
                        "name": "/abteilungs-austritt [Nutzer] [Abteilung]",
                        "desc": "Entfernt einen Beamten aus einer Sonderdivision (z.B. bei Abteilungswechsel oder Rauswurf) und bereinigt die damit verknüpften Rollen.",
                        "usage": "`/abteilungs-austritt @MaxMustermann SEK`"
                    }
                ]
            }
        ]

    @app_commands.command(name="help", description="Öffnet das interaktive Handbuch für das PPD Verwaltungssystem.")
    @has_allowed_role()
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def help_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild_icon = interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None
            bot_avatar = self.bot.user.display_avatar.url if self.bot and self.bot.user else None
            
            # Paginator-View erstellen
            view = HelpPaginator(self.help_pages, bot_avatar, guild_icon)
            
            # Erste Seite (Index 0) senden
            await interaction.followup.send(embed=view.create_embed(), view=view, ephemeral=True)
            
        except Exception as e:
            print(f"[HELP COG ERROR] Fehler beim Senden der Hilfe: {e}")
            await interaction.followup.send("⚠️ Ein interner Fehler ist beim Generieren der Hilfe-Seiten aufgetreten.", ephemeral=True)

    # Lokaler Fehler-Handler für Cooldowns
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"🚨 **Anti-Spam Schutz aktiv!** Bitte warte `{error.retry_after:.1f}` Sekunden, bevor du `/help` erneut nutzt.", 
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"🚨 **Anti-Spam Schutz aktiv!** Bitte warte `{error.retry_after:.1f}` Sekunden.", 
                    ephemeral=True
                )
        else:
            print(f"[HELP COG ERROR] Unerwarteter Fehler: {error}")


async def setup(bot):
    await bot.add_cog(HelpCog(bot))