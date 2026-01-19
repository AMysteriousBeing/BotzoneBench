import os
import json
import botzone
from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig
from multiprocessing import Pool
import time
from pathlib import Path
from bot_info import LV0_CONFIG_LIST, LV1_CONFIG_LIST, LLM_CONFIG_LIST, LV2_CONFIG_LIST

baseline_levels = {
    "lv0": LV0_CONFIG_LIST,
    "lv1": LV1_CONFIG_LIST,
    "lv2": LV2_CONFIG_LIST,
}


envs = {
    "Amazons": "Amazons-v8",
    "Ataxx": "Ataxx-v0",
    "ChineseStandardMahjong": "ChineseStandardMahjong-v0-dup",
    "FightTheLandlord": "FightTheLandlord-v0",
    "Go": "Go-v8",  # should not be counted
    "Gomoku": "Gomoku-v15",
    "Reversi": "Reversi-v0",
    "TicTacToe": "TicTacToe-v0",
    "Chess": "Chess-wrap",
    "TexasHoldem2p": "TexasHoldem2p-wrap",
}

online_llms = {
    "Qwen3_235_Thinking": "qwen3-235b-a22b-thinking-2507",
    "Qwen3_235_Instruct": "qwen3-235b-a22b-instruct-2507",
    "DeepSeek3.2": "deepseek-v3.2",
    "Gemini3Pro_Preview": "gemini-3-pro-preview",
    "ClaudeSonnet4.5": "claude-sonnet-4-5-20250929",
    "GPT5.2": "gpt-5.2-2025-12-11",
    "GLM4.6": "glm-4.6",
    "KimiK2": "kimi-k2",
}

llm2config = {
    "Qwen3_235_Thinking": "lab_openai_chinese",
    "Qwen3_235_Instruct": "lab_openai_chinese",
    "DeepSeek3.2": "lab_openai_chinese",
    "KimiK2": "lab_openai_chinese",
    "GLM4.6": "lab_openai_chinese",
    "Gemini3Pro_Preview": "lab_openai_foreign",
    "ClaudeSonnet4.5": "lab_openai_foreign",
    "GPT5.2": "lab_openai_foreign",
}


def runMatch(env, bots, init_data=None, game_log_output_dir=None, desc=None):
    env.init(bots)
    # specify random seed with: initdata={"srand": 1}
    if init_data != None:

        score = env.reset(init_data)
    else:
        score = env.reset()
    # disable render
    # env.render()
    while score is None:
        score = env.step()
        # disable render
        # env.render()
    else:
        if game_log_output_dir:
            path = Path(game_log_output_dir)
            path.mkdir(parents=True, exist_ok=True)
            with open(os.path.join(game_log_output_dir, f"{desc}.log"), "w") as f:
                f.writelines(json.dumps(env.display))
        return score


def evaluation(
    game,
    baseline_lvl,
    eval_lvl,
    eval_id,
    reverse_order,
    game_id,
    total_game,
    is_rematch=False,
):
    """
    Docstring for eval_single_game

    :param game: name of the game
    :param baseline_lvl: botzone baseline level
    :param llm: name of the llm
    :param reverse_order: True: baseline bot goes first, False: llm-based bot goes first
    :param game_id: game log identifier
    return: 1 if llm wins, 0 if draw, -1 if llm loses
    """
    appendix_marker = ""
    if is_rematch:
        appendix_marker = "-re"
    baseline_dict = baseline_levels[baseline_lvl]
    baseline_bots = baseline_dict[game]
    if isinstance(baseline_bots, BotConfig):
        baseline_bot = baseline_bots
    elif isinstance(baseline_bots, list):
        baseline_bot_ct = len(baseline_bots)
        assert total_game % baseline_bot_ct == 0
        single_bot_eval_ct = total_game // baseline_bot_ct
        eval_bot_list = [
            bot for bot in baseline_bots for _ in range(single_bot_eval_ct)
        ]
        baseline_bot = eval_bot_list[game_id]
    else:
        raise Exception("Double Check Baseline_lvl Param!")

    bots = []
    # Construct llm_bot from llm name
    if isinstance(baseline_levels[eval_lvl][game], list):
        eval_bot = baseline_levels[eval_lvl][game][eval_id]
    else:
        eval_bot = baseline_levels[eval_lvl][game]
    # populate bots list
    if game == "ChineseStandardMahjong":
        # 4-player game
        if reverse_order:
            bots.append(Bot(baseline_bot))
            bots.append(Bot(eval_bot))
            bots.append(Bot(baseline_bot))
            bots.append(Bot(eval_bot))
        else:
            bots.append(Bot(eval_bot))
            bots.append(Bot(baseline_bot))
            bots.append(Bot(eval_bot))
            bots.append(Bot(baseline_bot))
    elif game == "FightTheLandlord":
        # 3-player game
        if reverse_order:
            bots.append(Bot(baseline_bot))
            bots.append(Bot(eval_bot))
            bots.append(Bot(eval_bot))
        else:
            bots.append(Bot(eval_bot))
            bots.append(Bot(baseline_bot))
            bots.append(Bot(baseline_bot))
    else:
        # 2-player game
        if reverse_order:
            bots.append(Bot(baseline_bot))
            bots.append(Bot(eval_bot))
        else:
            bots.append(Bot(eval_bot))
            bots.append(Bot(baseline_bot))
    try:
        env = botzone.make(envs[game])
        rand_seed = game_id // 2
        if game == "ChineseStandardMahjong":
            result = runMatch(
                env,
                bots,
                {"srand": rand_seed},
            )
        elif game == "FightTheLandlord":
            result = runMatch(
                env,
                bots,
                {"seed": rand_seed},
            )
        elif game == "TexasHoldem2p":
            result = runMatch(
                env,
                bots,
                {"srand": rand_seed, "max_hand": 20},
            )
        else:
            result = runMatch(env, bots)
    except Exception as e:
        raise e
    finally:
        env.close()
        for bot in bots:
            bot.close()
    # interpret results
    if game == "ChineseStandardMahjong":
        # 4-player game
        if reverse_order:
            if result[1] > 0 or result[3] > 0:
                return 1, game_id
            elif result[1] == 0:
                return 0, game_id
            else:
                return -1, game_id
        else:
            if result[0] > 0 or result[2] > 0:
                return 1, game_id
            elif result[0] == 0:
                return 0, game_id
            else:
                return -1, game_id
    elif game == "FightTheLandlord":
        if reverse_order:
            if result[1] > result[0] or result[2] > result[0]:
                return 1, game_id
            else:
                return -1, game_id
        else:
            if result[0] > result[1] and result[0] > result[2]:
                return 1, game_id
            else:
                return -1, game_id
    else:
        if reverse_order:
            if result[1] > result[0]:
                return 1, game_id
            elif result[1] == result[0]:
                return 0, game_id
            else:
                return -1, game_id
        else:
            if result[0] > result[1]:
                return 1, game_id
            elif result[0] == result[1]:
                return 0, game_id
            else:
                return -1, game_id


def batched_evaluation(
    game, baseline_lvl, eval_lvl, next_lvl_id, rounds, success_list=None, parallel_ct=32
):
    """
    Docstring for batched_evaluation

    :param game: name of the game
    :param baseline_lvl: level name
    :param llm: llm name
    :param rounds: # of games
    :param success_list: None: first match, !=None: rematch for failed cases
    """
    pool = Pool(parallel_ct)
    result_list = []
    for i in range(rounds):
        if (success_list and i not in success_list) or not success_list:
            ret = pool.apply_async(
                evaluation,
                args=(
                    game,
                    baseline_lvl,
                    eval_lvl,
                    next_lvl_id,
                    i % 2,
                    i,
                    rounds,
                    success_list != None,
                ),
            )
            result_list.append(ret)
            time.sleep(0.5)
    pool.close()
    pool.join()
    positive_count = 0
    negative_count = 0
    draw_count = 0
    success_list = []
    for ret in result_list:
        try:
            ret, ret_id = ret.get()
            success_list.append(ret_id)
            if ret > 0:
                positive_count += 1
            elif ret == 0:
                draw_count += 1
            elif ret < 0:
                negative_count += 1
        except Exception as e:
            pass

    return (positive_count, draw_count, negative_count), rounds, success_list


if __name__ == "__main__":
    game = "Reversi"
    bot_lvl = "lv0"
    eval_lvl = "lv1"
    eval_num = 32
    parallel_ct = 16
    eval_id = 3
    (pos, draw, neg), total, success_list = batched_evaluation(
        game, bot_lvl, eval_lvl, eval_id, eval_num, parallel_ct=parallel_ct
    )
    print(f"Game {game} {bot_lvl} results for {eval_id}: {pos}-{draw}-{neg}/{total}")
    # ret = evaluation(game, bot_lvl, eval_lvl, eval_id, False, 0, 32)
    # print(ret)
