import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class ListenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daten_pfad = "daten/personal.json"
        self.daten = self.load_data()

    def load_data(self):
        if not os.path.exists("daten"):
            os.makedirs("daten")
        if not os.path.exists(self.daten_pfad):
            return {"einstellungen": {"kanal_id": None}, "mitarbeiter": {}}
        try:
            with open(self.daten_pfad, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"einstellungen": {"kanal_id": None}, "mitarbeiter": {}}

    def save_data(self):
        with open(self.daten_pfad, "w", encoding="utf-8") as f:
            json.dump(self.daten, f, ensure_ascii=False, indent=4)

    # ==========================================
    # DIENSTNUMMERN-KANAL EINRICHTEN
    # ==========================================
    @app_commands.command(name="setup-liste", description="Legt den Kanal fest, in dem die Dienstnummernliste vollautomatisch aktuell gehalten wird.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setup_liste(self, interaction: discord.Interaction, kanal: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        
        self.daten["einstellungen"]["kanal_id"] = kanal.id
        self.save_data()
        
        await interaction.followup.send(f"✅ Der Kanal {kanal.mention} wurde erfolgreich als Dienstnummern-Verzeichnis eingerichtet!", ephemeral=True)
        # Direkt die Liste das erste Mal generieren
        await self.update_list_channel(interaction.guild)

    # ==========================================
    # DIESE FUNKTION GENERIERT DIE LISTE NEU
    # ==========================================
    async def update_list_channel(self, guild: discord.Guild):
        kanal_id = self.daten["einstellungen"].get("kanal_id")
        if not kanal_id:
            return
            
        kanal = guild.get_channel(int(kanal_id))
        if not kanal:
            return

        # Wir teilen die Beamten in ihre 4 Hauptebenen auf
        ebenen = {
            "BHL": [], # Behördenleitung
            "HD": [],  # Höherer Dienst
            "GD": [],  # Gehobener Dienst
            "MD": []   # Mittlerer Dienst
        }

        # Alle Mitarbeiter aus der JSON auslesen
        for u_id, info in self.daten["mitarbeiter"].items():
            member = guild.get_member(int(u_id))
            if not member:
                continue # Falls der Beamte den Server verlassen hat
                
            ebene_key = info.get("rang") # Das ist "BHL", "HD", "GD" oder "MD"
            if ebene_key in ebenen:
                ebenen[ebene_key].append({
                    "mention": member.mention,
                    "nummer": info.get("nummer", "00"),
                    "abteilung": info.get("abteilung")
                })

        # Innerhalb der Ebenen sortieren wir nach der Dienstnummer (01, 02, 03...)
        for key in ebenen:
            ebenen[key].sort(key=lambda x: x["nummer"])

        # Embed erstellen
        embed = discord.Embed(
            title="🇩🇪 POLIZEIPRÄSIDIUM DIREKTION | BEAMTENVERZEICHNIS", 
            description="Übersicht aller aktiven Beamten im Dienstverhältnis. Automatisch aktualisiert durch die Personalabteilung.\n\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", 
            color=discord.Color.from_rgb(41, 128, 185)
        )
        embed.set_author(name="Bundesrepublik Deutschland • Polizeidatenbank", icon_url=guild.icon.url if guild.icon else None)

        # Übersetzungen für die Embed-Felder
        titel_mapping = {
            "BHL": "💼 BEHÖRDENLEITUNG",
            "HD": "🦅 HÖHERER POLIZEIDIENST",
            "GD": "⭐ GEHOBENER POLIZEIDIENST",
            "MD": "🛡️ MITTLERER POLIZEIDIENST"
        }

        # Die Kategorien dem Embed hinzufügen
        for ebene_key, beamte in ebenen.items():
            feld_inhalt = ""
            if beamte:
                for b in beamte:
                    # Falls eine Sonderabteilung eingetragen ist, zeigen wir sie an
                    abt_str = f" | `➔ {b['abteilung']}`" if b['abteilung'] else ""
                    feld_inhalt += f"• `Nrn. {b['nummer']}` ➔ {b['mention']}{abt_str}\n"
            else:
                feld_inhalt = "*Aktuell keine Beamten in dieser Ebene aktiv.*"
                
            embed.add_field(name=titel_mapping[ebene_key], value=feld_inhalt + "\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", inline=False)

        embed.set_footer(text="Stand der Kartei • Echtzeit-Synchronisierung aktiv", icon_url=self.bot.user.display_avatar.url)

        # Alten Bot-Post suchen oder neu posten, um Spam zu vermeiden
        letzte_nachricht = None
        async for msg in kanal.history(limit=5):
            if msg.author.id == self.bot.user.id and msg.embeds:
                letzte_nachricht = msg
                break

        if letzte_nachricht:
            await letzte_nachricht.edit(embed=embed)
        else:
            await kanal.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ListenCog(bot))