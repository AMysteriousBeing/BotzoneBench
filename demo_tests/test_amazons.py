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

def testLocalAmazonsWithLLM():
    samples = {
        "Amazons": "5bd136e00681335cc1f4d000",
    }

    envs = {
        "Amazons": "Amazons-v8",
    }

    game = "Amazons"
    print("Trying game", game)

    config_sample = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/amazons/sample.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./",
    )
    config_test = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/amazons/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="../api_config",
    )

    try:
        env = botzone.make(envs[game])
        bots = [
            Bot(BotConfig.fromID(samples[game])),  # 官方样例 Bot
            #Bot(config_sample),  # 本地随机 Bot
            Bot(config_test, log_path="./amazons.log"),  # 本地随机 Bot
        ]
        runMatch(env, bots)
    finally:
        env.close()
        for bot in bots:
            bot.close()

if __name__ == "__main__":
    testLocalAmazonsWithLLM()