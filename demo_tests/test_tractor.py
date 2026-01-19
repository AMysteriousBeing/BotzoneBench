import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from botzone.online.game import GameConfig
import botzone
from botzone.online.bot import BotConfig, Bot


def runMatch(env, bots):
    env.init(bots)
    score = env.reset()
    env.render()
    while score is None:
        score = env.step()
        env.render()
    else:
        print("Score:", score)
        print(env.display)


def testGame():
    envs = {
        "Tractor": "Tractor-wrap",
    }

    game = "Tractor"
    config_demo = BotConfig(
        game=GameConfig.fromName("Tractor"),
        path="../local_bots/tractor/sample.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./",
    )
    llm_agent = BotConfig(
        game=GameConfig.fromName("Tractor"),
        path="../local_bots/tractor/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./",
    )
    print("Trying game", game)
    try:
        env = botzone.make(envs[game])
        bots = []
        bots.append(Bot(llm_agent, "log"))
        bots.append(Bot(llm_agent, "log2"))
        bots.append(Bot(config_demo))
        bots.append(Bot(config_demo))
        runMatch(env, bots)
    finally:
        env.close()
        for bot in bots:
            bot.close()


if __name__ == "__main__":
    testGame()
