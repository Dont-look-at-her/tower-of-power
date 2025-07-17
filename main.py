
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def faq(ctx):
    embed = discord.Embed(title="🧙 Tower of Power — FAQ", color=0x9370DB)
    embed.add_field(name="How to grow?", value="• Chat (+5 XP)\n• React (+2 XP)\n• Level up = +3ft\n• Win duels = steal height", inline=False)
    await ctx.send(embed=embed)

bot.run("YOUR_DISCORD_BOT_TOKEN")
