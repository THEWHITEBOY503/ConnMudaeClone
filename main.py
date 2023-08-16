import os
import discord
import mysql.connector
import random
import string
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import uuid
import traceback

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
client.remove_command('help')
# Default cooldown time (6 hours)
default_cooldown_time = timedelta(hours=6)
# Dictionary to store cooldowns for each user
user_cooldowns = {}
# Event listener for when the bot is ready
@client.event
async def on_ready():
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!help"))
    print("Bot is ready.")

@client.event
async def on_command_error(ctx, error):
    # Filter only the specific error
    error_message = str(error)
    print(error_message)
    if "is not found" in error_message:
        return
    if isinstance(error, commands.MissingPermissions) and str(error) == "You are missing Administrator permission(s) to run this command.":
        return
    
    # get the traceback of the error
    error_traceback = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    
    # find the last message that starts with "!"
    async for message in ctx.channel.history(limit=50, before=ctx.message, oldest_first=False):
        if message.content.startswith('!'):
            channel_id = message.channel.id
            break
    
    # send the error message to the channel that the last "!command" message was sent in
    if channel_id:
        channel = client.get_channel(channel_id)
        await channel.send(f"Whoops, that's an error! Please share this information with my developers:\n```{error_traceback}```")
    else:
        print("ERROR: ")
        print(error_traceback)
        
    

@client.command()
async def draw(ctx):
    mydb.reconnect()
    discuserid = ctx.author.id
    cursor = mydb.cursor()
    cursor.execute("SELECT card_name, card_ID, image_link, color, rarity FROM cards WHERE rarity > 0;")
    results = cursor.fetchall()
    total_rarity = sum(result[4] for result in results)
    rand_int = random.randint(0, total_rarity-1)
    cumulative_rarity = 0
    for result in results:
        cumulative_rarity += result[4]
        if rand_int < cumulative_rarity:
            name, card_id, image_url, color_hex, rarity = result
            break
    color = discord.Colour(int(color_hex, 16))  # Convert hex string to integer and create Colour object
    embed = discord.Embed(title=f"You got {name}!", description=f"ID {card_id}!", color=color)
    embed.set_image(url=image_url)
    # Generate draw ID
    draw_id = uuid.uuid4().hex  # Generate a random hexadecimal string
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
    cursor.execute("INSERT INTO user_cards (user_id, card_id, draw_id, is_top_card) VALUES (%s, %s, %s, 0)", (discuserid, card_id, draw_id))
    mydb.commit()
    cursor.close()
    user_cooldowns[discuserid] = datetime.now() + cooldown_time
    # Add draw ID to the footer
    embed.set_footer(text=f"Draw ID: {draw_id}")
    await ctx.send(embed=embed)

@client.command()
async def view(ctx, card_id=None, member: discord.Member = None):
    mydb.reconnect()
    mycursor = mydb.cursor()
    if card_id:
        mycursor.execute("SELECT card_name, card_id, image_link, color FROM cards WHERE card_id = %s", (card_id,))
        result = mycursor.fetchone()
        if not result:
            await ctx.send(f"Card with ID {card_id} does not exist.")
            return
        card_name = result[0]
        card_id = result[1]
        card_image_url = result[2]
        color_hex = result[3]
        color = int(color_hex, 16)
        embed = discord.Embed(title=card_name, description=f"ID: {card_id}")
        embed.set_image(url=card_image_url)
        embed.colour = discord.Colour(color)
        await ctx.send(embed=embed)
    else:
        discuserid = ctx.message.author.id if not member else member.id
        mycursor.execute("SELECT card_id, is_top_card, COUNT(*) as count FROM user_cards WHERE user_id = %s GROUP BY card_id, is_top_card ORDER BY is_top_card DESC", (discuserid,))
        result = mycursor.fetchall()
        if len(result) == 0:
            if not member:
                await ctx.send("You don't have any cards yet! :(")
            else:
                await ctx.send(f"{member.display_name} doesn't have any cards yet! :(")
        else:
            total_cards = len(result)
            current_page = 1
            cards_per_page = 5  # Number of cards to display per page
            embed = None

            def generate_embed(page):
                start_index = (page - 1) * cards_per_page
                end_index = min(start_index + cards_per_page, total_cards)
                embed = None
                top_card_image_url = None
                for i in range(start_index, end_index):
                    row = result[i]
                    card_id = row[0]
                    is_top_card = row[1]
                    count = row[2]
                    mycursor.execute("SELECT card_name, image_link, color FROM cards where card_id = %s", (card_id,))
                    card_info = mycursor.fetchone()
                    card_name = card_info[0]
                    card_image_url = card_info[1]
                    color_hex = card_info[2]
                    color = int(color_hex, 16)
                    if is_top_card:
                        top_card_image_url = card_image_url
                    if embed is None:
                        embed = discord.Embed(title=f"{member.display_name}'s Cards" if member else "Your Cards", color=discord.Colour(color))
                    embed.add_field(name=card_name, value=f"ID: {card_id} (x{count})", inline=False)           
                if top_card_image_url:
                    embed.set_thumbnail(url=top_card_image_url)
                else:
                    embed.set_thumbnail(url=card_image_url)
                
                embed.set_footer(text=f"Page {current_page}/{total_pages}")
                return embed

            total_pages = (total_cards + cards_per_page - 1) // cards_per_page
            embed = generate_embed(current_page)
            message = await ctx.send(embed=embed)
            if total_pages > 1:
                await message.add_reaction("⬅️")
                await message.add_reaction("➡️")

                def check(reaction, user):
                    return user == ctx.author and reaction.message.id == message.id and str(reaction.emoji) in ["⬅️", "➡️"]

                while True:
                    try:
                        reaction, user = await client.wait_for('reaction_add', timeout=60.0, check=check)
                    except asyncio.TimeoutError:
                        break
                    else:
                        if str(reaction.emoji) == "⬅️" and current_page > 1:
                            current_page -= 1
                        elif str(reaction.emoji) == "➡️" and current_page < total_pages:
                            current_page += 1
                        await message.remove_reaction(reaction, user)
                        embed = generate_embed(current_page)
                        await message.edit(embed=embed)
                        await asyncio.sleep(1)

# Command for setting the cooldown time
@client.command()
@commands.has_permissions(administrator=True)
async def setcooldown(ctx, hours: int):
    mydb.reconnect()
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
        await ctx.send("I'm sorry, but you don't have permission to run this command. You need to have the server administrator permission.")

@client.command()
async def erasecards(ctx):
    mydb.reconnect()
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

@client.command()
async def cardview(ctx, card_id=None):
    mydb.reconnect()
    mycursor = mydb.cursor()
    if card_id:
        mycursor.execute("SELECT card_name, card_id, image_link, color FROM cards WHERE card_id = %s", (card_id,))
        result = mycursor.fetchone()
        if not result:
            await ctx.send(f"Card with ID {card_id} does not exist.")
            return
        card_name = result[0]
        card_id = result[1]
        card_image_url = result[2]
        color_hex = result[3]
        color = int(color_hex, 16)
        embed = discord.Embed(title=card_name, description=f"ID: {card_id}")
        embed.set_image(url=card_image_url)
        embed.colour = discord.Colour(color)
        await ctx.send(embed=embed)
    else:
        isadmin = ctx.message.author.guild_permissions.administrator
        if isadmin == True:
            mycursor.execute("SELECT card_name, card_id, image_link, color FROM cards")
            result = mycursor.fetchall()
            total_cards = len(result)
            current_card = 1
            embed = None
            while True:
                row = result[current_card-1]
                card_name = row[0]
                card_id = row[1]
                card_image_url = row[2]
                color_hex = row[3]
                color = int(color_hex, 16)
                if embed is not None:
                    await message.delete()
                embed = discord.Embed(title="Server Cards", color=discord.Colour(color))
                embed.set_image(url=card_image_url)
                embed.add_field(name=card_name, value=f"ID: {card_id} | {current_card}/{total_cards}", inline=False)
                message = await ctx.send(embed=embed)
                if total_cards == 1:
                    break
                if current_card == 1:
                    await message.add_reaction("➡️")
                elif current_card == total_cards:
                    await message.add_reaction("⬅️")
                else:
                    await message.add_reaction("⬅️")
                    await message.add_reaction("➡️")
                def check(reaction, user):
                    return user == ctx.author and reaction.message.id == message.id and str(reaction.emoji) in ["⬅️", "➡️"]
                try:
                    reaction, user = await client.wait_for('reaction_add', timeout=60.0, check=check)
                except asyncio.TimeoutError:
                    break
                else:
                    if str(reaction.emoji) == "⬅️" and current_card > 1:
                        current_card -= 1
                    elif str(reaction.emoji) == "➡️" and current_card < total_cards:
                        current_card += 1
                    await message.remove_reaction(reaction, user)
                    await asyncio.sleep(1)  
        else:
            await ctx.send("I'm sorry, but you don't have permission to run this command. You need to have the server administrator permission.")

@client.command()
@commands.has_permissions(administrator=True)
async def addcard(ctx, card_name, image_link, color, rarity: int):
    mydb.reconnect()
    mycursor = mydb.cursor()
    while True:
        # Generate random 4-digit ID
        card_id = ''.join(random.choices(string.digits, k=4))
        # Check if ID already exists in database
        mycursor.execute("SELECT COUNT(*) FROM cards WHERE card_id = %s", (card_id,))
        result = mycursor.fetchone()
        if result[0] == 0:
            # ID is unique, break out of loop
            break
    sql = "INSERT INTO cards (card_name, card_id, image_link, color, rarity) VALUES (%s, %s, %s, %s, %s)"
    val = (card_name, card_id, image_link, color, rarity)
    mycursor.execute(sql, val)
    mydb.commit()
    await ctx.send(f"Card added: {card_name} (ID: {card_id})")
@addcard.error
async def addcard_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("I'm sorry, but you don't have permission to run this command. You need to have the server administrator permission.")

@client.command()
@commands.has_permissions(administrator=True)
async def removecard(ctx, card_id: int):
    mydb.reconnect()
    mycursor = mydb.cursor()
    try:
        mycursor.execute("DELETE FROM cards WHERE card_id = %s", (card_id,))
        mycursor.execute("DELETE FROM user_cards WHERE card_id = %s", (card_id,))
        mydb.commit()
        await ctx.send(f"Card with ID {card_id} has been removed.")
    except mysql.connector.Error as error:
        await ctx.send(f"Failed to remove card with ID {card_id}. Error: {error}")
@removecard.error
async def removecard_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("I'm sorry, but you don't have permission to run this command. You need to have the server administrator permission.")

@client.command()
@commands.has_permissions(administrator=True)
async def remove(ctx, card_id: int, member: discord.Member = None):
    mydb.reconnect()
    member = member or ctx.author
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_cards WHERE user_id = %s AND card_id = %s", (member.id, card_id))
    result = cursor.fetchall()
    if not result:
        await ctx.send(f"{member.mention} doesn't have any cards with ID {card_id}.")
        return
    if len(result) == 1:
        cursor.execute("DELETE FROM user_cards WHERE user_id = %s AND card_id = %s", (member.id, card_id))
        mydb.commit()
        await ctx.send(f"{member.mention} has removed the card with ID {card_id}.")
        return
    # Select a random duplicate card with the given card_id
    card = random.choice(result)
    draw_id = card["draw_id"]
    cursor.execute("DELETE FROM user_cards WHERE user_id = %s AND card_id = %s AND draw_id = %s", (member.id, card_id, draw_id))
    mydb.commit()
    await ctx.send(f"{member.mention} has removed one of their cards with ID {card_id}.")
@remove.error
async def remove_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("I'm sorry, but you don't have permission to run this command. You need to have the server administrator permission.")

@client.command()
@commands.has_permissions(administrator=True)
async def add(ctx, card_id: int, member: discord.Member = None):
    mydb.reconnect()
    member = member or ctx.author
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cards WHERE card_id = %s", (card_id,))
    card = cursor.fetchone()
    if not card:
        await ctx.send(f"Sorry, the card with ID {card_id} does not exist in the database.")
        return
    cursor.execute("SELECT * FROM user_cards WHERE user_id = %s AND card_id = %s", (member.id, card_id))
    result = cursor.fetchall()
    if result:
        await ctx.send(f"{member.mention} already has the card with ID {card_id}.")
        return
    draw_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO user_cards (user_id, card_id, draw_id) VALUES (%s, %s, %s)", (member.id, card_id, draw_id))
    mydb.commit()
    if member == ctx.author:
        await ctx.send(f"{member.mention}, you have added the card with ID {card_id} to your collection.")
    else:
        await ctx.send(f"{ctx.author.mention} has added the card with ID {card_id} to {member.mention}'s collection.")
@add.error
async def add_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("I'm sorry, but you don't have permission to run this command. You need to have the server administrator permission.")

@client.command()
async def bias(ctx, card_id: int):
    mydb.reconnect()
    discuserid = ctx.message.author.id
    mycursor = mydb.cursor()
    mycursor.execute("SELECT card_id FROM user_cards WHERE user_id = %s", (discuserid,))
    result = mycursor.fetchall()
    if len(result) == 0:
        await ctx.send("You don't have any cards yet!")
    elif card_id not in [row[0] for row in result]:
        await ctx.send("You don't have that card in your collection!")
    else:
        mycursor.execute("UPDATE user_cards SET is_top_card = FALSE WHERE user_id = %s AND is_top_card = TRUE", (discuserid,))
        mycursor.execute("UPDATE user_cards SET is_top_card = TRUE WHERE user_id = %s AND card_id = %s", (discuserid, card_id))
        mydb.commit()
        await ctx.send(f"Your top card has been updated to card ID {card_id}!")

@client.command()
async def resetbias(ctx):
    mydb.reconnect()
    discuserid = ctx.message.author.id
    mycursor = mydb.cursor()
    mycursor.execute("UPDATE user_cards SET is_top_card = 0 WHERE user_id = %s AND is_top_card = 1", (discuserid,))
    mydb.commit()
    if mycursor.rowcount > 0:
        await ctx.send("Your top card has been reset!")
    else:
        await ctx.send("You don't have a top card set.")

@client.command()
async def trade(ctx, card_id: int, member: discord.Member = None):
    mydb.reconnect()
    mycursor = mydb.cursor()
    sender_id = ctx.author.id
    if member is not None:
        recipient_id = member.id
    else:
        await ctx.send("Please tag the user you want to trade with.")
        return
    # check if sender has multiple cards with the same ID
    mycursor.execute("SELECT draw_id FROM user_cards WHERE user_id = %s AND card_id = %s", (sender_id, card_id))
    cards = mycursor.fetchall()
    if len(cards) > 1:
        # select a random card to trade
        card_to_trade = random.choice(cards)[0]
    elif len(cards) == 1:
        card_to_trade = cards[0][0]
    else:
        await ctx.send(f"You don't have any cards with ID {card_id}.")
        return
    await ctx.send(f"{member.mention}, {ctx.author.mention} wants to trade card ID {card_id} with you. Please respond with the card ID you wish to trade, or type `decline` to decline.")
    def check(message):
        return message.author == member and message.channel == ctx.channel
    try:
        msg = await client.wait_for('message', check=check, timeout=30.0)
        if msg.content.lower() == 'decline':
            await ctx.send('Trade declined.')
        else:
            card_id_2 = int(msg.content)
            # check if recipient has multiple cards with the same ID
            mycursor.execute("SELECT draw_id FROM user_cards WHERE user_id = %s AND card_id = %s", (recipient_id, card_id_2))
            recipient_cards = mycursor.fetchall()
            if len(recipient_cards) > 1:
                # select a random card to trade
                recipient_card_to_trade = random.choice(recipient_cards)[0]
            elif len(recipient_cards) == 1:
                recipient_card_to_trade = recipient_cards[0][0]
            else:
                await ctx.send(f"{member.mention} doesn't have any cards with ID {card_id_2}.")
                return
            # perform the trade
            mycursor.execute("SELECT card_name FROM cards WHERE card_id = %s", [card_id])
            result = mycursor.fetchone()
            sendingcard = result[0]
            mycursor.execute("SELECT card_name FROM cards WHERE card_id = %s", [card_id_2])
            result = mycursor.fetchone()
            receivingcard = result[0]
            await ctx.send(f"{ctx.author.mention}, you are giving your {sendingcard} (ID: {card_id}) for {member.mention}'s {receivingcard} (ID: {card_id_2}). Do you accept? (Reply yes or no)")

            def check_author(m):
                return m.author == ctx.author

            try:
                msg = await client.wait_for('message', check=check_author, timeout=60.0)
            except asyncio.TimeoutError:
                await ctx.send("Trade response timeout.")
            else:
                if msg.content.lower() == 'no':
                    await ctx.send('Trade declined.')
                elif msg.content.lower() == 'yes':
                    mycursor.execute("UPDATE user_cards SET user_id = %s WHERE user_id = %s AND card_id = %s AND draw_id = %s", (recipient_id, sender_id, card_id, card_to_trade))
                    mycursor.execute("UPDATE user_cards SET user_id = %s WHERE user_id = %s AND card_id = %s AND draw_id = %s", (sender_id, recipient_id, card_id_2, recipient_card_to_trade))
                    mydb.commit()
                    await ctx.send(f"Trade complete! {ctx.author.mention} now has card ID {card_id_2}, and {member.mention} has card ID {card_id}.")
    except asyncio.TimeoutError:
        await ctx.send(f'{member.mention} did not respond in time. Trade cancelled.')

@client.command()
async def gift(ctx, card_id: int, member: discord.Member = None):
    mydb.reconnect()
    mycursor = mydb.cursor()
    sender_id = ctx.author.id
    if member is not None:
        recipient_id = member.id
    else:
        await ctx.send("Please tag the user you want to gift a card to.")
        return
    # check if sender has the card
    mycursor.execute("SELECT draw_id FROM user_cards WHERE user_id = %s AND card_id = %s", (sender_id, card_id))
    cards = mycursor.fetchall()
    if len(cards) == 0:
        await ctx.send(f"You don't have any cards with ID {card_id}.")
        return
    # confirm the gift
    await ctx.send(f"Are you sure you want to gift card ID {card_id} to {member.mention}? (Reply yes or no)")
    def check_author(m):
      return m.author == ctx.author
    try:
        msg = await client.wait_for('message', check=check_author, timeout=60.0)
    except asyncio.TimeoutError:
        await ctx.send("Gift confirmation timeout.")
    else:
        if msg.content.lower() == 'no':
            await ctx.send('Gift cancelled.')
        elif msg.content.lower() == 'yes':
            # gift the card
            mycursor.execute("UPDATE user_cards SET user_id = %s WHERE user_id = %s AND card_id = %s AND draw_id = %s", (recipient_id, sender_id, card_id, cards[0][0]))
            mydb.commit()
            await ctx.send(f"You have gifted card ID {card_id} to {member.mention}.")



@client.command()
async def help(ctx):
    embed = discord.Embed(title="List of Commands", color=discord.Colour(0x00FF00))
    embed.add_field(name="!draw", value="Draw a random card from the deck.", inline=False)
    embed.add_field(name="!view", value="View your card collection.", inline=False)
    embed.add_field(name="!setcooldown <Hours>", value="Set the cooldown time between draws.[ADMIN]", inline=False)
    embed.add_field(name="!erasecards", value="Erase your entire card collection.", inline=False)
    embed.add_field(name="!cardview <Optional card ID>", value="View details about a specific card, if specified, otherwise display the server deck.", inline=False)
    embed.add_field(name="!addcard \"<Name>\" \"<Link>\" \"<Color [0xFFFFFF Format]>\" <Rarity>", value="Add a card to the deck. [ADMIN]", inline=False)
    embed.add_field(name="!removecard <CardID>", value="Remove a card from the deck. [ADMIN]", inline=False)
    embed.add_field(name="!editcard <CardID> \"<Name>\" \"<Link>\" \"<Color [0xFFFFFF Format]>\" <Rarity>", value="Edits a card in the database. [ADMIN]", inline=False)
    embed.add_field(name="!remove <CardID> <Optional Member>", value="Remove a card from someone's collection. If no user is specified, it will be removed from your own. [ADMIN]", inline=False)
    embed.add_field(name="!add <CardID> <Optional Member>", value="Add a card to someone's collection. If no user is specified, it will be added to your own. [ADMIN]", inline=False)
    embed.add_field(name="!bias <CardID>", value="Sets a card to be shown on top of your card list.", inline=False)
    embed.add_field(name="!resetbias", value="Resets your top card.", inline=False)
    embed.add_field(name="!trade <CardID> @Member", value="Trade a card with another member.", inline=False)
    embed.add_field(name="!help", value="Displays this message.", inline=False)
    embed.add_field(name="!gift <CardID> @Member", value="Gift a card to a user of your choice.", inline=False)
    embed.add_field(name="!license", value="Display information about PulaCard's open-source MIT license", inline=False)
    embed.set_footer(text="Want to report a bug, send a feature request, or get instructions to make your own PulaCard instance? Come find us on GitHub! https://github.com/THEWHITEBOY503/ConnMudaeClone       For information on the MIT license, run !license.        Written with <3 by Conner S. 2023. Thank you for using PulaCard.")
    await ctx.send(embed=embed)

@client.command()
@commands.has_permissions(administrator=True)
async def wipe(ctx):
    await ctx.send("!!!!WARNING!!!! THIS WILL COMPLETELY WIPE THE BOTS DATABASE. THIS ACTION CANNOT BE REVERSED. PLEASE MAKE SURE YOU UNDERSTAND WHAT YOU ARE DOING. ARE YOU ABSOLUTELY SURE THIS IS WHAT YOU WANT TO DO? REPLY `goodbye` TO CONFIRM.")
    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel and message.content.lower() == "goodbye"
    try:
        await client.wait_for("message", check=check, timeout=30)
    except asyncio.TimeoutError:
        await ctx.send("You took too long to respond. Command cancelled.")
        return
    cursor = mydb.cursor()
    cursor.execute("DELETE FROM cards")
    cursor.execute("DELETE FROM user_cards")
    cursor.execute("DELETE FROM server_cooldowns")
    mydb.commit()
    cursor.close()
    await ctx.send("All records erased. Thank you for using this bot. We hope to see your continued support. <3")

@client.command()
async def license(ctx):
    await ctx.send("MIT License \n \n Copyright (c) 2023 Conner Smith \n \n Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the \"Software\"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: \n \n The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. \n \n THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.")

@client.command()
@commands.has_permissions(administrator=True)
async def editcard(ctx, card_id=None, card_name=None, image_link=None, color=None, rarity=None):
    if card_id is None or card_name is None or image_link is None or color is None or rarity is None:
        await ctx.send("Missing one or more required arguments. Usage: !editcard card_id card_name image_link color rarity")
        return
    mydb.reconnect()
    mycursor = mydb.cursor()
    if card_id:
        mycursor.execute("SELECT card_id FROM cards WHERE card_id = %s", (card_id,))
        result = mycursor.fetchone()
        if not result:
            await ctx.send(f"Card with ID {card_id} does not exist.")
            return
        sql = "UPDATE cards SET card_name = %s, card_id = %s, image_link = %s, color = %s, rarity = %s WHERE card_ID = %s"
        val = (card_name, card_id, image_link, color, rarity, card_id)
        mycursor.execute(sql, val)
        mydb.commit()
        await ctx.send(f"Card updated: {card_name} (ID: {card_id})")
@editcard.error
async def editcard_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("I'm sorry, but you don't have permission to run this command. You need to have the server administrator permission.")
                
# Start the bot with your Discord bot token
client.run('---YOUR TOKEN HERE---')
