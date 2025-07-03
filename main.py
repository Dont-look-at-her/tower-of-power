import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

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