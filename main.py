import os
import discord
import mysql.connector
import random
from discord.ext import commands
from datetime import datetime, timedelta

# Connect to MySQL database
mydb = mysql.connector.connect(
    host="localhost",
    user="myuser",
    password="mypassword",
    database="mydatabase"
)

# Create a new instance of the client
intents = discord.Intents().all()
client = commands.Bot(command_prefix='!', intents=intents)

# Default cooldown time (6 hours)
default_cooldown_time = timedelta(hours=6)

# Dictionary to store cooldowns for each user
user_cooldowns = {}

# Event listener for when the bot is ready
@client.event
async def on_ready():
    print("Bot is ready.")

# Command for drawing a random card
@client.command()
async def draw(ctx):
    discuserid = ctx.author.id
    cursor = mydb.cursor()
    cursor.execute("SELECT card_name, card_ID, image_link, color FROM cards ORDER BY RAND() LIMIT 1;")
    result = cursor.fetchone()
    name, card_id, image_url, color_hex = result
    color = discord.Colour(int(color_hex, 16))  # Convert hex string to integer and create Colour object
    embed = discord.Embed(title=f"You got {name}!", description=f"ID {card_id}!", color=color)
    embed.set_image(url=image_url)
    
    # Check if the server has a cooldown time set in the database
    cursor.execute("SELECT cooldown_hours FROM server_cooldowns WHERE server_id = %s", (str(ctx.guild.id),))
    cooldown_result = cursor.fetchone()
    if cooldown_result is not None:
        cooldown_hours = cooldown_result[0]
        cooldown_time = timedelta(hours=cooldown_hours)
    else:
        cooldown_time = default_cooldown_time
    
    # Check if user is on cooldown
    if discuserid in user_cooldowns and datetime.now() < user_cooldowns[discuserid]:
        cooldown_time_remaining = user_cooldowns[discuserid] - datetime.now()
        await ctx.send(f"Sorry, you need to wait {cooldown_time_remaining} before drawing another card.")
        return
    
    # Add card to user's collection and set cooldown
    cursor.execute("INSERT INTO user_cards (user_id, card_id) VALUES (%s, %s)", (discuserid, card_id))
    mydb.commit()
    cursor.close()
    user_cooldowns[discuserid] = datetime.now() + cooldown_time
    
    await ctx.send(embed=embed)

@client.command()
async def view(ctx):
    discuserid = ctx.message.author.id
    mycursor = mydb.cursor()
    mycursor.execute("SELECT card_id FROM user_cards WHERE user_id = %s", (discuserid,))
    result = mycursor.fetchall()
    if len(result) == 0:
        await ctx.send("You don't have any cards yet!")
    else:
        embed = None
        for row in result:
            card_id = row[0]
            mycursor.execute("SELECT card_name, image_link, color FROM cards WHERE card_id = %s", (card_id,))
            card_info = mycursor.fetchone()
            card_name = card_info[0]
            card_image_url = card_info[1]
            color_hex = card_info[2]
            color = int(color_hex, 16)
            if embed is None:
                embed = discord.Embed(title="Your Cards", color=discord.Colour(color))
            embed.add_field(name=card_name, value=f"ID: {card_id}", inline=False)
            embed.set_thumbnail(url=card_image_url)
        await ctx.send(embed=embed)

# Command for setting the cooldown time
@client.command()
@commands.has_permissions(administrator=True)
async def setcooldown(ctx, hours: int):
    global default_cooldown_time
    default_cooldown_time = timedelta(hours=hours)

    for user_id in user_cooldowns:
        user_cooldowns[user_id] = datetime.now() + default_cooldown_time    
    
    # Store the cooldown time and server ID in the database
    cursor = mydb.cursor()
    cursor.execute("REPLACE INTO server_cooldowns (server_id, cooldown_hours) VALUES (%s, %s)", (str(ctx.guild.id), hours))
    mydb.commit()
    cursor.close()
    
    await ctx.send(f"The cooldown time has been set to {hours} hours.")

# Handle missing permissions error
@setcooldown.error
async def setcooldown_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use this command.")

@client.command()
async def erasecards(ctx):
    # Prompt the user for confirmation
    await ctx.send("Are you sure you want to erase your card database? This cannot be undone. Reply 'erase' to confirm.")
    
    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel and message.content.lower() == "erase"
    
    try:
        # Wait for the user's response
        await client.wait_for("message", check=check, timeout=30)
    except asyncio.TimeoutError:
        # If the user doesn't respond within 30 seconds, cancel the command
        await ctx.send("You took too long to respond. Command cancelled.")
        return
    
    # Delete the user's entries from the database
    cursor = mydb.cursor()
    cursor.execute("DELETE FROM user_cards WHERE user_id = %s", (ctx.author.id,))
    mydb.commit()
    cursor.close()
    
    await ctx.send("Your card database has been erased.")        

# Start the bot with your Discord bot token
client.run('---TOKEN GOES HERE---')
