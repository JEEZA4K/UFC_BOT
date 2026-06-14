import discord
from discord.ext import commands
from discord import app_commands
import database as db


class Classement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="classement", description="🏆 Voir le classement des pronos UFC")
    async def classement(self, interaction: discord.Interaction):
        leaderboard = db.get_leaderboard(15)
        
        if not leaderboard:
            await interaction.response.send_message(
                "Aucun prono enregistré pour le moment. Soyez les premiers à voter ! 🥊",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🏆 Classement des Pronos UFC",
            color=discord.Color.gold()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        text = ""
        
        for i, user in enumerate(leaderboard):
            medal = medals[i] if i < 3 else f"**{i+1}.**"
            win_rate = 0
            if user["total_pronos"] > 0:
                win_rate = int(user["correct_winner"] / user["total_pronos"] * 100)
            
            text += (
                f"{medal} **{user['username']}** — "
                f"**{user['total_points']} pts** "
                f"| ✅ {user['correct_winner']} victoires "
                f"| 🎯 {win_rate}% précision\n"
            )
        
        embed.description = text
        embed.set_footer(text="✅ Bon gagnant | ⚡ Bonne méthode | 🎯 Bon round")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mon_score", description="📊 Voir tes stats de pronos")
    async def mon_score(self, interaction: discord.Interaction):
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM leaderboard WHERE user_id = ?", (str(interaction.user.id),))
        row = c.fetchone()
        conn.close()
        
        if not row:
            await interaction.response.send_message(
                "Tu n'as encore fait aucun prono ! Vote sur les combats pour apparaître ici. 🥊",
                ephemeral=True
            )
            return
        
        user = dict(row)
        win_rate = int(user["correct_winner"] / user["total_pronos"] * 100) if user["total_pronos"] > 0 else 0
        
        embed = discord.Embed(
            title=f"📊 Stats de {interaction.user.display_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="🏆 Points totaux", value=str(user["total_points"]), inline=True)
        embed.add_field(name="🗳️ Total pronos", value=str(user["total_pronos"]), inline=True)
        embed.add_field(name="✅ Victoires correctes", value=str(user["correct_winner"]), inline=True)
        embed.add_field(name="⚡ Méthodes correctes", value=str(user["correct_method"]), inline=True)
        embed.add_field(name="🎯 Rounds corrects", value=str(user["correct_round"]), inline=True)
        embed.add_field(name="📈 Précision", value=f"{win_rate}%", inline=True)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Classement(bot))
