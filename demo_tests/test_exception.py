import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import botzone
from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig

import time
from multiprocessing import Pool

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
        extension="py36",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./",
    )
    config_test = BotConfig(
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
        # bots.append(Bot(BotConfig.fromID(samples[game])))
        # bots.append(Bot(BotConfig.fromID(samples[game])))
        bots.append(Bot(config_sample))
        bots.append(Bot(config_sample))
        runMatch(env, bots)
    except Exception as e:
        print(f"Error encountered: {e}")
    finally:
        env.close()
        for bot in bots:
            bot.close()

def evaluation(game, baseline_lvl, llm, reverse_order, game_id, is_rematch=False):
    """
    Docstring for eval_single_game

    :param game: name of the game
    :param baseline_lvl: botzone baseline level
    :param llm: name of the llm
    :param reverse_order: True: baseline bot goes first, False: llm-based bot goes first
    :param game_id: game log identifier
    return: 1 if llm wins, 0 if draw, -1 if llm loses
    """
    if game_id%2==0:
        raise Exception("Abnormal Behavior")
    else:
        return 1, game_id


def batched_evaluation(game, baseline_lvl, llm, rounds, success_list = None):
    """
    Docstring for batched_evaluation
    
    :param game: name of the game
    :param baseline_lvl: level name
    :param llm: llm name
    :param rounds: # of games
    :param success_list: None: first match, !=None: rematch for failed cases
    """
    cpu_count = 32
    pool = Pool(cpu_count)
    result_list = []
    for i in range(rounds):
        if (success_list and i not in success_list) or not success_list:
            ret = pool.apply_async(
                evaluation, args=(game, baseline_lvl, llm, i > rounds // 2, i)
            )
            result_list.append(ret)
            print(f"adding job {i}")
            time.sleep(0.2)
    pool.close()
    pool.join()
    positive_count = 0
    success_list = []
    for ret in result_list:
        try:
            ret, ret_id = ret.get()
            success_list.append(ret_id)
            if ret > 0:
                positive_count += 1
        except Exception as e:
            pass

    return positive_count, rounds, success_list


if __name__ == "__main__":
    positive_count, rounds, success_list = batched_evaluation(None, None, None, 32)
    print(positive_count, rounds, success_list)
