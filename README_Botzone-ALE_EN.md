# Botzone-ALE

This project aims to build a general-purpose multi-agent game environment while being able to interface with existing games and bots on Botzone.

## Background
Botzone is an online program versus platform that offers a series of games. Users can submit their own programs (referred to as Bots) and create game tables to have their Bots automatically compete against others. This can be used in courses or competition groups for running batch matches.

However, since all matches on the platform take place online, it can be inconvenient in the following scenarios:

* A user develops two versions of a Bot and wants to run multiple matches to compare their performance. On the website, they can only manually create game tables repeatedly.

* A user is developing a Bot and needs to fix bugs iteratively. On the website, they have to repeatedly upload new versions of the Bot and run matches.

* A user wants to train a learning-based Bot. The current online matchmaking method does not support function-call-based agents, nor does it allow efficient data collection. Users often have to implement a local game environment themselves for agent training.

Therefore, the goal of this library is to provide a localized, offline-capable Botzone environment for running matches locally.

Differences between this library and the previous Botzone Local Debugger:

* In the Botzone Local Debugger, although the local program runs locally, each round requires sending a request to the server to invoke the game judge program on the server. It does not achieve fully local match execution and is less efficient.

* In the Botzone Local Environment, both the game judge program and the user's Bot are downloaded locally, enabling complete match execution on the user's host with high efficiency.

## Introduction
The initial purpose of this project was to support running Botzone-style matches locally. However, in its specific implementation and for the sake of scalability, we have developed it into a general-purpose multi-agent game environment library. Specifically:

* It defines the universal interface specifications for the game environment (Env) and agent (Agent) in multi-agent game scenarios, allowing matches to be run with very concise code.

* Users can develop new environments that comply with the interface specifications, or implement custom agents (e.g., for algorithm research).

* By running the game judge program and Bot programs within a lightweight sandbox (Docker), this library directly supports the existing games and Bots available online and wraps them into components that conform to the aforementioned universal interface specifications.

* To improve the efficiency of the game environment, the judge programs for various online games have been re-implemented in Python within this library. Users can use these implementations to replace the wrapped online game environments, significantly boosting the efficiency of local matches.

## Usage

### Installation

Environment Requirement: Python 3.8+

After cloning the repo, you need to install the dependencies
```
git clone https://github.com/AMysteriousBeing/Botzone-ALE.git
cd Botzone-ALE
pip install -r requirements.txt
```

### Using Online Games and Bots
To support online Bots, you first need to install Docker (for creating a local sandbox to run the code) and Node.js (for supporting simple interactions).

Users can easily run matches using existing online games and Bots. A concise example is provided below:
```
try:
	# Create an environment named NoGo
	from botzone.online.game import Game, GameConfig
	env = Game(GameConfig.fromName('NoGo'))
	# Create 2 bot instances，ID: 5fede20fd9383f7579afff06（This is the sample Bot）
	from botzone.online.bot import Bot, BotConfig
	bots = [Bot(BotConfig.fromID('5fede20fd9383f7579afff06')) for i in range(env.player_num)]
	# Assign bots for the game
	env.init(bots)
	# Start evaluation and rendering
	score = env.reset()
	env.render()
	while score is None:
		score = env.step() # At the end of the run, step will return players' scores in the form of tuple
		env.render()
	print(score)
finally:
	# Need to ensure that Docker containers are killed after evaluation. Otherwise, the containers will remain. 
	env.close()
	for bot in bots: bot.close()
```

Some points to note:

- When using the sandbox to run a game or Bot for the first time, this library will prompt you to download the Docker image file. We have precompiled images for runtime environments of various programming languages, as well as a universal image that supports all languages, which is almost identical to the server evaluation environment. You can choose to download only the images for commonly used languages (relatively small in size) or opt for the universal image (around 12 GB).

- When attempting to create a Bot, this library will try to download the Bot code from the Botzone website and cache it in the default directory (`botzone/online/bot/`). You can change the cache path by passing the path parameter to BotConfig.

- Some Bots require reading from or writing to files in the user workspace during execution. You can enable this behavior by passing the userfile parameter to BotConfig. In such cases, this library will attempt to download user workspace data from the Botzone website and cache it in the default directory (`botzone/online/bot/user_id/`). You can change the cache path by passing the userfile_path parameter to BotConfig.

- Downloading non-public Bots and user workspace files requires user permissions. In such cases, this library will automatically prompt you to enter your email and password to log into your account.

### Environment

Botzone-ALE uses unique ID to identify differnent game environments. The following code is used to access environment instances:
```
import botzone
env = botzone.make('Ataxx-v0') # Ataxx Env in Python
```
It is the same as the following
```
from botzone.envs.botzone.ataxx import AtaxxEnv
env = AtaxxEnv()
```

All sandbox environments are wrapped with ID format similar to `GameName-wrap`，The complete list of environments supported by Botzone-ALE can be access by:```botzone.all()```，`botzone/envs` provides simple description for each environment.

### Self-defined Environment and Agents

This library implements unified environment and agent interfaces: `botzone/env.py` (Environment) and `botzone/agent.py` (Agent). Users can create custom environments and agents by simply inheriting from `botzone.Env` and `botzone.Agent`, enabling seamless interaction under a consistent interface framework.

In another use case, users may create Bot programs or game judge programs locally that are intended for upload to Botzone, but wish to debug them locally first. In such scenarios, users can manually construct `BotConfig` or `GameConfig` objects and use them to create Bots or Games that exist solely on the local machine. For detailed information, please refer to the documentation comments of the relevant classes: Bot: botzone/online/bot.py, Game: `botzone/online/game.py`.
