import discord
from discord.ext import commands
from discord import app_commands
import database as db
from ufc_scraper import get_next_event, METHODS
import logging

logger = logging.getLogger(__name__)


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_admin():
        async def predicate(interaction: discord.Interaction):
            return interaction.user.guild_permissions.administrator
        return app_commands.check(predicate)

    # ─── /setup ───────────────────────────────────────────────
    @app_commands.command(name="setup", description="🔧 Définir le canal des pronos UFC")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction, canal: discord.TextChannel):
        db.set_setting("prono_channel_id", str(canal.id))
        await interaction.response.send_message(
            f"✅ Canal des pronos défini sur {canal.mention} !", ephemeral=True
        )

    # ─── /charger_event ───────────────────────────────────────
    @app_commands.command(name="charger_event", description="🥊 Charger automatiquement le prochain événement UFC")
    @app_commands.checks.has_permissions(administrator=True)
    async def charger_event(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        await interaction.followup.send("🔍 Récupération de l'événement UFC en cours...", ephemeral=True)
        
        event = await get_next_event()
        
        if not event:
            await interaction.followup.send(
                "❌ Impossible de récupérer l'événement UFC. Essaie `/creer_event` pour le créer manuellement.",
                ephemeral=True
            )
            return
        
        if not event.get("fights"):
            await interaction.followup.send(
                f"⚠️ Événement trouvé (**{event['name']}**) mais aucun combat récupéré. "
                f"Essaie `/creer_event` pour le créer manuellement.",
                ephemeral=True
            )
            return
        
        # Sauvegarder l'événement
        event_id = db.save_event(event["name"], event["date"], event.get("location", ""))
        db.set_event_status(event_id, "active")
        db.set_setting("active_event_id", str(event_id))
        
        # Sauvegarder les combats
        for fight in event["fights"]:
            db.save_fight(
                event_id,
                fight["fighter1"],
                fight["fighter2"],
                fight.get("weight_class", ""),
                fight.get("is_main_event", False),
                fight.get("max_rounds", 3),
                fight.get("position", 0)
            )
        
        await interaction.followup.send(
            f"✅ **{event['name']}** chargé avec **{len(event['fights'])} combats** !\n"
            f"📅 {event['date']} | 📍 {event.get('location', 'N/A')}\n\n"
            f"Utilise `/poster_pronos` pour poster les boutons de vote dans le canal.",
            ephemeral=True
        )

    # ─── /creer_event ─────────────────────────────────────────
    @app_commands.command(name="creer_event", description="✍️ Créer manuellement un événement UFC")
    @app_commands.checks.has_permissions(administrator=True)
    async def creer_event(self, interaction: discord.Interaction, nom: str, date: str, lieu: str = ""):
        event_id = db.save_event(nom, date, lieu)
        db.set_event_status(event_id, "active")
        db.set_setting("active_event_id", str(event_id))
        await interaction.response.send_message(
            f"✅ Événement **{nom}** créé ! (ID: {event_id})\n"
            f"Utilise `/ajouter_combat` pour ajouter les combats.",
            ephemeral=True
        )

    # ─── /ajouter_combat ──────────────────────────────────────
    @app_commands.command(name="ajouter_combat", description="➕ Ajouter un combat manuellement")
    @app_commands.checks.has_permissions(administrator=True)
    async def ajouter_combat(
        self,
        interaction: discord.Interaction,
        fighter1: str,
        fighter2: str,
        categorie: str = "",
        rounds_max: int = 3,
        main_event: bool = False
    ):
        event_id = db.get_setting("active_event_id")
        if not event_id:
            await interaction.response.send_message("❌ Aucun événement actif. Crée d'abord un événement.", ephemeral=True)
            return
        
        db.save_fight(int(event_id), fighter1, fighter2, categorie, main_event, rounds_max)
        await interaction.response.send_message(
            f"✅ Combat ajouté : **{fighter1}** vs **{fighter2}** ({rounds_max} rounds)", ephemeral=True
        )

    # ─── /resultat ────────────────────────────────────────────
    @app_commands.command(name="resultat", description="🏆 Entrer le résultat d'un combat")
    @app_commands.checks.has_permissions(administrator=True)
    async def resultat(
        self,
        interaction: discord.Interaction,
        combat_id: int,
        gagnant: str,
        methode: str,
        round_fin: int = 0
    ):
        db.set_fight_result(combat_id, gagnant, methode, round_fin)
        results = db.calculate_and_save_points(combat_id)
        
        # Poster les résultats dans le canal
        channel_id = db.get_setting("prono_channel_id")
        if channel_id:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                embed = discord.Embed(
                    title="🏆 Résultat du combat !",
                    color=discord.Color.gold()
                )
                embed.add_field(name="🥊 Gagnant", value=f"**{gagnant}**", inline=True)
                embed.add_field(name="⚡ Méthode", value=methode, inline=True)
                if round_fin:
                    embed.add_field(name="🔔 Round", value=str(round_fin), inline=True)
                
                if results:
                    winners_text = ""
                    for r in sorted(results, key=lambda x: x["points"], reverse=True):
                        if r["points"] > 0:
                            badges = ""
                            if r["correct_winner"]: badges += "✅"
                            if r["correct_method"]: badges += "⚡"
                            if r["correct_round"]: badges += "🎯"
                            winners_text += f"{badges} <@{r['user_id']}> — **+{r['points']} pts**\n"
                    
                    if winners_text:
                        embed.add_field(name="🎉 Points gagnés", value=winners_text, inline=False)
                
                await channel.send(embed=embed)
        
        await interaction.response.send_message(
            f"✅ Résultat enregistré pour le combat #{combat_id}. Points calculés pour {len(results)} participants.",
            ephemeral=True
        )

    # ─── /liste_combats ───────────────────────────────────────
    @app_commands.command(name="liste_combats", description="📋 Voir les combats de l'événement actif")
    @app_commands.checks.has_permissions(administrator=True)
    async def liste_combats(self, interaction: discord.Interaction):
        event_id = db.get_setting("active_event_id")
        if not event_id:
            await interaction.response.send_message("❌ Aucun événement actif.", ephemeral=True)
            return
        
        fights = db.get_fights_for_event(int(event_id))
        if not fights:
            await interaction.response.send_message("Aucun combat trouvé.", ephemeral=True)
            return
        
        text = ""
        for f in fights:
            status = "✅" if f["winner"] else "⏳"
            text += f"{status} **#{f['id']}** — {f['fighter1']} vs {f['fighter2']} ({f['max_rounds']} rds)\n"
        
        await interaction.response.send_message(f"**Combats de l'événement :**\n{text}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Admin(bot))
