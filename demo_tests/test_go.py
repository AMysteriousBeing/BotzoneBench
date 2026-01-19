import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import botzone
from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig
import json


def runMatch(env, bots):
    env.init(bots)
    score = env.reset()
    env.render()
    while score is None:
        score = env.step()
        env.render()
    else:
        print("Score:", score)

        # --- Debug Log Extraction ---
        # Check if the game ended with an error/non-normal status
        # env.display contains the history of turns.
        # The last item might have 'winner', 'verdict', or 'log' info.

        try:
            last_display = env.display[-1] if env.display else {}
            # If there was an error, the score is usually (0, 2) or (2, 0) but
            # we want to see WHY.

            # Unfortunately, env.display is formatted for the viewer.
            # The RAW execution logs (stderr) from the container are usually captured
            # by the Bot object wrapper or the sandbox.

            # In the local runner, we can try to peek into the bots' last result.
            # But the most reliable way in this local setup is to look at the
            # 'debug' field if it exists in the step result, OR just inspect the
            # recently killed container logs if we could (but they are killed).

            print("\n--- Match Debug Info ---")
            # Try to print the last few items of display which might contain error messages
            if len(env.display) > 0:
                print("Last Game Event:", env.display[-1])

        except Exception as e:
            print("Could not extract debug info:", e)


def testLocalGoBot():
    game = "Go"
    print(f"Testing {game} with Local LLM Bot...")

    # Define Local Bot Config
    llm_bot_config = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/go/go_llm.py",
        extension="py39",
        simpleio=False,
        keep_running=False,
        userfile_path="./",
    )

    # Define Opponent (Local Simple Bot)
    opponent_config = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/go/simple_go.py",
        extension="py39",
        simpleio=False,
        keep_running=False,
        userfile_path="./",
    )

    try:
        env = botzone.make("Go-v9")

        # Initialize bots with logging
        import random

        k = random.randint(0, 1)

        bot1 = Bot(llm_bot_config, log_path="llm_bot_prompts_go.log")
        bot2 = Bot(opponent_config)

        bots = [bot1, bot2] if k == 0 else [bot2, bot1]

        print("Starting Match: LLM Bot vs Simple Random Bot")
        print("LLM is playing as Black" if k == 0 else "LLM is playing as White")
        runMatch(env, bots)

    finally:
        if "env" in locals():
            env.close()
        if "bots" in locals():
            for bot in bots:
                bot.close()


if __name__ == "__main__":
    print("=== Testing Local Go LLM Bot ===")
    testLocalGoBot()
