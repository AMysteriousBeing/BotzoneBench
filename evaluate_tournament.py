import os
import json
import botzone
from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig
from multiprocessing import Pool
import time
from pathlib import Path
from bot_info import LLM_CONFIG_LIST, LLM_CONFIG_LIST2
from collections import defaultdict


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
    # "Qwen3_235_Thinking": "qwen3-235b-a22b-thinking-2507",
    "Qwen3_235_Instruct": "qwen3-235b-a22b-instruct-2507",
    "DeepSeek3.2": "deepseek-v3.2",
    "Gemini3Pro_Preview": "gemini-3-pro-preview",
    "ClaudeSonnet4.5": "claude-sonnet-4-5-20250929",
    # "GPT5.2": "gpt-5.2-2025-12-11",
    # "GLM4.6": "glm-4.6",
    # "KimiK2": "kimi-k2",
}

llm2config = {
    # "Qwen3_235_Thinking": "lab_openai_chinese",
    "Qwen3_235_Instruct": "lab_openai_chinese",
    "DeepSeek3.2": "lab_openai_chinese",
    # "KimiK2": "lab_openai_chinese",
    # "GLM4.6": "lab_openai_chinese",
    "Gemini3Pro_Preview": "lab_openai_foreign",
    "ClaudeSonnet4.5": "lab_openai_chinese",
    "GPT5.2": "lab_openai_foreign",
}

GAME_LOG_ROOT = "./log_game_tournament_records"
LLM_LOG_ROOT = "./log_llm_tournament_records"


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
    llm1,
    llm2,
    game_id,
    is_rematch=False,
):
    """
    Docstring for eval_single_game

    :param game: name of the game
    :param baseline_lvl: botzone baseline level
    :param llm: name of the llm
    :param reverse_order: True: baseline bot goes first, False: llm-based bot goes first
    :param game_id: game log identifier
    return: 1 if llm1 wins, 0 if draw, -1 if llm2 wins
    """
    appendix_marker = ""
    if is_rematch:
        appendix_marker = "-re4"

    bots = []
    # construct path for game log output
    path_to_game_log = os.path.join(GAME_LOG_ROOT, game)
    # construct path for llm interaction log output
    path_to_llm_interaction = os.path.join(LLM_LOG_ROOT, game)

    # update config for llms and construct llm-based bots
    llm_name1 = online_llms[llm1]
    llm_name2 = online_llms[llm2]
    match_marker = f"{llm1}_{llm2}_{game_id}"
    game_identifier = f"{match_marker}{appendix_marker}"
    # Construct llm_bot from llm name
    llm_bot1 = LLM_CONFIG_LIST[game]
    llm_bot2 = LLM_CONFIG_LIST2[game]
    # access_mode: lab_openai_chinese, lab_openai_foreign, silicon_flow, local_vllm
    api_access_mode1 = llm2config[llm1]
    with open("api_config/llm_config.json", "w") as f:
        json.dump({"llm_name": llm_name1, "api_access": api_access_mode1}, f)
    api_access_mode2 = llm2config[llm2]
    with open("api_config2/llm_config.json", "w") as f:
        json.dump({"llm_name": llm_name2, "api_access": api_access_mode2}, f)
    # populate bots list
    if game == "ChineseStandardMahjong":
        # 4-player game
        bots.append(
            Bot(
                llm_bot1,
                log_path=os.path.join(
                    path_to_llm_interaction,
                    f"{game_identifier}-{0}.log",
                ),
            )
        )
        bots.append(
            Bot(
                llm_bot2,
                log_path=os.path.join(
                    path_to_llm_interaction,
                    f"{game_identifier}-{1}.log",
                ),
            )
        )
        bots.append(
            Bot(
                llm_bot1,
                log_path=os.path.join(
                    path_to_llm_interaction,
                    f"{game_identifier}-{2}.log",
                ),
            )
        )
        bots.append(
            Bot(
                llm_bot2,
                log_path=os.path.join(
                    path_to_llm_interaction,
                    f"{game_identifier}-{3}.log",
                ),
            )
        )
    elif game == "FightTheLandlord":
        # 3-player game
        bots.append(
            Bot(
                llm_bot1,
                log_path=os.path.join(
                    path_to_llm_interaction,
                    f"{game_identifier}-{0}.log",
                ),
            )
        )
        bots.append(
            Bot(
                llm_bot2,
                log_path=os.path.join(
                    path_to_llm_interaction,
                    f"{game_identifier}-{1}.log",
                ),
            )
        )
        bots.append(
            Bot(
                llm_bot2,
                log_path=os.path.join(
                    path_to_llm_interaction,
                    f"{game_identifier}-{2}.log",
                ),
            )
        )
    else:
        # 2-player game
        bots.append(
            Bot(
                llm_bot1,
                log_path=os.path.join(
                    path_to_llm_interaction,
                    f"{game_identifier}-{0}.log",
                ),
            )
        )
        bots.append(
            Bot(
                llm_bot2,
                log_path=os.path.join(
                    path_to_llm_interaction,
                    f"{game_identifier}-{1}.log",
                ),
            )
        )

    try:
        env = botzone.make(envs[game])
        rand_seed = game_id
        if game == "ChineseStandardMahjong":
            result = runMatch(
                env,
                bots,
                {"srand": rand_seed},
                game_log_output_dir=path_to_game_log,
                desc=game_identifier,
            )
        elif game == "FightTheLandlord":
            result = runMatch(
                env,
                bots,
                {"seed": rand_seed},
                game_log_output_dir=path_to_game_log,
                desc=game_identifier,
            )
        elif game == "TexasHoldem2p":
            result = runMatch(
                env,
                bots,
                {"srand": rand_seed, "max_hand": 20},
                game_log_output_dir=path_to_game_log,
                desc=game_identifier,
            )
        else:
            result = runMatch(
                env, bots, game_log_output_dir=path_to_game_log, desc=game_identifier
            )
    except Exception as e:
        raise e
    finally:
        env.close()
        for bot in bots:
            bot.close()

    # interpret results
    if game == "ChineseStandardMahjong":
        # 4-player game
        if result[0] > 0 or result[2] > 0:
            return 1, match_marker, llm1, llm2
        elif result[0] == 0:
            return 0, match_marker, llm1, llm2
        else:
            return -1, match_marker, llm1, llm2
    elif game == "FightTheLandlord":
        if result[0] > result[1] and result[0] > result[2]:
            return 1, match_marker, llm1, llm2
        else:
            return -1, match_marker, llm1, llm2
    else:
        if result[0] > result[1]:
            return 1, match_marker, llm1, llm2
        elif result[0] == result[1]:
            return 0, match_marker, llm1, llm2
        else:
            return -1, match_marker, llm1, llm2


def tournament_evaluation(
    game, eval_multiplier, success_list=None, parallel_ct=32, id_offset=0
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
    # i dictates seed for imperfect information games
    for i in range(id_offset, eval_multiplier):
        for llm1 in online_llms.keys():
            for llm2 in online_llms.keys():
                if llm1 != llm2:
                    match_marker = f"{llm1}_{llm2}_{i}"
                    if (
                        success_list and match_marker not in success_list
                    ) or not success_list:
                        print("Init:", match_marker)
                        ret = pool.apply_async(
                            evaluation,
                            args=(
                                game,
                                llm1,
                                llm2,
                                i,
                                success_list != None,
                            ),
                        )
                        result_list.append(ret)
                        time.sleep(5)
    pool.close()
    pool.join()
    round_robin_mat = defaultdict(lambda: defaultdict(int))
    success_list = []
    for ret in result_list:
        try:
            ret, ret_id, tested_llm1, tested_llm2 = ret.get()
            success_list.append(ret_id)
            if ret > 0:
                round_robin_mat[tested_llm1][tested_llm2] += 1
            elif ret == 0:
                pass
            elif ret < 0:
                round_robin_mat[tested_llm2][tested_llm1] += 1
        except Exception as e:
            pass

    return round_robin_mat, success_list


if __name__ == "__main__":
    game = "Reversi"
    # launch more tournaments for higher accuracy results
    multiplier = 2
    offset_id = 0
    parallel_ct = 24
    success_list = [
        "Qwen3_235_Instruct_DeepSeek3.2_0",
        "Qwen3_235_Instruct_Gemini3Pro_Preview_0",
        "Qwen3_235_Instruct_ClaudeSonnet4.5_0",
        "Qwen3_235_Instruct_ClaudeSonnet4.5_1",
        "DeepSeek3.2_Qwen3_235_Instruct_0",
        "DeepSeek3.2_Gemini3Pro_Preview_0",
        "DeepSeek3.2_ClaudeSonnet4.5_0",
        "DeepSeek3.2_ClaudeSonnet4.5_1",
        "Gemini3Pro_Preview_Qwen3_235_Instruct_0",
        "Gemini3Pro_Preview_DeepSeek3.2_0",
        "Qwen3_235_Instruct_DeepSeek3.2_1",
        "DeepSeek3.2_Qwen3_235_Instruct_1",
        "ClaudeSonnet4.5_DeepSeek3.2_0",
        "ClaudeSonnet4.5_DeepSeek3.2_1",
        "ClaudeSonnet4.5_Qwen3_235_Instruct_0",
        "ClaudeSonnet4.5_Qwen3_235_Instruct_1",
        "Qwen3_235_Instruct_Gemini3Pro_Preview_1",
        "DeepSeek3.2_Gemini3Pro_Preview_1",
        "Gemini3Pro_Preview_Qwen3_235_Instruct_1",
        "Gemini3Pro_Preview_DeepSeek3.2_1",
        "Gemini3Pro_Preview_ClaudeSonnet4.5_0",
        "Gemini3Pro_Preview_ClaudeSonnet4.5_1",
    ]

    round_robin_results, success_list = tournament_evaluation(
        game,
        multiplier,
        success_list=success_list,
        parallel_ct=parallel_ct,
        id_offset=offset_id,
    )
    print(
        f"Game {game} tournament results: {round_robin_results}, success list: {success_list}"
    )
    with open("./result.txt", "w") as f:
        f.write(f"Game {game} results:\n {round_robin_results}")
    with open("./result.json", "w") as f:
        json.dump(round_robin_results, f)
