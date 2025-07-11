import discord
import json
import random
import os
import time
from typing import Optional
from discord.ext import commands

# Get Discord bot token from environment variable
TOKEN = os.getenv('TOKEN') or os.getenv('DISCORD_BOT_TOKEN') or 'YOUR_BOT_TOKEN_HERE'

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Initialize data storage
user_data = {}

def load_data():
    """Load user data from JSON file"""
    global user_data
    try:
        with open('tower_data.json', 'r') as f:
            user_data = json.load(f)
        print(f"✅ Loaded data for {len(user_data)} users")
    except FileNotFoundError:
        user_data = {}
        print("📁 Created new data file")
    except json.JSONDecodeError:
        user_data = {}
        print("⚠️ Data file corrupted, starting fresh")

def save_data():
    """Save user data to JSON file"""
    try:
        with open('tower_data.json', 'w') as f:
            json.dump(user_data, f, indent=2)
    except Exception as e:
        print(f"❌ Failed to save data: {e}")

def calculate_level(xp):
    """Calculate level based on total XP with progressive requirements"""
    if xp < 100:
        return 1
    
    total_xp_needed = 0
    level = 1
    
    while total_xp_needed <= xp:
        level += 1
        # Each level requires 50 more XP than the previous, capped at 500 XP per level
        xp_for_next_level = min(50 + (level - 2) * 50, 500)
        total_xp_needed += xp_for_next_level
        
        if total_xp_needed > xp:
            level -= 1
            break
    
    return max(1, level)

def xp_required_for_next_level(current_xp):
    """Calculate XP needed for next level"""
    current_level = calculate_level(current_xp)
    
    # Calculate total XP needed for next level
    total_xp_needed = 0
    level = 1
    
    while level <= current_level:
        level += 1
        xp_for_level = min(50 + (level - 2) * 50, 500)
        total_xp_needed += xp_for_level
    
    return total_xp_needed - current_xp

def calculate_height(user_id):
    """Calculate tower height with base, bonus, and level components"""
    if user_id not in user_data:
        return 5  # Default base height
    
    user = user_data[user_id]
    base_height = user.get("base_height", 5)
    bonus_height = user.get("bonus_height", 0)
    user_xp = user.get("xp", 0)
    level = calculate_level(user_xp)
    level_height = (level - 1) * 3  # 3 feet per level above 1
    
    return base_height + bonus_height + level_height

def get_title(level):
    """Get title based on user level"""
    titles = [
        "Peasant", "Apprentice", "Builder", "Craftsman", "Architect",
        "Master Builder", "Tower Lord", "Sky Reacher", "Cloud Walker", "Storm Touched",
        "Heaven's Engineer"
    ]
    
    if level <= len(titles):
        return titles[level - 1]
    else:
        # Dynamic titles for levels beyond predefined
        return f"Celestial Architect Lv.{level}"

def get_tower_flavor(height):
    """Get flavor text based on tower height"""
    if height <= 10:
        return "A modest foundation, every tower starts somewhere."
    elif height <= 25:
        return "Your tower begins to cast a shadow."
    elif height <= 50:
        return "Impressive! Your tower dominates the skyline."
    elif height <= 100:
        return "Magnificent! Your tower pierces the clouds."
    elif height <= 200:
        return "Legendary! Your tower reaches toward the heavens."
    else:
        return "DIVINE! Your tower challenges the gods themselves!"

def init_user(user_id):
    """Initialize new user data if not exists"""
    if user_id not in user_data:
        user_data[user_id] = {
            "xp": 0,
            "base_height": 5,
            "bonus_height": 0,
            "wins": 0,
            "losses": 0,
            "welcomed": False,
            "height_timestamp": time.time(),
            "previous_height": 5
        }

def update_height_timestamp(user_id):
    """Update timestamp if user reached a new height"""
    if user_id in user_data:
        current_height = calculate_height(user_id)
        previous_height = user_data[user_id].get("previous_height", 5)
        
        if current_height > previous_height:
            user_data[user_id]["height_timestamp"] = time.time()
            user_data[user_id]["previous_height"] = current_height

async def add_xp(user, amount, channel):
    """Add XP to user and handle level ups"""
    user_id = str(user.id)
    init_user(user_id)
    
    old_level = calculate_level(user_data[user_id]["xp"])
    user_data[user_id]["xp"] += amount
    new_level = calculate_level(user_data[user_id]["xp"])
    
    # Check for level up
    if new_level > old_level:
        height = calculate_height(user_id)
        title = get_title(new_level)
        flavor = get_tower_flavor(height)
        
        embed = discord.Embed(
            title="🎉 Level Up!",
            description=f"**{user.display_name}** has reached **Level {new_level}**!",
            color=0x00FF7F
        )
        embed.add_field(
            name="New Title",
            value=f"*{title}*",
            inline=True
        )
        embed.add_field(
            name="Tower Stats",
            value=f"**Tower Height:** {height}ft\n*\"{flavor}\"*"
        )
        
        await channel.send(embed=embed)
    
    # Update height timestamp for leaderboard ordering
    update_height_timestamp(user_id)
    save_data()

@bot.event
async def on_ready():
    """Event handler for when bot comes online"""
    # Record start time for uptime calculation
    if not hasattr(bot, 'start_time'):
        bot.start_time = time.time()  # type: ignore
    
    print(f'🏰 Tower of Power Bot is online as {bot.user}')
    print(f'Bot is connected to {len(bot.guilds)} guild(s)')
    
    # Send welcome message to the first available channel
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name in ['tower-of-power', 'general', 'bot-commands'] and channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send("⚡ Your Tower's Power has been Activated!")
                    print(f"✅ Welcome message sent to #{channel.name} in {guild.name}")
                    break
                except Exception as e:
                    print(f"⚠️ Could not send welcome message to {guild.name}: {e}")

@bot.event
async def on_message(message):
    """Event handler for messages - awards XP for activity"""
    if message.author.bot:
        return
    
    # Award 1 XP for sending a message
    await add_xp(message.author, 1, message.channel)
    
    # Process commands
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    """Event handler for reactions - awards XP for engagement"""
    if user.bot:
        return
    
    # Award 2 XP for adding a reaction
    await add_xp(user, 2, reaction.message.channel)

@bot.command(name='towerstats')
async def towerstats(ctx, target: Optional[discord.Member] = None):
    """Display tower statistics for yourself or another user"""
    # Use target user if provided, otherwise use command author
    if target:
        user_id = str(target.id)
        display_user = target
    else:
        user_id = str(ctx.author.id)
        display_user = ctx.author
    
    init_user(user_id)
    user = user_data[user_id]
    
    xp = user["xp"]
    level = calculate_level(xp)
    height = calculate_height(user_id)
    title = get_title(level)
    flavor = get_tower_flavor(height)
    wins = user["wins"]
    losses = user["losses"]
    xp_needed = xp_required_for_next_level(xp)
    
    embed = discord.Embed(
        title=f"🏰 {display_user.display_name}'s Tower",
        color=0x7289DA
    )
    embed.add_field(
        name="📊 Stats",
        value=f"**Level:** {level}\n**Title:** *{title}*\n**XP:** {xp}\n**Next Level:** {xp_needed} XP needed",
        inline=True
    )
    embed.add_field(
        name="🏗️ Tower",
        value=f"**Height:** {height}ft\n**Record:** {wins}W - {losses}L",
        inline=True
    )
    embed.add_field(
        name="💭 Tower Essence",
        value=f"*\"{flavor}\"*",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='challenge')
async def challenge(ctx, target: discord.Member):
    """Challenge another user to a tower duel"""
    attacker_id = str(ctx.author.id)
    defender_id = str(target.id)
    
    init_user(attacker_id)
    init_user(defender_id)
    
    attacker_height = calculate_height(attacker_id)
    defender_height = calculate_height(defender_id)
    
    # Validation checks
    if attacker_id == defender_id:
        await ctx.send("❌ You can't challenge yourself, even in the Tower of Power.")
        return
    
    # Get leaderboard to check for special ranking rules (sorted by height, then by timestamp)
    def sort_key(user_item):
        user_id, stats = user_item
        height = calculate_height(user_id)
        timestamp = stats.get("height_timestamp", float('inf'))
        return (-height, timestamp)
    
    leaderboard = sorted(user_data.items(), key=sort_key)
    first_place_id = leaderboard[0][0] if leaderboard else None
    second_place_id = leaderboard[1][0] if len(leaderboard) > 1 else None
    third_place_id = leaderboard[2][0] if len(leaderboard) > 2 else None
    
    # Check challenge permissions
    can_challenge = False
    
    # Special rule: 2nd place can always challenge 1st place
    if attacker_id == second_place_id and defender_id == first_place_id:
        can_challenge = True
    # Special rule: 3rd place can always challenge 2nd place
    elif attacker_id == third_place_id and defender_id == second_place_id:
        can_challenge = True
    # Special rule: anyone can challenge 3rd place
    elif defender_id == third_place_id:
        can_challenge = True
    # Regular rule: can only challenge equal or smaller towers
    elif attacker_height >= defender_height:
        can_challenge = True
    
    if not can_challenge:
        if defender_id == first_place_id:
            await ctx.send("❌ Only the 2nd place player can challenge the tower king!")
        elif defender_id == second_place_id:
            await ctx.send("❌ Only the 3rd place player can challenge the 2nd place holder!")
        else:
            await ctx.send("❌ You can only challenge someone with equal or smaller tower height.")
        return

    # Random battle outcome (50/50 chance)
    winner, loser = (ctx.author, target) if random.choice([True, False]) else (target, ctx.author)
    winner_id = str(winner.id)
    loser_id = str(loser.id)
    
    # Calculate stolen height (everything above base 5ft)
    loser_height = calculate_height(loser_id)
    stolen = loser_height - 5

    # Update winner's bonus height
    if "bonus_height" not in user_data[winner_id]:
        user_data[winner_id]["bonus_height"] = 0
    user_data[winner_id]["bonus_height"] += stolen
    
    # Update height timestamp for winner (they gained height)
    update_height_timestamp(winner_id)
    
    # Reset loser's tower height but preserve XP and level
    loser_xp = user_data[loser_id]["xp"]  # Preserve current XP
    user_data[loser_id] = {
        "xp": loser_xp,  # Keep their earned XP and level
        "base_height": 5,
        "bonus_height": 0,
        "wins": user_data[loser_id]["wins"],
        "losses": user_data[loser_id]["losses"] + 1,
        "welcomed": True,
        "height_timestamp": time.time(),  # Reset timestamp since they're back to base height
        "previous_height": 5  # Reset previous height tracking
    }

    # Update win/loss records
    user_data[winner_id]["wins"] += 1

    # Create battle result embed
    embed = discord.Embed(
        title="⚔️ Tower Duel Results",
        color=0xFF6B6B
    )
    embed.add_field(
        name="Victory!", 
        value=f"**{winner.display_name}** has defeated **{loser.display_name}**!", 
        inline=False
    )
    embed.add_field(
        name="Spoils of War", 
        value=f"**{winner.display_name}** absorbs {stolen}ft and rises even higher.", 
        inline=False
    )
    loser_level = calculate_level(user_data[loser_id]["xp"])
    embed.add_field(
        name="The Fallen", 
        value=f"**{loser.display_name}** returns to a humble 5ft base but keeps their Level {loser_level} experience 😔", 
        inline=False
    )
    
    await ctx.send(embed=embed)
    save_data()

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    """Display the top 10 tower heights"""
    if not user_data:
        await ctx.send("📊 No towers have been built yet! Start chatting to gain XP.")
        return
    
    # Sort by height (descending), then by timestamp (ascending - who reached it first)
    def sort_key(user_item):
        user_id, stats = user_item
        height = calculate_height(user_id)
        timestamp = stats.get("height_timestamp", float('inf'))
        return (-height, timestamp)
    
    sorted_users = sorted(user_data.items(), key=sort_key)
    top_10 = sorted_users[:10]
    
    embed = discord.Embed(
        title="🏆 Tower Leaderboard",
        description="Top 10 Tallest Towers",
        color=0xFFD700
    )
    
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    
    for i, (user_id, stats) in enumerate(top_10):
        try:
            user = bot.get_user(int(user_id))
            username = user.display_name if user else f"User {user_id}"
        except:
            username = f"User {user_id}"
        
        height = calculate_height(user_id)
        level = calculate_level(stats["xp"])
        title = get_title(level)
        
        embed.add_field(
            name=f"{medals[i]} #{i+1}",
            value=f"**{username}**\n{height}ft tall\nLevel {level} *{title}*",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command(name='resetme')
async def resetme(ctx):
    """Reset user's tower to starting stats"""
    user_id = str(ctx.author.id)
    
    user_data[user_id] = {
        "xp": 0,
        "base_height": 5,
        "bonus_height": 0,
        "wins": 0,
        "losses": 0,
        "welcomed": True,
        "height_timestamp": time.time(),
        "previous_height": 5
    }
    
    save_data()
    await ctx.send(f"🔄 **{ctx.author.display_name}**, your tower has been reset to humble beginnings. Time to rebuild!")

@bot.command(name='ping')
async def ping_command(ctx):
    """Display bot latency and uptime information"""
    import time
    
    # Calculate bot latency
    latency = round(bot.latency * 1000)  # Convert to milliseconds
    
    # Calculate uptime (bot started when it came online)
    if hasattr(bot, 'start_time'):
        uptime_seconds = time.time() - bot.start_time  # type: ignore
        uptime_hours = uptime_seconds / 3600
        uptime_days = int(uptime_hours // 24)
        uptime_hours_remaining = int(uptime_hours % 24)
        uptime_minutes = int((uptime_seconds % 3600) / 60)
        
        if uptime_days > 0:
            uptime_str = f"{uptime_days}d {uptime_hours_remaining}h {uptime_minutes}m"
        elif uptime_hours_remaining > 0:
            uptime_str = f"{uptime_hours_remaining}h {uptime_minutes}m"
        else:
            uptime_str = f"{uptime_minutes}m"
    else:
        uptime_str = "Unknown"
    
    # Determine connection quality
    if latency < 100:
        status_emoji = "🟢"
        status_text = "Excellent"
    elif latency < 200:
        status_emoji = "🟡"
        status_text = "Good"
    else:
        status_emoji = "🔴"
        status_text = "Poor"
    
    embed = discord.Embed(
        title="🏓 Bot Status",
        color=0x00FF7F
    )
    embed.add_field(
        name="Latency",
        value=f"{status_emoji} {latency}ms ({status_text})",
        inline=True
    )
    embed.add_field(
        name="Uptime",
        value=f"⏰ {uptime_str}",
        inline=True
    )
    embed.add_field(
        name="Status",
        value="🏰 Tower Power Active!",
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.command(name='faq')
async def help_command(ctx):
    """Display bot commands and information"""
    embed = discord.Embed(
        title="🏰 Tower of Power - Help",
        description="Build the tallest tower through activity and strategic duels!",
        color=0x7289DA
    )
    
    embed.add_field(
        name="📈 Gaining XP & Height",
        value="• **Chat messages:** +1 XP\n• **Reactions:** +2 XP\n• **Level up:** +3ft per level\n• **Win duels:** Absorb opponent's bonus height",
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Duel Rules",
        value="• Challenge equal/smaller towers\n• 2nd place can challenge 1st\n• 3rd place can challenge 2nd\n• Anyone can challenge 3rd\n• Loser keeps XP/level, loses bonus height",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Commands",
        value="• `!towerstats` - Your tower info\n• `!towerstats @user` - View another's tower\n• `!challenge @user` - Start a duel\n• `!leaderboard` - Top 10 towers\n• `!resetme` - Reset your progress\n• `!ping` - Bot status",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required argument. Use `!faq` for help.")
    else:
        await ctx.send("❌ Something went wrong. Please try again.")
        print(f"Command error: {error}")

# Load data and run bot
if __name__ == "__main__":
    load_data()
    
    if TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Please set your Discord bot token in the TOKEN environment variable")
    else:
        print("🏰 Starting Tower of Power Bot...")
        try:
            bot.run(TOKEN)
        except discord.LoginFailure:
            print("❌ Invalid token. Please check your Discord bot token.")
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")