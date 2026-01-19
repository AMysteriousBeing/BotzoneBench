import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import botzone
from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig
from bot_info import LV1_CONFIG_LIST, LV2_CONFIG_LIST, LV3_CONFIG_LIST

# from openai import OpenAI


def runMatch(env, bots):
    env.init(bots)
    score = env.reset()
    env.render()
    while score is None:
        score = env.step()
        env.render()
    else:
        print("Score:", score)


def testGame():
    samples = {
        "ChineseStandardMahjong": "5e918db24a3d0c0568f34083",
    }
    envs = {
        "ChineseStandardMahjong": "ChineseStandardMahjong-v0-dup",
    }

    game = "ChineseStandardMahjong"
    print("Trying game", game)
    local_config = BotConfig(
        game=GameConfig.fromName("ChineseStandardMahjong"),
        path="../local_bots/mahjong/llm_bot.py",
        extension="py39",
        simpleio=True,  # bot是否使用简单输入
        keep_running=True,  # bot是否长时运行
        userfile_path="./",
    )
    try:
        env = botzone.make(envs[game])
        bots = []
        # bots.append(Bot(local_config, log_path="./mahjong_online.log"))
        # bots.append(Bot(BotConfig.fromID(samples[game])))
        bots.append(Bot(LV3_CONFIG_LIST["ChineseStandardMahjong"][0]))
        bots.append(Bot(LV3_CONFIG_LIST["ChineseStandardMahjong"][1]))
        bots.append(Bot(LV3_CONFIG_LIST["ChineseStandardMahjong"][2]))
        bots.append(Bot(LV3_CONFIG_LIST["ChineseStandardMahjong"][3]))

        runMatch(env, bots)
    finally:
        env.close()
        for bot in bots:
            bot.close()


if __name__ == "__main__":
    testGame()
