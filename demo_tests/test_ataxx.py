import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import botzone
from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig
from bot_info import LV6_CONFIG_LIST, LV3_CONFIG_LIST


def runMatch(env, bots):
    env.init(bots)
    score = env.reset()
    env.render()
    while score is None:
        score = env.step()
        env.render()
    else:
        print("Score:", score)


def testLocalAtaxxWithLLM():
    samples = {
        "Ataxx": "58d8c01327d1065e145ee3f7",
    }

    # Env名称
    envs = {
        "Ataxx": "Ataxx-v0",
    }

    game = "Ataxx"
    print("Trying game", game)

    # 本地 LLM Bot 配置
    config_sample = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/ataxx/sample.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./",
    )
    config_test = BotConfig(
        game=GameConfig.fromName(game),
        path="../local_bots/ataxx/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="../api_config",
    )

    try:
        env = botzone.make(envs[game])
        bots = [
            Bot(LV6_CONFIG_LIST["Ataxx"][0]),  # 官方样例Bot
            Bot(LV6_CONFIG_LIST["Ataxx"][1]),  # 本地LLM Bot
            # Bot(config_sample),                       # 本地随机 Bot
        ]
        runMatch(env, bots)
    finally:
        env.close()
        for bot in bots:
            bot.close()


if __name__ == "__main__":
    testLocalAtaxxWithLLM()
