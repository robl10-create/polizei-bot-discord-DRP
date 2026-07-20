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


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Zeigt eine Übersicht aller verfügbaren Personal- und Sanktionsbefehle.")
    @has_allowed_role()
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def help_command(self, interaction: discord.Interaction):
        # Sofort dem Discord-Server signalisieren, dass wir arbeiten
        await interaction.response.defer(ephemeral=True)
        
        try:
            embed = discord.Embed(
                title="📚 PPD Verwaltungssystem | Befehlsübersicht",
                description="Hier findest du alle Befehle des Personal- und Disziplinarsystems.",
                color=discord.Color.blue()
            )
            
            # Falls kein Server-Icon existiert, bleibt es None
            guild_icon = interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None
            embed.set_author(name="Dienstaufsicht Handbuch", icon_url=guild_icon)
            
            sanktionen = (
                "`/mv` - Stellt eine Mündliche Dienstverwarnung aus (inkl. Beweispflicht).\n"
                "`/sv` - Stellt eine Schriftliche Dienstverwarnung aus.\n"
                "`/su` - Suspendiert einen Beamten temporär oder bis zur GA."
            )
            embed.add_field(name="⚠️ Disziplinarmaßnahmen & Sanktionen", value=sanktionen, inline=False)
            
            management = (
                "`/beförderung` - Befördert einen Beamten (inkl. automatischem Rollen-Update).\n"
                "`/degradierung` - Degradiere einen Beamten (inkl. automatischem Rollen-Update).\n"
                "`/kündigung` - Entlässt einen Mitarbeiter aus der Bundeskartei und entzieht die Rolle.\n"
                "`/abteilungs-betritt` - Weist einen Beamten einer Sonderdivision zu.\n"
                "`/abteilungs-austritt` - Entfernt einen Beamten aus einer Sonderabteilung."
            )
            embed.add_field(name="📈 Personalverwaltung", value=management, inline=False)
            
            # Bot-Avatar absichern
            bot_avatar = self.bot.user.display_avatar.url if self.bot and self.bot.user else None
            embed.set_footer(text="Zugriff nur für autorisierte Dienstaufsichts-Mitglieder.", icon_url=bot_avatar)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"[HELP COG ERROR] Fehler beim Senden der Hilfe: {e}")
            await interaction.followup.send("⚠️ Ein interner Fehler ist beim Generieren der Hilfe-Liste aufgetreten.", ephemeral=True)

    # Lokaler Fehler-Handler NUR für diese Help-Cog
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            # Prüfen, ob bereits ein defer() oder eine Antwort gesendet wurde
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


# Setup-Funktion zum Laden der Cog
async def setup(bot):
    await bot.add_cog(HelpCog(bot))