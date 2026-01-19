import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import botzone
from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig
from bot_info import LV2_CONFIG_LIST, LV3_CONFIG_LIST


def runMatch(env, bots, init_data=None):
    env.init(bots)
    # specify random seed with: initdata={"srand": 1}
    if init_data != None:

        score = env.reset(init_data)
    else:
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
        "Chess": "Chess-wrap",
    }

    config_demo = BotConfig(
        game=GameConfig.fromName("Chess"),
        path="../local_bots/chess/sample.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./",
    )
    config_demo_py = BotConfig(
        game=GameConfig.fromName("Chess"),
        path="../local_bots/chess/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="../api_config",
    )
    game = "Chess"
    print("Trying game", game)
    try:
        env = botzone.make(envs[game])
        bots = []
        # bots.append(Bot(BotConfig.fromID(samples[game])))

        # bots.append(Bot(config_demo_py, log_path="./chess.log"))
        # bots.append(Bot(config_demo_py, log_path="./chess.log"))
        bots.append(Bot(LV3_CONFIG_LIST["Chess"]))
        bots.append(Bot(BotConfig.fromID("61e9683f3e8ab26550c84f7e", userfile=True)))
        runMatch(env, bots)
    finally:
        env.close()
        for bot in bots:
            bot.close()


if __name__ == "__main__":
    testGame()
