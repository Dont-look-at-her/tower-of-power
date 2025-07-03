
import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command()
async def faq(ctx):
    embed = discord.Embed(
        title="📜 Tower of Power — FAQ",
        description=(
            "💬 Message or 🧙‍♂️ React to grow your tower.\n"
            "⚔️ Duel others to absorb their height.\n"
            "🧱 Levels increase your tower.\n"
            "🎯 2nd place can challenge 1st.\n"
            "🔮 When the Tower wins… no one is safe."
        ),
        color=0x9b59b6
    )
    await ctx.send(embed=embed)

bot.run(os.environ['DISCORD_TOKEN'])
