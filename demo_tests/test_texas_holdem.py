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
    samples = {
        "TexasHoldem2p": "63fc5cbe6ce79f4b2dcce80f",
    }
    envs = {
        "TexasHoldem2p": "TexasHoldem2p-wrap",
    }

    config_test = BotConfig(
        game=GameConfig.fromName("TexasHoldem2p"),
        path="../local_bots/texasholdem/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="../api_config",
    )
    game = "TexasHoldem2p"
    print("Trying game", game)
    initdata = {"srand": 1, "max_hand": 20}
    try:
        env = botzone.make(envs[game])
        bots = []
        bots.append(Bot(LV3_CONFIG_LIST["TexasHoldem2p"][0]))
        # bots.append(Bot(BotConfig.fromID(samples[game])))
        bots.append(Bot(LV3_CONFIG_LIST["TexasHoldem2p"][1]))
        runMatch(env, bots, initdata)
    finally:
        env.close()
        for bot in bots:
            bot.close()


if __name__ == "__main__":
    testGame()
