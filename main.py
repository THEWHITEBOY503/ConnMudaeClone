import os
import discord
import mysql.connector
import random
import requests
from discord.ext import commands

# Connect to MySQL database
mydb = mysql.connector.connect(
    host="localhost",
    user="myuser",
    password="mypassword",
    database="mydatabase"
)

mycursor = mydb.cursor()


mycursor.execute("SELECT * FROM mytable")
result = mycursor.fetchall()

# Print the result
for x in result:
    print(x)

# Create a new instance of the client
intents = discord.Intents().all()
from discord.ext import commands

client = commands.Bot(command_prefix='!', intents=intents)

# Event listener for when the bot is ready
@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))

# Event listener for when a message is sent in any channel
@client.event
async def on_ready():
    print("Bot is ready.")

# Command for drawing a random card
@client.command()
async def draw(ctx):
    cursor = mydb.cursor()
    cursor.execute("SELECT name, ID, image_path FROM chars ORDER BY RAND() LIMIT 1;")
    result = cursor.fetchone()
    name, card_id, image_url = result
    embed = discord.Embed(title="PHOTOCARD PULL", description=f"You got {name} [ID {card_id}]!", color=0xff0000)

    # Download the image from the URL and save it to a file
    response = requests.get(image_url)
    image_path = "card_image.jpg"
    with open(image_path, "wb") as f:
        f.write(response.content)
    #print("image_path:", image_path)
    #print("response.content:", response.content)
    
    # Attach the file to the message
    #file = discord.File(image_path)
    #file = discord.File(image_path, filename="card_image.jpg")
    #embed.set_image(url=f"attachment://card_image.jpg")
    # Try setting the image URL directly from SQL, without downloading the image
    embed.set_image(url=image_url)
    
    #await ctx.send(file=file, embed=embed)
    await ctx.send(embed=embed)
    
    cursor.close()
# Start the bot with your Discord bot token
client.run('---TOKEN GOES HERE---')
