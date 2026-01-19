import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import botzone
from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig
from bot_info import (
    LV2_CONFIG_LIST,
    LV3_CONFIG_LIST,
    LV5_CONFIG_LIST,
    LV6_CONFIG_LIST,
    LV0_CONFIG_LIST,
    LV1_CONFIG_LIST,
)
import time

# from openai import OpenAI


def runMatch(env, bots):
    env.init(bots)
    score = env.reset()
    env.render()
    while score is None:
        score = env.step()
        env.render()
        # time.sleep(2)
    else:
        print("Score:", score)


def testGame():
    samples = {
        "Reversi": "5afe9e6f6cc5394385d40062",
        "Snake": "555ef3aa7110330007712994",
        "Tank": "5bc836510681335cc1ef467b",
        "Tank2": "5cb5abf18aa8bb6e75cc9b84",
        "Tank2S": "5cd5818a86d50d05a0095859",
        "Tetris": "58fddf2233b28604c34e2af5",
        "Tetris2": "59f860eb5a11ed72c933561e",
        "TicTacToe": "5ff9514438843939e7476086",
    }
    envs = {
        "Reversi": "Reversi-v0",
        "Snake": "Snake-v0",
        "Tank": "Tank-wrap",
        "Tank2": "Tank2-wrap",
        "Tank2S": "Tank2S-wrap",
        "Tetris": "Tetris-wrap",
        "Tetris2": "Tetris2-wrap",
        "TicTacToe": "TicTacToe-v0",
    }

    game = "Reversi"
    print("Trying game", game)
    config_sample = BotConfig(
        game=GameConfig.fromName("Reversi"),
        path="../local_bots/reversi/sample.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./",
    )
    config_llm = BotConfig(
        game=GameConfig.fromName("Reversi"),
        path="../local_bots/reversi/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="../api_config",
    )
    try:
        env = botzone.make(envs[game])
        # bots = [Bot(BotConfig.fromID(samples[game])) for i in range(env.player_num)]
        bots = []
        # bots.append(Bot(BotConfig.fromID("5677b2bd41c47e1a0f3622ad")))
        # bots.append(Bot(BotConfig.fromID("567ad752e98e37a623ef1d9d")))
        # bots.append(Bot(config_llm, log_path="./log_llm", show_action=True))
        # bots.append(Bot(config_llm, log_path="./log_llm", show_action=True))
        bots.append(Bot(LV1_CONFIG_LIST["Reversi"][0], log_path="./log"))
        bots.append(Bot(LV1_CONFIG_LIST["Reversi"][0], log_path="./log"))
        runMatch(env, bots)
    finally:
        env.close()
        for bot in bots:
            bot.close()


if __name__ == "__main__":
    testGame()
