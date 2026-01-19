import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import botzone
from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig
import argparse
import sys
import os
import json
from bot_info import LV4_CONFIG_LIST


def runMatch(env, bots):
    env.init(bots)
    score = env.reset()
    env.render()
    while score is None:
        score = env.step()
        env.render()
    else:
        print("Score:", score)


def testLocalLandlordBot():
    game = "FightTheLandlord"
    print(f"Testing {game} with Local LLM Bot)...")

    # Define Local Bot Config
    # We use userfile_path to ensure the config file (and other assets) are available to the bot
    llm_bot_config = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/landlord/llm_bot.py",
        extension="py39",
        simpleio=False,
        keep_running=False,
        userfile_path="../api_config",
    )

    # Define Opponent (Simple Random Bot)
    opponent_config = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/landlord/llm_bot.py",
        extension="py39",
        simpleio=False,
        keep_running=False,
        userfile_path="../api_config",
    )

    sample_config = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/landlord/sample.py",
        extension="py39",
        simpleio=False,
        keep_running=False,
        userfile_path="../api_config",
    )

    try:
        env = botzone.make("FightTheLandlord-v0")

        # Create Bots
        import random

        k = random.randint(0, 2)
        bot1 = Bot(LV4_CONFIG_LIST["FightTheLandlord"][0])
        bot2 = Bot(LV4_CONFIG_LIST["FightTheLandlord"][1])
        # bot3 = Bot(BotConfig.fromID("5aefb5aca5858d0880e4b138"))
        bot3 = Bot(LV4_CONFIG_LIST["FightTheLandlord"][3])
        if k == 0:
            bots = [bot1, bot2, bot3]
            print("LLM is playing as Landlord, player 0")
        elif k == 1:
            bots = [bot2, bot3, bot1]
            print("LLM is playing as Peasant, player 2")
        else:
            bots = [bot3, bot1, bot2]
            print("LLM is playing as Peasant, player 1")

        runMatch(env, bots)

    finally:
        if "env" in locals():
            env.close()
        if "bots" in locals():
            for bot in bots:
                bot.close()


if __name__ == "__main__":
    testLocalLandlordBot()
    # testLocalLandlordBot("qwen")
