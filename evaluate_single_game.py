import os
import json
import botzone
from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig
from multiprocessing import Pool
import time
from pathlib import Path
from bot_info import (
    LV0_CONFIG_LIST,
    LV1_CONFIG_LIST,
    LLM_CONFIG_LIST,
    LV2_CONFIG_LIST,
    LV3_CONFIG_LIST,
    LV4_CONFIG_LIST,
    LV5_CONFIG_LIST,
)

baseline_levels = {
    "lv0": LV0_CONFIG_LIST,
    "lv1": LV1_CONFIG_LIST,
    "lv2": LV2_CONFIG_LIST,
    "lv3": LV3_CONFIG_LIST,
    "lv4": LV4_CONFIG_LIST,
    "lv5": LV5_CONFIG_LIST,
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
    "Qwen3-8B": "Qwen/Qwen3-8B",
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
    "Qwen3-8B": "silicon_flow",
    "Qwen3-32B": "local_vllm",
    "Qwen3-32B-Instruct": "local_vllm",
}

GAME_LOG_ROOT = "./log_game_records"
LLM_LOG_ROOT = "./log_llm_records"


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
    llm,
    reverse_order,
    game_id,
    total_game,
    is_rematch=False,
    game_id_offset=0,
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
        baseline_bot = eval_bot_list[game_id - game_id_offset]
    else:
        raise Exception("Double Check Baseline_lvl Param!")

    bots = []
    # construct path for game log output
    path_to_game_log = os.path.join(GAME_LOG_ROOT, game, baseline_lvl, llm)
    # construct path for llm interaction log output
    path_to_llm_interaction = os.path.join(LLM_LOG_ROOT, game, baseline_lvl, llm)
    # Construct llm_bot from llm name
    llm_bot = LLM_CONFIG_LIST[game]
    # populate bots list
    if game == "ChineseStandardMahjong":
        # 4-player game
        if reverse_order:
            bots.append(Bot(baseline_bot))
            bots.append(
                Bot(
                    llm_bot,
                    log_path=os.path.join(
                        path_to_llm_interaction, f"{game_id}-{1}{appendix_marker}.log"
                    ),
                )
            )
            bots.append(Bot(baseline_bot))
            bots.append(
                Bot(
                    llm_bot,
                    log_path=os.path.join(
                        path_to_llm_interaction, f"{game_id}-{3}{appendix_marker}.log"
                    ),
                )
            )
        else:
            bots.append(
                Bot(
                    llm_bot,
                    log_path=os.path.join(
                        path_to_llm_interaction, f"{game_id}-{0}{appendix_marker}.log"
                    ),
                )
            )
            bots.append(Bot(baseline_bot))
            bots.append(
                Bot(
                    llm_bot,
                    log_path=os.path.join(
                        path_to_llm_interaction, f"{game_id}-{2}{appendix_marker}.log"
                    ),
                )
            )
            bots.append(Bot(baseline_bot))
    elif game == "FightTheLandlord":
        # 3-player game
        if reverse_order:
            bots.append(Bot(baseline_bot))
            bots.append(
                Bot(
                    llm_bot,
                    log_path=os.path.join(
                        path_to_llm_interaction, f"{game_id}-{1}{appendix_marker}.log"
                    ),
                )
            )
            bots.append(
                Bot(
                    llm_bot,
                    log_path=os.path.join(
                        path_to_llm_interaction, f"{game_id}-{2}{appendix_marker}.log"
                    ),
                )
            )
        else:
            bots.append(
                Bot(
                    llm_bot,
                    log_path=os.path.join(
                        path_to_llm_interaction, f"{game_id}-{0}{appendix_marker}.log"
                    ),
                )
            )
            bots.append(Bot(baseline_bot))
            bots.append(Bot(baseline_bot))
    else:
        # 2-player game
        if reverse_order:
            bots.append(Bot(baseline_bot))
            bots.append(
                Bot(
                    llm_bot,
                    log_path=os.path.join(
                        path_to_llm_interaction, f"{game_id}-{1}{appendix_marker}.log"
                    ),
                )
            )
        else:
            bots.append(
                Bot(
                    llm_bot,
                    log_path=os.path.join(
                        path_to_llm_interaction, f"{game_id}-{0}{appendix_marker}.log"
                    ),
                )
            )
            bots.append(Bot(baseline_bot))
    game_identifier = (
        f"{game_id}-bl{appendix_marker}"
        if reverse_order
        else f"{game_id}-llm{appendix_marker}"
    )
    try:
        env = botzone.make(envs[game])
        rand_seed = game_id // 2
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
    game, baseline_lvl, llm, rounds, success_list=None, parallel_ct=32, game_id_offset=0
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
        if (
            success_list and (i + game_id_offset) not in success_list
        ) or not success_list:
            ret = pool.apply_async(
                evaluation,
                args=(
                    game,
                    baseline_lvl,
                    llm,
                    i % 2,
                    i + game_id_offset,
                    rounds,
                    success_list != None,
                    game_id_offset,
                ),
            )
            result_list.append(ret)
            time.sleep(2)
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
    game = "Ataxx"
    bot_lvl = "lv3"
    eval_num = 32
    # this parameter is used to append additional testing to existing evals
    optional_eval_offset = 0
    parallel_ct = 16
    # llm list: ["Qwen3_235_Thinking", "Qwen3_235_Instruct", "DeepSeek3.2", "Gemini3Pro_Preview","ClaudeSonnet4.5", "GPT5.2" ]
    llm = "Qwen3-32B-Instruct"
    # access_mode: lab_openai_chinese, lab_openai_foreign, silicon_flow, local_vllm
    api_access_mode = llm2config[llm]
    llm_name = online_llms[llm]
    with open("api_config/llm_config.json", "w") as f:
        json.dump(
            {"llm_name": llm_name, "api_access": api_access_mode}, f
        )  # lab_openai
    (pos, draw, neg), total, success_list = batched_evaluation(
        game,
        bot_lvl,
        llm,
        eval_num,
        parallel_ct=parallel_ct,
        game_id_offset=optional_eval_offset,
    )
    print(f"Round 1 results: {pos, draw, neg}, {total}, {success_list}")
    # (pos2, draw2, neg2), total2, success_list2 = batched_evaluation(
    #     game,
    #     bot_lvl,
    #     llm,
    #     eval_num,
    #     success_list,
    #     parallel_ct=parallel_ct,
    #     game_id_offset=optional_eval_offset,
    # )
    # print(f"Rematch results: {pos2, draw2, neg2}, {total2}, {success_list2}")
    # ret = evaluation(game, bot_lvl, llm, False, 0, 32)
    print(f"Game {game} {bot_lvl} results for {llm}: {pos}-{draw}-{neg}/{total}")
    with open("./result.txt", "w") as f:
        f.write(f"Game {game} {bot_lvl} results for {llm}: {pos}-{draw}-{neg}/{total}")
