import discord
from discord.ext import commands
from discord import app_commands
import database as db
from ufc_scraper import METHODS
import logging

logger = logging.getLogger(__name__)

# ─── VIEWS (boutons interactifs) ──────────────────────────────────────────────

class FighterSelectView(discord.ui.View):
    """Choix du gagnant pour un combat"""
    
    def __init__(self, fight: dict):
        super().__init__(timeout=None)
        self.fight = fight
        
        # Bouton Fighter 1
        btn1 = discord.ui.Button(
            label=fight["fighter1"],
            style=discord.ButtonStyle.red,
            emoji="🥊",
            custom_id=f"fighter_{fight['id']}_1"
        )
        btn1.callback = self.make_callback(fight["fighter1"])
        self.add_item(btn1)
        
        # Bouton Fighter 2
        btn2 = discord.ui.Button(
            label=fight["fighter2"],
            style=discord.ButtonStyle.blurple,
            emoji="🥊",
            custom_id=f"fighter_{fight['id']}_2"
        )
        btn2.callback = self.make_callback(fight["fighter2"])
        self.add_item(btn2)
    
    def make_callback(self, fighter_name):
        async def callback(interaction: discord.Interaction):
            # Sauvegarder le prono basique (juste le gagnant)
            db.save_prono(
                interaction.user.id,
                interaction.user.display_name,
                self.fight["id"],
                fighter_name
            )
            
            # Proposer de choisir la méthode
            view = MethodSelectView(self.fight, fighter_name)
            await interaction.response.send_message(
                f"✅ Tu as choisi **{fighter_name}** !\n"
                f"Veux-tu aussi prédire la méthode de victoire ? *(optionnel, bonus de points)*",
                view=view,
                ephemeral=True
            )
        return callback


class MethodSelectView(discord.ui.View):
    """Choix de la méthode de victoire"""
    
    def __init__(self, fight: dict, picked_fighter: str):
        super().__init__(timeout=120)
        self.fight = fight
        self.picked_fighter = picked_fighter
        
        methods = [
            ("KO/TKO", "💥", discord.ButtonStyle.danger),
            ("Soumission", "🤼", discord.ButtonStyle.success),
            ("Décision", "📋", discord.ButtonStyle.secondary),
        ]
        
        for method, emoji, style in methods:
            btn = discord.ui.Button(label=method, emoji=emoji, style=style)
            btn.callback = self.make_callback(method)
            self.add_item(btn)
        
        # Bouton "Passer"
        skip_btn = discord.ui.Button(label="Passer", style=discord.ButtonStyle.secondary, emoji="⏭️", row=1)
        skip_btn.callback = self.skip_callback
        self.add_item(skip_btn)
    
    def make_callback(self, method):
        async def callback(interaction: discord.Interaction):
            # Si décision, pas de round
            if method == "Décision":
                db.save_prono(
                    interaction.user.id,
                    interaction.user.display_name,
                    self.fight["id"],
                    self.picked_fighter,
                    method,
                    None
                )
                await interaction.response.edit_message(
                    content=f"🎯 Prono enregistré !\n**{self.picked_fighter}** par **{method}**",
                    view=None
                )
            else:
                # Proposer le round
                view = RoundSelectView(self.fight, self.picked_fighter, method)
                await interaction.response.edit_message(
                    content=f"✅ Méthode : **{method}** !\nVeux-tu prédire le round ? *(bonus points)*",
                    view=view
                )
        return callback
    
    async def skip_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=f"✅ Prono enregistré : **{self.picked_fighter}** (sans méthode)",
            view=None
        )


class RoundSelectView(discord.ui.View):
    """Choix du round"""
    
    def __init__(self, fight: dict, picked_fighter: str, picked_method: str):
        super().__init__(timeout=120)
        self.fight = fight
        self.picked_fighter = picked_fighter
        self.picked_method = picked_method
        
        max_rounds = fight.get("max_rounds", 3)
        
        for r in range(1, max_rounds + 1):
            btn = discord.ui.Button(
                label=f"Round {r}",
                style=discord.ButtonStyle.primary,
                emoji="🔔"
            )
            btn.callback = self.make_callback(r)
            self.add_item(btn)
        
        skip_btn = discord.ui.Button(label="Passer", style=discord.ButtonStyle.secondary, emoji="⏭️", row=1)
        skip_btn.callback = self.skip_callback
        self.add_item(skip_btn)
    
    def make_callback(self, round_num):
        async def callback(interaction: discord.Interaction):
            db.save_prono(
                interaction.user.id,
                interaction.user.display_name,
                self.fight["id"],
                self.picked_fighter,
                self.picked_method,
                round_num
            )
            await interaction.response.edit_message(
                content=f"🎯 **Prono complet enregistré !**\n"
                        f"**{self.picked_fighter}** par **{self.picked_method}** au **Round {round_num}**\n"
                        f"*(+2 pts bonus si tu vises juste 🎯)*",
                view=None
            )
        return callback
    
    async def skip_callback(self, interaction: discord.Interaction):
        db.save_prono(
            interaction.user.id,
            interaction.user.display_name,
            self.fight["id"],
            self.picked_fighter,
            self.picked_method,
            None
        )
        await interaction.response.edit_message(
            content=f"✅ Prono enregistré : **{self.picked_fighter}** par **{self.picked_method}**",
            view=None
        )


class VoirMonPronoView(discord.ui.View):
    """Bouton pour voir son propre prono"""
    
    def __init__(self, fight_id: int):
        super().__init__(timeout=None)
        self.fight_id = fight_id
    
    @discord.ui.button(label="Voir mon prono", style=discord.ButtonStyle.secondary, emoji="👁️")
    async def voir_prono(self, interaction: discord.Interaction, button: discord.ui.Button):
        prono = db.get_prono(interaction.user.id, self.fight_id)
        if not prono:
            await interaction.response.send_message("Tu n'as pas encore fait de prono pour ce combat !", ephemeral=True)
        else:
            parts = [f"🥊 **{prono['picked_fighter']}**"]
            if prono["picked_method"]:
                parts.append(f"⚡ {prono['picked_method']}")
            if prono["picked_round"]:
                parts.append(f"🔔 Round {prono['picked_round']}")
            await interaction.response.send_message(
                f"Ton prono : {' | '.join(parts)}", ephemeral=True
            )


# ─── COG PRONOS ───────────────────────────────────────────────────────────────

class Pronos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ─── /poster_pronos ───────────────────────────────────────
    @app_commands.command(name="poster_pronos", description="📣 Poster les boutons de vote pour l'événement actif")
    @app_commands.checks.has_permissions(administrator=True)
    async def poster_pronos(self, interaction: discord.Interaction):
        event_id = db.get_setting("active_event_id")
        if not event_id:
            await interaction.response.send_message("❌ Aucun événement actif.", ephemeral=True)
            return
        
        channel_id = db.get_setting("prono_channel_id")
        if not channel_id:
            await interaction.response.send_message(
                "❌ Canal non configuré. Utilise `/setup` d'abord.", ephemeral=True
            )
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            await interaction.response.send_message("❌ Canal introuvable.", ephemeral=True)
            return
        
        fights = db.get_fights_for_event(int(event_id))
        if not fights:
            await interaction.response.send_message("❌ Aucun combat dans cet événement.", ephemeral=True)
            return
        
        # Message d'introduction
        event = None
        conn_event = __import__("database").get_connection()
        c = conn_event.cursor()
        c.execute("SELECT * FROM events WHERE id = ?", (int(event_id),))
        row = c.fetchone()
        conn_event.close()
        if row:
            event = dict(row)
        
        intro_embed = discord.Embed(
            title=f"🥊 {event['name'] if event else 'Événement UFC'}",
            description=(
                f"📅 {event['date'] if event else ''} | 📍 {event['location'] if event else ''}\n\n"
                "**Faites vos pronos avant le début des combats !**\n"
                "🔴 / 🔵 = Choisir le gagnant\n"
                "⚡ = Méthode (optionnel, **+1 pt**)\n"
                "🎯 = Round exact (optionnel, **+2 pts**)"
            ),
            color=discord.Color.red()
        )
        intro_embed.set_footer(text="Système de pronos UFC • Les votes sont privés !")
        await channel.send(embed=intro_embed)
        
        # Un message par combat
        for fight in fights:
            is_main = fight.get("is_main_event", False)
            title = f"{'👑 MAIN EVENT — ' if is_main else ''}**{fight['fighter1']}** 🆚 **{fight['fighter2']}**"
            
            embed = discord.Embed(
                title=title,
                color=discord.Color.gold() if is_main else discord.Color.blurple()
            )
            
            if fight.get("weight_class"):
                embed.add_field(name="⚖️ Catégorie", value=fight["weight_class"], inline=True)
            embed.add_field(name="🔔 Rounds max", value=str(fight["max_rounds"]), inline=True)
            embed.set_footer(text=f"Combat #{fight['id']} • Clique sur un combattant pour voter !")
            
            view = FighterSelectView(fight)
            await channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(
            f"✅ {len(fights)} combats postés dans {channel.mention} !", ephemeral=True
        )

    # ─── /mon_prono ───────────────────────────────────────────
    @app_commands.command(name="mon_prono", description="👁️ Voir tous tes pronos pour l'événement actif")
    async def mon_prono(self, interaction: discord.Interaction):
        event_id = db.get_setting("active_event_id")
        if not event_id:
            await interaction.response.send_message("Aucun événement actif.", ephemeral=True)
            return
        
        fights = db.get_fights_for_event(int(event_id))
        if not fights:
            await interaction.response.send_message("Aucun combat trouvé.", ephemeral=True)
            return
        
        embed = discord.Embed(title="🗳️ Tes pronos", color=discord.Color.blue())
        
        for fight in fights:
            prono = db.get_prono(interaction.user.id, fight["id"])
            if prono:
                val = f"🥊 **{prono['picked_fighter']}**"
                if prono["picked_method"]:
                    val += f" | ⚡ {prono['picked_method']}"
                if prono["picked_round"]:
                    val += f" | 🔔 R{prono['picked_round']}"
                embed.add_field(
                    name=f"{fight['fighter1']} vs {fight['fighter2']}",
                    value=val, inline=False
                )
            else:
                embed.add_field(
                    name=f"{fight['fighter1']} vs {fight['fighter2']}",
                    value="*Pas encore de prono*", inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ─── /stats_combat ────────────────────────────────────────
    @app_commands.command(name="stats_combat", description="📊 Stats des pronos pour un combat (admin)")
    @app_commands.checks.has_permissions(administrator=True)
    async def stats_combat(self, interaction: discord.Interaction, combat_id: int):
        pronos = db.get_pronos_for_fight(combat_id)
        if not pronos:
            await interaction.response.send_message("Aucun prono pour ce combat.", ephemeral=True)
            return
        
        from collections import Counter
        fighters = Counter(p["picked_fighter"] for p in pronos)
        
        embed = discord.Embed(title=f"📊 Stats combat #{combat_id}", color=discord.Color.orange())
        embed.add_field(name="Total votes", value=str(len(pronos)), inline=False)
        for fighter, count in fighters.most_common():
            pct = int(count / len(pronos) * 100)
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            embed.add_field(name=fighter, value=f"{bar} {pct}% ({count} votes)", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Pronos(bot))
