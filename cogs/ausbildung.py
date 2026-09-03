import discord
from discord.ext import commands
from discord import app_commands
from .listen import ListenCog

# Füge hier alle Rollen-IDs ein, die Ausbildungen eintragen dürfen (z. B. SG22 / Ausbilder)
ALLOWED_ROLE_IDS = [
    1497905102156206162,  # Haupt-Admin / Dienstaufsicht
    1497905103397457991 # <--- Hier die Rollen-ID der SG22 / Ausbildungsleitung eintragen
]

def has_allowed_role():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_roles:
            return True

        user_role_ids = [role.id for role in interaction.user.roles]
        if any(role_id in user_role_ids for role_id in ALLOWED_ROLE_IDS):
            return True

        await interaction.response.send_message(
            "🚨 **Zugriff verweigert!** Du benötigst die Berechtigung der **SG22 (Ausbildungsabteilung)**.", 
            ephemeral=True
        )
        return False
        
    return app_commands.check(predicate)


class EducationSetupModal(discord.ui.Modal, title="Ausbildung details"):
    def __init__(self, member: discord.Member, view_setup):
        super().__init__()
        self.member = member
        self.view_setup = view_setup

        self.ausbildungs_name = discord.ui.TextInput(
            label="Name der Ausbildung / Fortbildung",
            placeholder="z. B. Grundausbildung, FTI, Spezialeinheit...",
            required=True
        )
        self.status_type = discord.ui.TextInput(
            label="Art der Zertifizierung",
            placeholder="Schreibe '1' für Erfolgreich Bestanden oder '2' für Prüfungszulassung",
            max_length=1,
            required=True
        )
        self.neuer_rang = discord.ui.TextInput(
            label="Neuer Rang (Exakter Discord-Rollenname)",
            placeholder="z. B. Polizeimeister (Freilassen wenn nur Zulassung)",
            required=False
        )
        self.alter_rang = discord.ui.TextInput(
            label="Alter Rang (Exakter Discord-Rollenname)",
            placeholder="Rolle die entfernt werden soll (falls vorhanden)",
            required=False
        )

        self.add_item(self.ausbildungs_name)
        self.add_item(self.status_type)
        self.add_item(self.neuer_rang)
        self.add_item(self.alter_rang)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        is_befoerderung = self.status_type.value.strip() == "1"
        status_str = "🎓 Abgeschlossen & Befördert" if is_befoerderung else "📝 Prüfungszulassung erhalten"

        self.view_setup.ergebnisse.append({
            "member": self.member,
            "ausbildung": self.ausbildungs_name.value.strip(),
            "status": status_str,
            "is_befoerderung": is_befoerderung,
            "neuer_rang": self.neuer_rang.value.strip() if self.neuer_rang.value else None,
            "alter_rang": self.alter_rang.value.strip() if self.alter_rang.value else None
        })

        await self.view_setup.process_next_member(interaction)


class MemberSelect(discord.ui.UserSelect):
    def __init__(self, view_setup):
        self.view_setup = view_setup
        super().__init__(
            placeholder="Wähle die absolvierenden Mitarbeiter aus (max. 10)...", 
            min_values=1, 
            max_values=10
        )

    async def callback(self, interaction: discord.Interaction):
        self.view_setup.members_to_process = [m for m in self.values if isinstance(m, discord.Member)]
        await self.view_setup.process_next_member(interaction)


class EducationSetupView(discord.ui.View):
    def __init__(self, creator: discord.Member, ausbildung_cog):
        super().__init__(timeout=600)
        self.creator = creator
        self.ausbildung_cog = ausbildung_cog
        
        self.members_to_process = []
        self.ergebnisse = []

        # Füge das Nutzersuch-Feld direkt hinzu
        self.add_item(MemberSelect(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.creator.id:
            await interaction.response.send_message("Nur der Ersteller des Befehls kann dieses Menü bedienen.", ephemeral=True)
            return False
        return True

    async def process_next_member(self, interaction: discord.Interaction):
        if self.members_to_process:
            member = self.members_to_process.pop(0)
            modal = EducationSetupModal(member, self)
            await interaction.response.send_modal(modal)
        else:
            await self.finish_and_post(interaction)

    async def finish_and_post(self, interaction: discord.Interaction):
        guild = interaction.guild
        lc = self.ausbildung_cog.get_listen_cog()
        datum_heute = interaction.created_at.strftime("%d.%m.%Y - %H:%M")

        embed = discord.Embed(
            title="🎓 AUSBILDUNG & ZERTIFIZIERUNG | BEKANNTMACHUNG", 
            color=discord.Color.from_rgb(52, 152, 219)
        )
        embed.set_author(
            name="Ausbildungsabteilung • SG22", 
            icon_url=guild.icon.url if guild.icon else None
        )

        bekanntmachung_text = ""
        status_log = []

        for item in self.ergebnisse:
            member = item["member"]
            ausbildung = item["ausbildung"]
            status = item["status"]
            
            bekanntmachung_text += f"👤 **Beamter:** <@{member.id}>\n"
            bekanntmachung_text += f"📚 **Lehrgang:** `{ausbildung}`\n"
            bekanntmachung_text += f"📌 **Status:** {status}\n"

            # Wenn es eine direkte Beförderung ist:
            if item["is_befoerderung"] and item["neuer_rang"]:
                role_add = discord.utils.get(guild.roles, name=item["neuer_rang"])
                role_remove = discord.utils.get(guild.roles, name=item["alter_rang"]) if item["alter_rang"] else None

                try:
                    if role_add: 
                        await member.add_roles(role_add, reason="PPD System: Ausbildung bestanden")
                    if role_remove: 
                        await member.remove_roles(role_remove, reason="PPD System: Ausbildung bestanden")
                    
                    bekanntmachung_text += f"📈 **Neuer Rang:** {role_add.mention if role_add else item['neuer_rang']}\n"
                except discord.Forbidden:
                    status_log.append(f"⚠️ Rollen für {member.display_name} konnten wegen fehlender Rechte nicht angepasst werden.")

                # In DB eintragen
                u_id = str(member.id)
                if lc and u_id not in lc.daten["mitarbeiter"]:
                    lc.daten["mitarbeiter"][u_id] = {"abteilung": None}
                if lc:
                    lc.daten["mitarbeiter"][u_id]["name"] = member.name

            bekanntmachung_text += "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"

        embed.add_field(name="​", value=bekanntmachung_text, inline=False)
        embed.add_field(name="🖋️ Autorisierte Ausbilder", value=f"<@{interaction.user.id}>\n*Ausbildungsleitung SG22*", inline=True)
        embed.add_field(name="📅 Datum", value=f"`{datum_heute} Uhr`", inline=True)
        embed.set_footer(text="🇩🇪 Akte Ausbildungsabteilung • PPD", icon_url=self.ausbildung_cog.bot.user.display_avatar.url)

        if lc:
            lc.save_data()

        # Nachricht öffentlich im Kanal senden
        pings = " ".join([f"<@{i['member'].id}>" for i in self.ergebnisse])
        await interaction.channel.send(content=f"🎓 **Ausbildungsergebnisse veröffentlicht:** {pings}", embed=embed)

        # Rückmeldung an den Ausbilder
        msg = "✅ **Alle Ausbildungen und Beförderungen wurden erfolgreich verarbeitet und gepostet!**"
        if status_log:
            msg += "\n\n" + "\n".join(status_log)

        if interaction.response.is_done():
            await interaction.followup.send(content=msg, ephemeral=True)
        else:
            await interaction.edit_original_response(content=msg, view=None)


class AusbildungCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_listen_cog(self) -> ListenCog:
        return self.bot.get_cog("ListenCog")

    @app_commands.command(name="ausbildung", description="Trage Prüfungszulassungen oder Beförderungen nach einer Ausbildung ein.")
    @has_allowed_role()
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def ausbildung(self, interaction: discord.Interaction):
        view = EducationSetupView(interaction.user, self)
        await interaction.response.send_message(
            "🎓 **Ausbildungsverwaltung**\n\nBitte wähle unten die Mitarbeiter aus, die eine Ausbildung abgeschlossen oder eine Prüfungszulassung erhalten haben:", 
            view=view, 
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(AusbildungCog(bot))