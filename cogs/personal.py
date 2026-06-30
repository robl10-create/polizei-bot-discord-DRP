import discord
from discord.ext import commands
from discord import app_commands
from .listen import ListenCog

# ==========================================
# INTERAKTIVE MENÜS FÜR DEN WEEKLY INSIDER
# ==========================================

class RankSelect(discord.ui.Select):
    def __init__(self, member: discord.Member, service_type: str, view_setup):
        self.member = member
        self.service_type = service_type
        self.view_setup = view_setup
        
        if service_type == "GD":
            options = [
                discord.SelectOption(label="G1 ➔ G2", value="G1|G2"),
                discord.SelectOption(label="G2 ➔ G3", value="G2|G3"),
                discord.SelectOption(label="G3 ➔ G4", value="G3|G4"),
                discord.SelectOption(label="G4 ➔ G5", value="G4|G5"),
                discord.SelectOption(label="G5 ➔ G6", value="G5|G6"),
            ]
        else:
            options = [
                discord.SelectOption(label="M1 ➔ M2", value="M1|M2"),
                discord.SelectOption(label="M2 ➔ M3", value="M2|M3"),
                discord.SelectOption(label="M3 ➔ M4", value="M3|M4"),
                discord.SelectOption(label="M4 ➔ M5", value="M4|M5"),
            ]
            
        super().__init__(placeholder=f"Beförderungsstufe für {member.display_name}...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        old_rank_str, new_rank_str = self.values[0].split("|")
        
        if self.service_type == "GD":
            self.view_setup.gehobener_dienst.append((self.member, old_rank_str, new_rank_str))
        else:
            self.view_setup.mittlerer_dienst.append((self.member, old_rank_str, new_rank_str))
            
        await self.view_setup.process_next_member_rank(interaction, self.service_type)


class MemberSelect(discord.ui.UserSelect):
    def __init__(self, category: str, view_setup):
        self.category = category
        self.view_setup = view_setup
        super().__init__(placeholder="Wähle die Mitarbeiter aus (Mehrfachauswahl möglich)...", min_values=1, max_values=10)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.category == "VW":
            for member in self.values:
                if isinstance(member, discord.Member):
                    self.view_setup.verwarnungen.append(member)
            await self.view_setup.update_message(interaction)
        else:
            self.view_setup.members_to_process = [m for m in self.values if isinstance(m, discord.Member)]
            await self.view_setup.process_next_member_rank(interaction, self.category)


class WeeklyInsiderSetupView(discord.ui.View):
    def __init__(self, creator: discord.Member, personal_cog):
        super().__init__(timeout=600)
        self.creator = creator
        self.personal_cog = personal_cog
        
        self.gehobener_dienst = []  
        self.mittlerer_dienst = []   
        self.verwarnungen = []      
        self.members_to_process = []

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.creator.id:
            await interaction.response.send_message("Nur die Person, die den Befehl gestartet hat, kann das Menü bedienen.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⭐ Gehobener Dienst hinzufügen", style=discord.ButtonStyle.primary, row=0)
    async def add_gd(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        view = discord.ui.View()
        view.add_item(MemberSelect("GD", self))
        await interaction.followup.edit_message(message_id=interaction.message.id, content="**Wähle die Mitarbeiter für den Gehobenen Dienst aus:**", view=view)

    @discord.ui.button(label="🛡️ Mittlerer Dienst hinzufügen", style=discord.ButtonStyle.primary, row=0)
    async def add_md(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        view = discord.ui.View()
        view.add_item(MemberSelect("MD", self))
        await interaction.followup.edit_message(message_id=interaction.message.id, content="**Wähle die Mitarbeiter für den Mittleren Dienst aus:**", view=view)

    @discord.ui.button(label="⚠️ Verwarnung hinzufügen", style=discord.ButtonStyle.danger, row=1)
    async def add_vw(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        view = discord.ui.View()
        view.add_item(MemberSelect("VW", self))
        await interaction.followup.edit_message(message_id=interaction.message.id, content="**Wähle die Mitarbeiter für die Verwarnungen aus:**", view=view)

    @discord.ui.button(label="🚀 Fertigstellen & Posten", style=discord.ButtonStyle.success, row=1)
    async def post_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        guild = interaction.guild
        lc = self.personal_cog.get_listen_cog()
        datum_heute = interaction.created_at.strftime("%d.%m.%Y")
        
        text = f"# Wöchentliche Upranks vom Sonntag, den {datum_heute}\n"
        text += "**Beförderungen:**\n\n"
        
        status_log = []

        if self.gehobener_dienst:
            text += "**Gehobener Dienst**\n"
            for member, old_r, new_r in self.gehobener_dienst:
                text += f"{member.mention} ➔ {old_r} ➔ {new_r}\n"
                
                role_to_remove = discord.utils.get(guild.roles, name=old_r)
                role_to_add = discord.utils.get(guild.roles, name=new_r)
                
                try:
                    if role_to_add: await member.add_roles(role_to_add, reason="Weekly Insider")
                    if role_to_remove: await member.remove_roles(role_to_remove, reason="Weekly Insider")
                except discord.Forbidden:
                    status_log.append(f"⚠️ Keine Rechte für Rollen von {member.display_name}")

                u_id = str(member.id)
                if u_id not in lc.daten["mitarbeiter"]: lc.daten["mitarbeiter"][u_id] = {"abteilung": None}
                lc.daten["mitarbeiter"][u_id]["rang"] = "GD"
                lc.daten["mitarbeiter"][u_id]["name"] = member.name

            text += "\n"
            
        if self.mittlerer_dienst:
            text += "**Mittlerer Dienst:**\n"
            for member, old_r, new_r in self.mittlerer_dienst:
                text += f"{member.mention} ➔ {old_r} ➔ {new_r}\n"
                
                role_to_remove = discord.utils.get(guild.roles, name=old_r)
                role_to_add = discord.utils.get(guild.roles, name=new_r)
                
                try:
                    if role_to_add: await member.add_roles(role_to_add, reason="Weekly Insider")
                    if role_to_remove: await member.remove_roles(role_to_remove, reason="Weekly Insider")
                except discord.Forbidden:
                    status_log.append(f"⚠️ Keine Rechte für Rollen von {member.display_name}")

                u_id = str(member.id)
                if u_id not in lc.daten["mitarbeiter"]: lc.daten["mitarbeiter"][u_id] = {"abteilung": None}
                lc.daten["mitarbeiter"][u_id]["rang"] = "MD"
                lc.daten["mitarbeiter"][u_id]["name"] = member.name

            text += "\n"
            
        if self.verwarnungen:
            text += "**Verwarnungen:**\n*(Dienstzeit nicht erfüllt)*\n"
            for member in self.verwarnungen:
                text += f"{member.mention}\n"
            text += "\n"
            
        text += "Bei Fragen ein Behördenleitung-Ticket öffnen\n# 🎫 | kontakt-aufnehmen\n\n"
        text += f"Unterschrift\n{interaction.user.mention} | ☀️"
        
        lc.save_data()
        await interaction.channel.send(content=text)
        
        final_info = "✅ **Die wöchentliche Liste wurde erfolgreich gepostet und die Server-Rollen wurden aktualisiert!**"
        if status_log:
            error_msg = "\n".join(status_log)
            final_info += f"\n\n**Hinweis zu den Rollen:**\n{error_msg}"
            
        await interaction.followup.edit_message(message_id=interaction.message.id, content=final_info, view=None)

    async def process_next_member_rank(self, interaction: discord.Interaction, service_type: str):
        if self.members_to_process:
            member = self.members_to_process.pop(0)
            view = discord.ui.View()
            view.add_item(RankSelect(member, service_type, self))
            await interaction.followup.edit_message(message_id=interaction.message.id, content=f"Welchen Rang erhält {member.mention}?", view=view)
        else:
            await self.update_message(interaction)

    async def update_message(self, interaction: discord.Interaction):
        preview = "**Aktuelle Liste im Speicher:**\n\n"
        preview += "**Gehobener Dienst:**\n" + ("\n".join([f"• {m.display_name} ({old} ➔ {new})" for m, old, new in self.gehobener_dienst]) if self.gehobener_dienst else "*Keine Einträge*") + "\n\n"
        preview += "**Mittlerer Dienst:**\n" + ("\n".join([f"• {m.display_name} ({old} ➔ {new})" for m, old, new in self.mittlerer_dienst]) if self.mittlerer_dienst else "*Keine Einträge*") + "\n\n"
        preview += "**Verwarnungen:**\n" + ("\n".join([f"• {m.display_name}" for m in self.verwarnungen]) if self.verwarnungen else "*Keine Einträge*") + "\n\n"
        preview += "Nutze die Buttons unten, um weitere Personen hinzuzufügen. Wenn alles passt, klicke auf Posten."
        
        await interaction.followup.edit_message(message_id=interaction.message.id, content=preview, view=self)


# ==========================================
# HAUPT COG MIT SANKTIONS- & PERSONAL-SYSTEM
# ==========================================

class PersonalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_listen_cog(self) -> ListenCog:
        return self.bot.get_cog("ListenCog")

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"🚨 **Anti-Spam Schutz aktiv!** Bitte warte `{error.retry_after:.1f}` Sekunden, bevor du diesen Befehl erneut nutzt.", 
                ephemeral=True
            )

    # ==========================================
    # SANKTIONSBEFEHLE
    # ==========================================

    @app_commands.command(name="mv", description="Stellt eine Mündliche Dienstverwarnung aus.")
    @app_commands.choices(beweis=[
        app_commands.Choice(name="🎥 Clip", value="Clip (Videobeweis)"),
        app_commands.Choice(name="📸 Screenshot", value="Screenshot (Bildbeweis)"),
        app_commands.Choice(name="📂 Zeugenaussage / Dienstbericht", value="Zeugenaussage / Interner Dienstbericht")
    ])
    @app_commands.checks.has_permissions(manage_roles=True)
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
            f"• **Name:** {mitarbeiter.mention}\n\n"
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
        
        unterschriften = f"{interaction.user.mention}\n*Disziplinarausschuss PPD*"
        if mitunterschrift_1:
            unterschriften += f"\n{mitunterschrift_1.mention}"
        if mitunterschrift_2:
            unterschriften += f"\n{mitunterschrift_2.mention}"
            
        embed.add_field(name="🖋️ Autorisierte Unterschrift", value=unterschriften, inline=True)
        embed.add_field(name="📅 Ausstellungsdatum", value=f"`{interaction.created_at.strftime('%d.%m.%Y - %H:%M')} Uhr`", inline=True)
        
        embed.set_thumbnail(url=mitarbeiter.display_avatar.url)
        embed.set_footer(text="🇩🇪 Geprüftes Dokument • PPD Bundeskartei", icon_url=self.bot.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="sv", description="Stellt eine Schriftliche Dienstverwarnung aus.")
    @app_commands.choices(beweis=[
        app_commands.Choice(name="🎥 Clip", value="Clip (Videobeweis)"),
        app_commands.Choice(name="📸 Screenshot", value="Screenshot (Bildbeweis)"),
        app_commands.Choice(name="📂 Zeugenaussage / Dienstbericht", value="Zeugenaussage / Interner Dienstbericht")
    ])
    @app_commands.checks.has_permissions(manage_roles=True)
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
            f"• **Name:** {mitarbeiter.mention}\n\n"
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
        
        unterschriften = f"{interaction.user.mention}\n*Disziplinarausschuss PPD*"
        if mitunterschrift_1:
            unterschriften += f"\n{mitunterschrift_1.mention}"
        if mitunterschrift_2:
            unterschriften += f"\n{mitunterschrift_2.mention}"
            
        embed.add_field(name="🖋️ Autorisierte Unterschrift", value=unterschriften, inline=True)
        embed.add_field(name="📅 Ausstellungsdatum", value=f"`{interaction.created_at.strftime('%d.%m.%Y - %H:%M')} Uhr`", inline=True)
        
        embed.set_thumbnail(url=mitarbeiter.display_avatar.url)
        embed.set_footer(text="🇩🇪 Geprüftes Dokument • PPD Bundeskartei", icon_url=self.bot.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="su", description="Stellt eine dienstliche Suspendierung aus.")
    @app_commands.describe(dauer_in_tagen="Die Dauer der Suspendierung (z.B. 3 oder 7)")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def suspendierung(
        self, 
        interaction: discord.Interaction, 
        mitarbeiter: discord.Member, 
        dauer_in_tagen: int,
        grund: str, 
        anmerkung: str = "Bei Fragen oder Anliegen, öffnen sie bitte ein Dienstaufsicht-Ticket.",
        mitunterschrift_1: discord.Member = None,
        mitunterschrift_2: discord.Member = None
    ):
        await interaction.response.defer()
        
        embed = discord.Embed(title="🚨 DISZIPLINARMASSNAHME | SUSPENDIERUNG", color=discord.Color.from_rgb(44, 62, 80))
        embed.set_author(name="Dienstliche Bekanntmachung • Disziplinarbeschluss", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        inhalt = (
            f"📋 **Stammdaten des Beamten**\n"
            f"• **Name:** {mitarbeiter.mention}\n\n"
            f"📢 **Sanktionsstatus**\n"
            f"• Hiermit erhält der Beamte eine temporäre **Suspendierung vom Dienst**.\n\n"
            f"⏳ **Dauer der Maßnahme**\n"
            f"• `{dauer_in_tagen} Tage`\n\n"
            f"📜 **Disziplinarischer Grund**\n"
            f"*{grund}*\n\n"
            f"💡 **Anmerkung**\n"
            f"*{anmerkung}*\n\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        )
        embed.add_field(name="​", value=inhalt, inline=False)
        
        unterschriften = f"{interaction.user.mention}\n*Behördenleitung / Direktion*"
        if mitunterschrift_1:
            unterschriften += f"\n{mitunterschrift_1.mention}"
        if mitunterschrift_2:
            unterschriften += f"\n{mitunterschrift_2.mention}"
            
        embed.add_field(name="🖋️ Autorisierte Unterschrift", value=unterschriften, inline=True)
        embed.add_field(name="📅 Ausstellungsdatum", value=f"`{interaction.created_at.strftime('%d.%m.%Y - %H:%M')} Uhr`", inline=True)
        
        embed.set_thumbnail(url=mitarbeiter.display_avatar.url)
        embed.set_footer(text="🇩🇪 Geprüftes Dokument • PPD Bundeskartei", icon_url=self.bot.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed)

    # ==========================================
    # CORE MANAGEMENT COMMANDS WITH NUMBERS
    # ==========================================

    @app_commands.command(name="beförderung", description="Befördere einen Mitarbeiter und passe seine Rollen automatisch an.")
    @app_commands.choices(ebene=[
        app_commands.Choice(name="🛡️ Mittlerer Dienst (MD)", value="MD"),
        app_commands.Choice(name="⭐ Gehobener Dienst (GD)", value="GD"),
        app_commands.Choice(name="🦅 Höherer Dienst (HD)", value="HD"),
        app_commands.Choice(name="💼 Behördenleitung (BHL)", value="BHL")
    ])
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def befoerderung(
        self, 
        interaction: discord.Interaction, 
        mitarbeiter: discord.Member, 
        ebene: str, 
        dienstnummer: str, 
        alter_rang: discord.Role, 
        neuer_rang: discord.Role, 
        grund: str
    ):
        await interaction.response.defer()
        lc = self.get_listen_cog()
        user_id = str(mitarbeiter.id)

        try:
            await mitarbeiter.add_roles(neuer_rang, reason="PPD System: Beförderung")
            await mitarbeiter.remove_roles(alter_rang, reason="PPD System: Beförderung")
            rollen_status = f"🟩 **Rollen-Update:** {neuer_rang.mention} hinzugefügt, {alter_rang.mention} entfernt."
        except discord.Forbidden:
            rollen_status = f"⚠️ **System-Fehler:** Bot-Hierarchie unzureichend! Rolle konnte nicht angepasst werden."

        # Speichert die Dienstnummer und Meta-Infos im JSON-Backend ab
        if user_id not in lc.daten["mitarbeiter"]:
            lc.daten["mitarbeiter"][user_id] = {"abteilung": None}
            
        lc.daten["mitarbeiter"][user_id]["rang"] = ebene
        lc.daten["mitarbeiter"][user_id]["nummer"] = dienstnummer
        lc.daten["mitarbeiter"][user_id]["name"] = mitarbeiter.name
        lc.save_data()

        embed = discord.Embed(title="📈 DIENSTGRADÄNDERUNG | BEFÖRDERUNG", color=discord.Color.from_rgb(46, 204, 113))
        embed.set_author(name="Dienstliche Bekanntmachung • Personalabteilung", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        inhalt = (
            f"📋 **Stammdaten des Beamten**\n• **Name:** {mitarbeiter.mention}\n• **Ebene:** `{ebene}`\n• **Dienstnummer:** `{ebene}-{dienstnummer}`\n\n"
            f"📈 **Dienstgradänderung**\n• **Alter Dienstgrad:** {alter_rang.mention}\n• **Neuer Dienstgrad:** {neuer_rang.mention}\n\n"
            f"📜 **Begründung der Maßnahme**\n*{grund}*\n\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n⚙️ **Automatische Protokollierung**\n{rollen_status}"
        )
        embed.add_field(name="​", value=inhalt, inline=False)
        embed.add_field(name="🖋️ Autorisierte Unterschrift", value=f"{interaction.user.mention}\n*Personalabteilung PPD*", inline=True)
        embed.add_field(name="📅 Ausstellungsdatum", value=f"`{interaction.created_at.strftime('%d.%m.%Y - %H:%M')} Uhr`", inline=True)
        embed.set_thumbnail(url=mitarbeiter.display_avatar.url)
        embed.set_footer(text="🇩🇪 Geprüftes Dokument • PPD Bundeskartei", icon_url=self.bot.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="degradierung", description="Degradiere einen Mitarbeiter und passe seine Rollen automatisch an.")
    @app_commands.choices(ebene=[
        app_commands.Choice(name="🛡️ Mittlerer Dienst (MD)", value="MD"),
        app_commands.Choice(name="⭐ Gehobener Dienst (GD)", value="GD"),
        app_commands.Choice(name="🦅 Höherer Dienst (HD)", value="HD"),
        app_commands.Choice(name="💼 Behördenleitung (BHL)", value="BHL")
    ])
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def degradierung(
        self, 
        interaction: discord.Interaction, 
        mitarbeiter: discord.Member, 
        ebene: str, 
        dienstnummer: str, 
        alter_rang: discord.Role, 
        neuer_rang: discord.Role, 
        grund: str
    ):
        await interaction.response.defer()
        lc = self.get_listen_cog()
        user_id = str(mitarbeiter.id)

        if user_id in lc.daten["mitarbeiter"]:
            try:
                await mitarbeiter.add_roles(neuer_rang, reason="PPD System: Disziplinarmaßnahme")
                await mitarbeiter.remove_roles(alter_rang, reason="PPD System: Disziplinarmaßnahme")
                rollen_status = f"🟥 **Rollen-Update:** {neuer_rang.mention} zugewiesen, {alter_rang.mention} entzogen."
            except discord.Forbidden:
                rollen_status = f"⚠️ **System-Fehler:** Bot-Hierarchie unzureichend!"

            lc.daten["mitarbeiter"][user_id]["rang"] = ebene
            lc.daten["mitarbeiter"][user_id]["nummer"] = dienstnummer
            lc.save_data()
            
            embed = discord.Embed(title="⚠️ DISZIPLINARMASSNAHME | DEGRADIERUNG", color=discord.Color.from_rgb(231, 76, 60))
            embed.set_author(name="Dienstliche Bekanntmachung • Disziplinarbeschluss", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            inhalt = (
                f"📋 **Stammdaten des Beamten**\n• **Name:** {mitarbeiter.mention}\n• **Ebene:** `{ebene}`\n• **Dienstnummer:** `{ebene}-{dienstnummer}`\n\n"
                f"📉 **Dienstgradänderung**\n• **Alter Dienstgrad:** {alter_rang.mention}\n• **Neuer Dienstgrad:** {neuer_rang.mention}\n\n"
                f"📜 **Disziplinarischer Grund**\n*{grund}*\n\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n⚙️ **Automatische Protokollierung**\n{rollen_status}"
            )
            embed.add_field(name="​", value=inhalt, inline=False)
            embed.add_field(name="🖋️ Autorisierte Unterschrift", value=f"{interaction.user.mention}\n*Disziplinarausschuss PPD*", inline=True)
            embed.add_field(name="📅 Ausstellungsdatum", value=f"`{interaction.created_at.strftime('%d.%m.%Y - %H:%M')} Uhr`", inline=True)
            embed.set_thumbnail(url=mitarbeiter.display_avatar.url)
            embed.set_footer(text="🇩🇪 Geprüftes Dokument • PPD Bundeskartei", icon_url=self.bot.user.display_avatar.url)
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Dieser Nutzer war nicht im System registriert.", ephemeral=True)

    @app_commands.command(name="kündigung", description="Entlasse einen Mitarbeiter und entziehe ihm seine Dienstrolle.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def kuendigung(self, interaction: discord.Interaction, mitarbeiter: discord.Member, letzter_rang: discord.Role, grund: str):
        await interaction.response.defer()
        lc = self.get_listen_cog()
        user_id = str(mitarbeiter.id)

        if user_id in lc.daten["mitarbeiter"]:
            try:
                await mitarbeiter.remove_roles(letzter_rang, reason="PPD System: Kündigung")
                rollen_status = f"🔮 **Rollen-Update:** Dienstrolle {letzter_rang.mention} entfernt."
            except discord.Forbidden:
                rollen_status = f"⚠️ **System-Fehler:** Bot fehlen Berechtigungen."

            del lc.daten["mitarbeiter"][user_id]
            lc.save_data()
            
            embed = discord.Embed(title="❌ DIENSTBEENDIGUNG | ENTLASSUNG", color=discord.Color.from_rgb(155, 89, 182))
            embed.set_author(name="Dienstliche Bekanntmachung • Entlassungsurkunde", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            inhalt = (
                f"📋 **Stammdaten des Ex-Beamten**\n• **Name:** {mitarbeiter.mention}\n• **Letzter Dienstgrad:** {letzter_rang.mention}\n\n"
                f"📜 **Offizielle Begründung**\n*{grund}*\n\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n⚙️ **Automatische Protokollierung**\n{rollen_status}"
            )
            embed.add_field(name="​", value=inhalt, inline=False)
            embed.add_field(name="🖋️ Autorisierte Unterschrift", value=f"{interaction.user.mention}\n*Behördenleitung PPD*", inline=True)
            embed.add_field(name="📅 Ausstellungsdatum", value=f"`{interaction.created_at.strftime('%d.%m.%Y - %H:%M')} Uhr`", inline=True)
            embed.set_thumbnail(url=mitarbeiter.display_avatar.url)
            embed.set_footer(text="Geschlossene Akte • PPD Archiv", icon_url=self.bot.user.display_avatar.url)
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Mitarbeiter nicht in der Liste gefunden.", ephemeral=True)

    @app_commands.command(name="abteilungs-betritt", description="Füge einen Mitarbeiter einer Sonderabteilung hinzu.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def abt_betritt(self, interaction: discord.Interaction, mitarbeiter: discord.Member, abteilung: str, grund: str = "Zulassungsverfahren bestanden"):
        lc = self.get_listen_cog()
        user_id = str(mitarbeiter.id)

        if user_id in lc.daten["mitarbeiter"]:
            lc.daten["mitarbeiter"][user_id]["abteilung"] = abteilung
            lc.save_data()
            
            embed = discord.Embed(title="🔰 SONDERDIVISION | ZUWEISUNG", color=discord.Color.from_rgb(52, 152, 219))
            embed.set_author(name="Dienstliche Bekanntmachung • Versetzung", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            inhalt = f"📋 **Stammdaten des Beamten**\n• **Name:** {mitarbeiter.mention}\n• **Zugewiesene Division:** `{abteilung}`\n\n📜 **Qualifikationsgrund**\n*{grund}*"
            embed.add_field(name="​", value=inhalt, inline=False)
            embed.add_field(name="🖋️ Unterschrift Direktion", value=f"{interaction.user.mention}\n*Kommandantur*", inline=True)
            embed.add_field(name="📅 Datum", value=f"`{interaction.created_at.strftime('%d.%m.%Y')}`", inline=True)
            embed.set_thumbnail(url=mitarbeiter.display_avatar.url)
            embed.set_footer(text="Sondereinheiten • PPD Taktikakte", icon_url=self.bot.user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Der Mitarbeiter muss zuerst im System registriert sein (z.B. über /beförderung).", ephemeral=True)

    @app_commands.command(name="abteilungs-austritt", description="Entferne einen Mitarbeiter aus einer Abteilung.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def abt_austritt(self, interaction: discord.Interaction, mitarbeiter: discord.Member, grund: str = "Freiwillige Niederlegung / Rotation"):
        lc = self.get_listen_cog()
        user_id = str(mitarbeiter.id)

        if user_id in lc.daten["mitarbeiter"] and lc.daten["mitarbeiter"][user_id].get("abteilung"):
            alt_abt = lc.daten["mitarbeiter"][user_id]["abteilung"]
            lc.daten["mitarbeiter"][user_id]["abteilung"] = None
            lc.save_data()
            
            embed = discord.Embed(title="🚪 SONDERDIVISION | AUSTRITT", color=discord.Color.from_rgb(241, 196, 15))
            embed.set_author(name="Dienstliche Bekanntmachung • Rotationsbeschluss", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            inhalt = f"📋 **Stammdaten des Beamten**\n• **Name:** {mitarbeiter.mention}\n• **Ausgeschieden aus:** `{alt_abt}`\n\n📜 **Grund des Austritts**\n*{grund}*"
            embed.add_field(name="​", value=inhalt, inline=False)
            embed.add_field(name="🖋️ Unterschrift Direktion", value=f"{interaction.user.mention}\n*Kommandantur*", inline=True)
            embed.add_field(name="📅 Datum", value=f"`{interaction.created_at.strftime('%d.%m.%Y')}`", inline=True)
            embed.set_thumbnail(url=mitarbeiter.display_avatar.url)
            embed.set_footer(text="Sondereinheiten • PPD Taktikakte", icon_url=self.bot.user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Mitarbeiter hat keine Abteilung oder ist nicht im System.", ephemeral=True)

    @app_commands.command(name="weekly-insider", description="Erstellt die wöchentlichen Upranks über interaktive Auswahlmenüs.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: i.user.id)
    async def weekly_insider(self, interaction: discord.Interaction):
        view = WeeklyInsiderSetupView(interaction.user, self)
        await interaction.response.send_message(
            "**Wöchentliche Upranks erstellen**\n\nKlicke auf die Buttons unten, um Personen direkt aus der Discord-Nutzerliste auszuwählen.", 
            view=view, 
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(PersonalCog(bot))