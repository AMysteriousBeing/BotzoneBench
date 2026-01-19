import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import botzone
from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig
from bot_info import LV5_CONFIG_LIST, LV6_CONFIG_LIST


def runMatch(env, bots):
    env.init(bots)
    score = env.reset()
    env.render()
    while score is None:
        score = env.step()
        env.render()
    else:
        print("Score:", score)


def testLocalGomokuBot():
    game = "Gomoku"
    print(f"Testing {game} with Local LLM Bot...")

    # Define Local Bot Config
    llm_bot_config = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/gomoku/llm_bot.py",
        extension="py39",
        simpleio=False,
        keep_running=False,
        userfile_path="../api_config",
    )

    # Define Opponent (Local Simple Bot)
    opponent_config = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/gomoku/sample.py",
        extension="py39",
        simpleio=False,
        keep_running=False,
        userfile_path="./",
    )

    try:
        env = botzone.make("Gomoku-v15")  # v15 = 15x15 board

        # Create Bots
        # Player 1: Local LLM Bot
        # Player 2: Simple Local Bot
        import random

        k = random.randint(0, 1)
        # k = 1
        # bot1 = Bot(BotConfig.fromID("61cb50238d8bd011d779c378"))
        # bot2 = Bot(BotConfig.fromID("61c4d1428d8bd011d7748737"))
        bot1 = Bot(LV6_CONFIG_LIST["Gomoku"][0])
        bot2 = Bot(LV6_CONFIG_LIST["Gomoku"][1])

        bots = [bot1, bot2]

        print("Starting Match: LLM Bot vs Simple Random Bot")
        print("LLM is playing as Black")
        runMatch(env, bots)

    finally:
        if "env" in locals():
            env.close()
        if "bot1" in locals():
            bot1.close()
        if "bot2" in locals():
            bot2.close()


if __name__ == "__main__":
    print("=== Testing Local Gomoku LLM Bot ===")
    testLocalGomokuBot()
