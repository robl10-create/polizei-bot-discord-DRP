import discord
from discord.ext import commands
from discord import app_commands

ALLOWED_ROLE_ID = 1497905102156206162

def has_allowed_role():
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

class SanktionenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mv", description="Stellt eine Mündliche Dienstverwarnung aus.")
    @app_commands.choices(beweis=[
        app_commands.Choice(name="🎥 Clip", value="Clip (Videobeweis)"),
        app_commands.Choice(name="📸 Screenshot", value="Screenshot (Bildbeweis)"),
        app_commands.Choice(name="📂 Zeugenaussage / Dienstbericht", value="Zeugenaussage / Interner Dienstbericht")
    ])
    @has_allowed_role()
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def muendliche_verwarnung(
        self, 
        interaction: discord.Interaction, 
        mitarbeiter: discord.Member, 
        beweis: app_commands.Choice[str],
        grund: str, 
        anmerkung: str = "Bei Fragen oder Anliegen öffnen sie bitte ein Dienstaufsicht-Ticket.",
        mitunterschrift_1: discord.Member = None,
        mitunterschrift_2: discord.Member = None
    ):
        await interaction.response.defer()
        
        embed = discord.Embed(title="⚠️ DISZIPLINARMASSNAHME | MÜNDLICHE VERWARNUNG", color=discord.Color.from_rgb(230, 126, 34))
        embed.set_author(name="Dienstliche Bekanntmachung • Disziplinarbeschluss", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        inhalt = (
            f"📋 **Stammdaten des Beamten**\n"
            f"• **Name:** <@{mitarbeiter.id}>\n\n"
            f"📢 **Sanktionsstatus**\n"
            f"• Hiermit erhält der Beamte eine **Mündliche Dienstverwarnung**.\n\n"
            f"🔍 **Beweisführung**\n"
            f"• {beweis.value}\n\n"
            f"📜 **Disziplinarischer Grund**\n"
            f"*{grund}*\n\n"
            f"💡 **Anmerkung**\n"
            f"*{anmerkung}*\n\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        )
        embed.add_field(name="​", value=inhalt, inline=False)
        
        unterschriften = f"<@{interaction.user.id}>\n*Disziplinarausschuss PPD*"
        if mitunterschrift_1:
            unterschriften += f"\n<@{mitunterschrift_1.id}>"
        if mitunterschrift_2:
            unterschriften += f"\n<@{mitunterschrift_2.id}>"
            
        embed.add_field(name="🖋️ Autorisierte Unterschrift", value=unterschriften, inline=True)
        embed.add_field(name="📅 Ausstellungsdatum", value=f"`{interaction.created_at.strftime('%d.%m.%Y - %H:%M')} Uhr`", inline=True)
        
        embed.set_thumbnail(url=mitarbeiter.display_avatar.url)
        embed.set_footer(text="🇩🇪 Geprüftes Dokument • PPD Bundeskartei", icon_url=self.bot.user.display_avatar.url)
        
        await interaction.followup.send(content=f"<@{mitarbeiter.id}>", embed=embed)

    @app_commands.command(name="sv", description="Stellt eine Schriftliche Dienstverwarnung aus.")
    @app_commands.choices(beweis=[
        app_commands.Choice(name="🎥 Clip", value="Clip (Videobeweis)"),
        app_commands.Choice(name="📸 Screenshot", value="Screenshot (Bildbeweis)"),
        app_commands.Choice(name="📂 Zeugenaussage / Dienstbericht", value="Zeugenaussage / Interner Dienstbericht")
    ])
    @has_allowed_role()
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def schriftliche_verwarnung(
        self, 
        interaction: discord.Interaction, 
        mitarbeiter: discord.Member, 
        beweis: app_commands.Choice[str],
        grund: str, 
        anmerkung: str = "Ich hoffe sie unterlassen das in Zukunft. Bei Fragen öffnen sie einen SG23 Ticket oder wenden sie sich an die Ausstellenden Personen.",
        mitunterschrift_1: discord.Member = None,
        mitunterschrift_2: discord.Member = None
    ):
        await interaction.response.defer()
        
        embed = discord.Embed(title="⚠️ DISZIPLINARMASSNAHME | SCHRIFTLICHE VERWARNUNG", color=discord.Color.from_rgb(192, 41, 43))
        embed.set_author(name="Dienstliche Bekanntmachung • Disziplinarbeschluss", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        inhalt = (
            f"📋 **Stammdaten des Beamten**\n"
            f"• **Name:** <@{mitarbeiter.id}>\n\n"
            f"📢 **Sanktionsstatus**\n"
            f"• Hiermit erhält der Beamte eine **Schriftliche Dienstverwarnung**.\n\n"
            f"🔍 **Beweisführung**\n"
            f"• {beweis.value}\n\n"
            f"📜 **Disziplinarischer Grund**\n"
            f"*{grund}*\n\n"
            f"💡 **Anmerkung**\n"
            f"*{anmerkung}*\n\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        )
        embed.add_field(name="​", value=inhalt, inline=False)
        
        unterschriften = f"<@{interaction.user.id}>\n*Disziplinarausschuss PPD*"
        if mitunterschrift_1:
            unterschriften += f"\n<@{mitunterschrift_1.id}>"
        if mitunterschrift_2:
            unterschriften += f"\n<@{mitunterschrift_2.id}>"
            
        embed.add_field(name="🖋️ Autorisierte Unterschrift", value=unterschriften, inline=True)
        embed.add_field(name="📅 Ausstellungsdatum", value=f"`{interaction.created_at.strftime('%d.%m.%Y - %H:%M')} Uhr`", inline=True)
        
        embed.set_thumbnail(url=mitarbeiter.display_avatar.url)
        embed.set_footer(text="🇩🇪 Geprüftes Dokument • PPD Bundeskartei", icon_url=self.bot.user.display_avatar.url)
        
        await interaction.followup.send(content=f"<@{mitarbeiter.id}>", embed=embed)

    @app_commands.command(name="su", description="Stellt eine dienstliche Suspendierung aus.")
    @app_commands.choices(art_der_dauer=[
        app_commands.Choice(name="⏳ Bestimmte Anzahl an Tagen (unten angeben)", value="tage"),
        app_commands.Choice(name="📚 Bis zur GA (Grundausbildung)", value="ga")
    ])
    @app_commands.describe(dauer_in_tagen="Nur ausfüllen, wenn oben 'Bestimmte Anzahl an Tagen' gewählt wurde.")
    @has_allowed_role()
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def suspendierung(
        self, 
        interaction: discord.Interaction, 
        mitarbeiter: discord.Member, 
        art_der_dauer: app_commands.Choice[str],
        grund: str, 
        dauer_in_tagen: int = None,
        anmerkung: str = "Bei Fragen oder Anliegen, öffnen sie bitte ein Dienstaufsicht-Ticket.",
        mitunterschrift_1: discord.Member = None,
        mitunterschrift_2: discord.Member = None
    ):
        await interaction.response.defer()
        
        if art_der_dauer.value == "ga":
            dauer_text = "`Bis zur GA (Grundausbildung)`"
        else:
            tage = dauer_in_tagen if dauer_in_tagen is not None else 1
            dauer_text = f"`{tage} Tag(e)`"
        
        embed = discord.Embed(title="🚨 DISZIPLINARMASSNAHME | SUSPENDIERUNG", color=discord.Color.from_rgb(44, 62, 80))
        embed.set_author(name="Dienstliche Bekanntmachung • Disziplinarbeschluss", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        inhalt = (
            f"📋 **Stammdaten des Beamten**\n"
            f"• **Name:** <@{mitarbeiter.id}>\n\n"
            f"📢 **Sanktionsstatus**\n"
            f"• Hiermit erhält der Beamte eine temporäre **Suspendierung vom Dienst**.\n\n"
            f"⏳ **Dauer der Maßnahme**\n"
            f"• {dauer_text}\n\n"
            f"📜 **Disziplinarischer Grund**\n"
            f"*{grund}*\n\n"
            f"💡 **Anmerkung**\n"
            f"*{anmerkung}*\n\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        )
        embed.add_field(name="​", value=inhalt, inline=False)
        
        unterschriften = f"<@{interaction.user.id}>\n*Behördenleitung / Direktion*"
        if mitunterschrift_1:
            unterschriften += f"\n<@{mitunterschrift_1.id}>"
        if mitunterschrift_2:
            unterschriften += f"\n<@{mitunterschrift_2.id}>"
            
        embed.add_field(name="🖋️ Autorisierte Unterschrift", value=unterschriften, inline=True)
        embed.add_field(name="📅 Ausstellungsdatum", value=f"`{interaction.created_at.strftime('%d.%m.%Y - %H:%M')} Uhr`", inline=True)
        
        embed.set_thumbnail(url=mitarbeiter.display_avatar.url)
        embed.set_footer(text="🇩🇪 Geprüftes Dokument • PPD Bundeskartei", icon_url=self.bot.user.display_avatar.url)
        
        await interaction.followup.send(content=f"<@{mitarbeiter.id}>", embed=embed)

async def setup(bot):
    await bot.add_cog(SanktionenCog(bot))