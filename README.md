
# ConnMudaeClone

This bot is an open-source Discord card game, similar to Mudae. It allows you to draw a card every X hours (default 6), and even trade cards with your friends.

## Commands
### Any commands marked with [ADMIN] require the "Server Administrator" permission to be run. 

 - `!draw`
 Draw a random card from the deck.

- `!view`
View your card collection.

- `!setcooldown <Hours>`
Set the cooldown time between draws. **[ADMIN]**

- `!erasecards`
Erase your entire card collection.

- `!cardview <Optional card ID>`
View details about a specific card, if specified, otherwise display the server deck.

- `!addcard "<Name>" "<Link>" "<Color [0xFFFFFF Format]>" <Rarity>`
Add a card to the deck. You'll need to specify a name for your card, an image link, a color for your card (in 0xFFFFFF HTML color format), and a rarity level 0-16, with 16 being the most rare, 1 being the most, and 0 being manual assignment only. **[ADMIN]**

- `!removecard <CardID>`
Remove a card from the deck. **[ADMIN]**

- `!remove <CardID> <Optional Member>`
Remove a card from someone's collection. If no user is specified, it will be removed from your own. **[ADMIN]**

- `!add <CardID> <Optional Member>`
Add a card to someone's collection. If no user is specified, it will be added to your own. **[ADMIN]**

- `!bias <CardID>`
Sets a card to be shown on top of your card list.

- `!resetbias`
Resets your top card.

- `!trade <CardID> @Member`
Trade a card with another member.
## Dependancies
This application needs MySQL to function correctly. [You can find installation instructions for your system here.](https://dev.mysql.com/doc/mysql-installation-excerpt/5.7/en/) You also need Python (Obviously) and the `discord.py` package, which can be installed with `pip install discord.py`
## Database structure
This bot requires a MySQL database to run. You will need three tables, `cards`, `uesr_cards`, and `server_cooldowns`, 
`cards` needs these columns: `card_name` varchar(255), `card_ID` int, `image_link` varchar(255), `color` varchar(255), `rarity` int
`user_cards` needs these columns: `user_id` bigint, `card_id` int, `draw_id` varchar(255), `is_top_card` varchar(100)
`server_cooldowns` needs two columns: `server_id` bigint, `cooldown_hours` int
## Installation
This section is under construction. Please check again later.
## Progress

### Bot Completed as of 3/18/23
Final testing and debugging is currently in progress, before I call the bot "finished"
## Feature suggestions

### To suggest further features, please open a request under "Issues".
Opening an issue request for each individual feature request helps me keep track of my progress on them a lot better. 

### For bug reports, please open a request under "Issues".
If you can, mark it with the "Bug" label so I can sort it better. I'll post comments to your thread and assign any additional tags as they are needed. 

### If you'd like to contribute, please feel free to make a pull request!
Even though this project is marked as "Completed", there's always room for improvement! I'd love to see and ideas or changes you may have!

## Attributions
This project was written with the assistance of ChatGPT, a large language model trained by [OpenAI](https://openai.com/). [(Their GitHub)](https://github.com/openai)

## Licensing
This project is licensed under the MIT license. It's free, but I'm sure you knew that, given that it's open-source and freely available on GitHub. If you'd like to put your own spin on this project, please feel absolutely free to! However, this software is provided "as-is", with no warranty of any kind, express or implied. For more information on the MIT license as it applies to this project, [Please see the licensing file here.](https://github.com/THEWHITEBOY503/ConnMudaeClone/blob/main/LICENSE)
