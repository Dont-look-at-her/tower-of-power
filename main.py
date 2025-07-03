
import discord
from discord.ext import commands
import os
import random

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("DISCORD_TOKEN")

# Example leaderboard and level tracking (simplified for demo)
user_data = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = str(message.author.id)
    if user_id not in user_data:
        user_data[user_id] = {"xp": 0, "level": 1, "height": 5}

    # XP gain logic
    user_data[user_id]["xp"] += 10
    xp_needed = min(500, user_data[user_id]["level"] * 50)
    if user_data[user_id]["xp"] >= xp_needed:
        user_data[user_id]["xp"] -= xp_needed
        user_data[user_id]["level"] += 1
        user_data[user_id]["height"] += 3
        await message.channel.send(embed=discord.Embed(
            title=f"📈 {message.author.display_name} has leveled up!",
            description=f"You are now Level {user_data[user_id]['level']}\nYour tower grows to {user_data[user_id]['height']}ft.",
            color=0x9B59B6
        ))

    await bot.process_commands(message)

@bot.command()
async def faq(ctx):
    faq_embed = discord.Embed(
        title="🔮 Tower of Power – FAQ",
        description=(
            "🧙‍♂️ Welcome, Seeker of Stature!\n\n"
            "📈 **Level Up** by messaging or reacting in the server.\n"
            "⚔️ **Duel** those with equal or lesser height to absorb their inches.\n"
            "🏆 **Leaderboards** track the tallest towers.\n"
            "😈 **3rd Place** is always vulnerable.\n"
            "🌩️ **Beware**: The Tower itself may punish greed...\n\n"
            "**Command List:**\n"
            "`!faq` – You're lookin' at it.\n"
            "`!towerstats` – View your current level and height.\n"
            "`!duel @user` – Battle for girth.\n"
            "`!leaderboard` – Witness the top towers."
        ),
        color=0x9B59B6
    )
    faq_embed.set_footer(text="Grow responsibly. Size isn't everything—but it helps.")
    await ctx.send(embed=faq_embed)

bot.run(TOKEN)
