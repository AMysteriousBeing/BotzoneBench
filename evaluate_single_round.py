import os
import json
import botzone
from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig
import random
from pathlib import Path
from bot_info import (
    LV0_CONFIG_LIST,
    LV1_CONFIG_LIST,
    LLM_CONFIG_LIST,
    LV2_CONFIG_LIST,
    LV3_CONFIG_LIST,
    LV4_CONFIG_LIST,
)

baseline_levels = {
    "lv0": LV0_CONFIG_LIST,
    "lv1": LV1_CONFIG_LIST,
    "lv2": LV2_CONFIG_LIST,
    "lv3": LV3_CONFIG_LIST,
    "lv4": LV4_CONFIG_LIST,
}


envs = {
    "Reversi": "Reversi-v0",
    "ChineseStandardMahjong": "ChineseStandardMahjong-v0-dup",
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
    "Qwen3_235_Thinking": "silicon_flow",
    "Qwen3_235_Instruct": "silicon_flow",
    "DeepSeek3.2": "silicon_flow",
    "KimiK2": "silicon_flow",
    "GLM4.6": "silicon_flow",
    "Gemini3Pro_Preview": "silicon_flow",
    "ClaudeSonnet4.5": "silicon_flow",
    "GPT5.2": "silicon_flow",
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
    # disable or enable render
    env.render()
    while score is None:
        score = env.step()
        # disable or enable render
        env.render()
    else:
        if game_log_output_dir:
            path = Path(game_log_output_dir)
            path.mkdir(parents=True, exist_ok=True)
            with open(os.path.join(game_log_output_dir, f"{desc}.log"), "w") as f:
                f.writelines(json.dumps(env.display))
        return score


if __name__ == "__main__":
    game = "ChineseStandardMahjong"
    bot_lvl = "lv0"
    llm = "Qwen3-8B"
    # access_mode: silicon_flow, local_vllm
    api_access_mode = llm2config[llm]
    llm_name = online_llms[llm]
    with open("api_config/llm_config.json", "w") as f:
        json.dump({"llm_name": llm_name, "api_access": api_access_mode}, f)
    baseline_dict = baseline_levels[bot_lvl]
    baseline_bots = baseline_dict[game]
    if isinstance(baseline_bots, BotConfig):
        baseline_bot = baseline_bots
    elif isinstance(baseline_bots, list):
        baseline_bot_ct = len(baseline_bots)
        baseline_bot = random.choice(baseline_bots)
    llm_bot = LLM_CONFIG_LIST[game]
    bots = []
    bots.append(
        Bot(baseline_bot, log_path="./mahjong_agent1.log", show_action=True, color_id=0)
    )
    bots.append(
        Bot(llm_bot, log_path="./mahjong_agent2.log", show_action=True, color_id=1)
    )
    bots.append(
        Bot(baseline_bot, log_path="./mahjong_agent3.log", show_action=True, color_id=2)
    )
    bots.append(
        Bot(llm_bot, log_path="./mahjong_agent4.log", show_action=True, color_id=3)
    )
    env = botzone.make(envs[game])
    result = runMatch(env, bots, game_log_output_dir="logs", desc="mj_test.py")
