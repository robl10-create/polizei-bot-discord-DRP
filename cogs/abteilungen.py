import discord
from discord.ext import commands
from discord import app_commands
from .listen import ListenCog

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

class AbteilungenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_listen_cog(self) -> ListenCog:
        return self.bot.get_cog("ListenCog")

    @app_commands.command(name="abteilungs-betritt", description="Füge einen Mitarbeiter einer Sonderabteilung hinzu.")
    @has_allowed_role()
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def abt_betritt(
        self, 
        interaction: discord.Interaction, 
        mitarbeiter: discord.Member, 
        abteilung: str, 
        grund: str = "Zulassungsverfahren bestanden",
        mitunterschrift_1: discord.Member = None,
        mitunterschrift_2: discord.Member = None
    ):
        await interaction.response.defer()
        lc = self.get_listen_cog()
        user_id = str(mitarbeiter.id)

        if user_id in lc.daten["mitarbeiter"]:
            lc.daten["mitarbeiter"][user_id]["abteilung"] = abteilung
            lc.save_data()
            
            embed = discord.Embed(title="🔰 SONDERDIVISION | ZUWEISUNG", color=discord.Color.from_rgb(52, 152, 219))
            embed.set_author(name="Dienstliche Bekanntmachung • Versetzung", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            inhalt = f"📋 **Stammdaten des Beamten**\n• **Name:** <@{mitarbeiter.id}>\n• **Zugewiesene Division:** `{abteilung}`\n\n📜 **Qualifikationsgrund**\n*{grund}*"
            embed.add_field(name="​", value=inhalt, inline=False)
            
            unterschriften = f"<@{interaction.user.id}>\n*Kommandantur*"
            if mitunterschrift_1:
                unterschriften += f"\n<@{mitunterschrift_1.id}>"
            if mitunterschrift_2:
                unterschriften += f"\n<@{mitunterschrift_2.id}>"
                
            embed.add_field(name="🖋️ Unterschrift Direktion", value=unterschriften, inline=True)
            embed.add_field(name="📅 Datum", value=f"`{interaction.created_at.strftime('%d.%m.%Y')}`", inline=True)
            embed.set_thumbnail(url=mitarbeiter.display_avatar.url)
            embed.set_footer(text="Sondereinheiten • PPD Taktikakte", icon_url=self.bot.user.display_avatar.url)
            
            await interaction.followup.send(content=f"<@{mitarbeiter.id}>", embed=embed)
        else:
            await interaction.followup.send("Der Mitarbeiter muss zuerst im System registriert sein (z.B. über /beförderung).", ephemeral=True)

    @app_commands.command(name="abteilungs-austritt", description="Entferne einen Mitarbeiter aus einer Abteilung.")
    @has_allowed_role()
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def abt_austritt(
        self, 
        interaction: discord.Interaction, 
        mitarbeiter: discord.Member, 
        grund: str = "Freiwillige Niederlegung / Rotation",
        mitunterschrift_1: discord.Member = None,
        mitunterschrift_2: discord.Member = None
    ):
        await interaction.response.defer()
        lc = self.get_listen_cog()
        user_id = str(mitarbeiter.id)

        if user_id in lc.daten["mitarbeiter"] and lc.daten["mitarbeiter"][user_id].get("abteilung"):
            alt_abt = lc.daten["mitarbeiter"][user_id]["abteilung"]
            lc.daten["mitarbeiter"][user_id]["abteilung"] = None
            lc.save_data()
            
            embed = discord.Embed(title="🚪 SONDERDIVISION | AUSTRITT", color=discord.Color.from_rgb(241, 196, 15))
            embed.set_author(name="Dienstliche Bekanntmachung • Rotationsbeschluss", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            inhalt = f"📋 **Stammdaten des Beamten**\n• **Name:** <@{mitarbeiter.id}>\n• **Ausgeschieden aus:** `{alt_abt}`\n\n📜 **Grund des Austritts**\n*{grund}*"
            embed.add_field(name="​", value=inhalt, inline=False)
            
            unterschriften = f"<@{interaction.user.id}>\n*Kommandantur*"
            if mitunterschrift_1:
                unterschriften += f"\n<@{mitunterschrift_1.id}>"
            if mitunterschrift_2:
                unterschriften += f"\n<@{mitunterschrift_2.id}>"
                
            embed.add_field(name="🖋️ Unterschrift Direktion", value=unterschriften, inline=True)
            embed.add_field(name="📅 Datum", value=f"`{interaction.created_at.strftime('%d.%m.%Y')}`", inline=True)
            embed.set_thumbnail(url=mitarbeiter.display_avatar.url)
            embed.set_footer(text="Sondereinheiten • PPD Taktikakte", icon_url=self.bot.user.display_avatar.url)
            
            await interaction.followup.send(content=f"<@{mitarbeiter.id}>", embed=embed)
        else:
            await interaction.followup.send("Mitarbeiter hat keine Abteilung oder ist nicht im System.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AbteilungenCog(bot))