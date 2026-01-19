import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import botzone
from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig


def runMatch(env, bots):
    env.init(bots)
    score = env.reset()
    env.render()
    while score is None:
        score = env.step()
        env.render()
    else:
        print("Score:", score)


def testLocalLLMBot():
    game = "TicTacToe"
    print(f"Testing {game} with Local LLM Bot...")

    # Define Local Bot Config
    llm_bot_config = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/tictactoe/llm_bot.py",  # Updated path
        extension="py39",  # Python 3.9 environment (has openai)
        simpleio=False,
        keep_running=False,
        userfile_path="../api_config",
    )

    # Define Opponent (Local Simple Bot)
    opponent_config = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/tictactoe/llm_bot.py",
        extension="py39",
        simpleio=False,
        keep_running=False,
        userfile_path="../api_config",
    )

    sample_config = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/tictactoe/sample.py",
        extension="py39",
        simpleio=False,
        keep_running=False,
        userfile_path="../api_config",
    )

    try:
        env = botzone.make("TicTacToe-v0")

        # Create Bots
        import random

        k = random.randint(0, 1)
        bot1 = Bot(BotConfig.fromID("61ef619c3e8ab26550ccf094"))
        bot2 = Bot(BotConfig.fromID("630729d85f9ce709a6007539"))

        bots = [bot1, bot2] if k == 0 else [bot2, bot1]

        print("Starting Match: Sample Bot vs LLM Bot")
        print("LLM is playing as O" if k == 0 else "LLM is playing as X")
        runMatch(env, bots)

    finally:
        if "env" in locals():
            env.close()
        if "bot1" in locals():
            bot1.close()
        if "bot2" in locals():
            bot2.close()


if __name__ == "__main__":
    print("=== Testing Local LLM Bot (Priority) ===")
    testLocalLLMBot()

    # Optional: Uncomment to test other parts
    # print("\n=== Testing Standard Bots ===")
    # testBot()
    # print("\n=== Testing Game Logic ===")
    # testGame()
