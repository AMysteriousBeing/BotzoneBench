import json
import re
import requests

from data.conf import (
    access_mode_and_llm,
    openai_foreign_info,
    openai_chinese_info,
    silicon_flow_info,
    local_vllm_info,
)

N_PLAYERS = 2
SMALL_BLIND = 50
BIG_BLIND = 100


def card_suit(card):
    return card % 4


def card_number(card):
    return card // 4 + 2


def next_player(player, offset):
    return (player + offset) % N_PLAYERS


def get_valid_action(input_data):
    N_PLAYERS = input_data["num_players"]  # 比赛中一共有多少玩家, 固定为2
    my_id = input_data["my_id"]  # 我的玩家ID, 0或1

    # ==============================================================================
    # 恢复当前牌面信息
    round = 0  # 当前轮次 0: preflop, 1: flop, 2: turn, 3: river
    round_bet = BIG_BLIND  # 当前轮次的最大下注
    round_raise = 2 * round_bet  # 当前轮次最小加注到的筹码数
    round_action_count = 0  # 当前轮次已经叫注的玩家数
    player_bets = [0] * N_PLAYERS  # 当前轮次每个玩家已经下注的筹码数
    player_bets[next_player(input_data["dealer_id"], 1)] = SMALL_BLIND
    player_bets[next_player(input_data["dealer_id"], 2)] = BIG_BLIND

    for h in input_data["history"]:
        id, action, type = h["player_id"], h["action"], h["action_type"]
        if type == "fold":
            player_bets[id] = -1  # 标记已弃牌
        elif type == "allin":
            round_bet = -2  # 标记本轮只能全押或弃牌
            player_bets[id] = -2  # 标记已全押
        elif type == "call" or type == "check":
            player_bets[id] = round_bet  # 跟注
            round_action_count += 1
            round_bet_left = [bet for bet in player_bets if bet >= 0]
            # 在场玩家均等注时进入下一轮
            if round_action_count >= len(round_bet_left) and round_bet_left.count(
                round_bet
            ) == len(round_bet_left):
                round += 1  # 轮次+1，进入下一轮
                round_bet = 0  # 重置当前轮次的最大下注
                round_raise = BIG_BLIND  # 每轮开始最小加注的筹码数均为大盲注
                round_action_count = 0  # 重置当前轮次已经叫注的玩家数
                player_bets = [0 if bet >= 0 else bet for bet in player_bets]
        elif type == "raise":
            player_bets[id] += action  # 加注
            round_bet = max(round_bet, player_bets[id])  # 更新当前轮次的最大下注
            round_raise = max(round_raise, 2 * action)  # 下次加注至少为当前加注的2倍
            round_action_count += 1

    # ==============================================================================
    # 生成可能的动作: (动作, 概率)
    # 动作包括 -1: 弃牌, -2: 全押, 0: 过牌或跟注, >0: 加注的数量
    possible_actions = []
    possible_actions.append(-1)  # 弃牌, 概率0.15
    possible_actions.append(-2)  # 全押, 概率0.05

    if round_bet >= 0:
        if round_bet - player_bets[my_id] < input_data["my_chips"]:  # 剩余筹码可跟注
            possible_actions.append(0)  # 过牌或跟注, 概率0.6
        if round_raise < input_data["my_chips"]:  # 剩余筹码足够加注
            possible_actions.append(round_raise)  # 加注, 概率0.2
    else:  # 有人全押, 本轮只能全押或弃牌
        # 如果对面最后一手牌翻牌前allin，且我目前丢掉盲注不能稳赢，就直接全押
        if (
            round == 0
            and input_data["hand"] == input_data["max_hand"] - 1
            and input_data["total_win_chips"][my_id] - player_bets[my_id] < 0
        ):
            possible_actions.append(-2)  # 直接全押, 概率0.8
        else:
            possible_actions.append(-1)  # 弃牌, 概率0.8
    return possible_actions


def convert_num_to_card(card_num):
    """
    将0-51的数字转换为扑克牌英文名称
    格式示例: "Ace of Spades", "3 of Clubs"
    """
    # 参数验证
    if not isinstance(card_num, int) or card_num < 0 or card_num > 51:
        return "Invalid card number"

    # 花色映射 (按您的顺序: 红桃, 方块, 黑桃, 草花)
    suits = ["Hearts", "Diamonds", "Spades", "Clubs"]

    # 点数映射
    ranks = [
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "Jack",
        "Queen",
        "King",
        "Ace",
    ]

    # 计算花式和点数
    suit_index = card_num % 4  # 取模得花色索引
    rank_index = card_num // 4  # 整除得点数索引

    suit = suits[suit_index]
    rank = ranks[rank_index]

    return f"{rank} of {suit}"


def interpret_availble_actions_for_llm(valid_actions):
    min_bet = -1
    can_check = False
    for action in valid_actions:
        if action > 0:
            min_bet = action
        if action == 0:
            can_check = True
    valid_action_prompt = "Your valid actions are: [-2 (All-in), -1 (Fold)"
    if can_check:
        valid_action_prompt += ", 0 (Check)"
    if min_bet > 0:
        valid_action_prompt += f", {min_bet} (raise the bet), or any value above {min_bet} but lower than your current chips."
    valid_action_prompt += "].\n"
    return valid_action_prompt


def interpret_request_for_llm(input_data):
    N_PLAYERS = input_data["num_players"]  # 比赛中一共有多少玩家, 固定为2
    my_id = input_data["my_id"]  # 我的玩家ID, 0或1
    cur_hand = input_data["hand"]
    max_hand = input_data["max_hand"]
    current_win_or_loss = input_data["total_win_chips"][my_id]
    available_chips = input_data["my_chips"]
    if current_win_or_loss > 0:
        situation_prompt = "You are currently in the lead.\n"
    else:
        situation_prompt = "You are currently losing to your opponent.\n"
    meta_prompt = (
        f"This is the {cur_hand+1} hand out of {max_hand} hands. Everyone starts with 20,000 chips each hand, and you have {available_chips}. Your cumulative win/loss on chips until last hand are {current_win_or_loss}, but the cumulative win/loss chips are inaccessible and independent from your current chips (consider them as deposits/debts to a bank)."
        + situation_prompt
    )

    # ==============================================================================
    # 恢复当前牌面信息
    round = 0  # 当前轮次 0: preflop, 1: flop, 2: turn, 3: river
    round_bet = BIG_BLIND  # 当前轮次的最大下注
    round_raise = 2 * round_bet  # 当前轮次最小加注到的筹码数
    round_action_count = 0  # 当前轮次已经叫注的玩家数
    player_bets = [0] * N_PLAYERS  # 当前轮次每个玩家已经下注的筹码数
    player_bets[next_player(input_data["dealer_id"], 1)] = SMALL_BLIND
    player_bets[next_player(input_data["dealer_id"], 2)] = BIG_BLIND
    my_card_vals = input_data["my_cards"]
    my_card_names = [convert_num_to_card(i) for i in my_card_vals]
    public_card_vals = input_data["public_cards"]
    my_card_prompt = "Your cards are: " + ", ".join(my_card_names) + ".\n"
    public_card_names = [convert_num_to_card(i) for i in public_card_vals]
    if len(public_card_names) == 0:
        public_card_prompt = "Currently there is no public card shown.\n"
    else:
        public_card_prompt = (
            "Current public cards are: " + ", ".join(public_card_names) + ".\n"
        )
    history_prompt = "The Game history is as follows: \n"
    for history_entry in input_data["history"]:
        round_idx, id, action, type = (
            history_entry["round"],
            history_entry["player_id"],
            history_entry["action"],
            history_entry["action_type"],
        )
        if id == my_id:
            role = "you"
        else:
            role = "your opponent"
        if action > 0:
            history_prompt += (
                f"* On Round {round_idx}, {role} raised bet by {action}.\n"
            )
        else:
            history_prompt += (
                f"* On Round {round_idx}, {role} performed action: {action}.\n"
            )
    return meta_prompt + my_card_prompt + public_card_prompt + history_prompt


rule_prompt = """
You are a 2-player Texas Hold'em Player. 
The game's objective is to make the best 5-card poker hand using any combination of your 2 private cards and the 5 community cards.
Rounds in Texas Hold'em: 

1. Pre-flop: Each player gets 2 face-down cards. Betting begins.

2. The Flop: 3 community cards dealt face-up. Another betting round.

3. The Turn: A 4th community card dealt face-up. Betting round.

4. The River: The 5th and final community card dealt face-up. Final betting round.

5. Showdown: Remaining players reveal their hands. The best hand wins the pot.

Hand Rankings (High to Low) are: Royal Flush, Straight Flush, Four of a Kind, Full House, Flush, Straight, Three of a Kind, Two Pair, One Pair, High Card.

The hand will be explained in detail below:
1. Royal Flush: The highest possible hand: A, K, Q, J, 10, all the same suit. Example: Your hand: A of Spades, K of Spades | Board: Q of Spades, J of Spades, 10 of Spades, 5 of Diamonds, 2 of Hearts, then you can form: A, K, Q, J, 10 of Spades.

2. Straight Flush: Five consecutive cards of the same suit. Example: 3, 4, 5, 6, 7 of Diamond.

3. Four of a Kind: Four cards of the same rank. Example: Your hand: J of Clubs, J of Hearts | Board: J of Diamons, J of Spades, 9 of Hearts, 5 of Clubs, 2 of Diamons

4. Full House: Three of a kind + a pair. Example: 10 of clubs, 10 of Spades, 10 of Hearts, 4 of Diamonds, 4 of Spades

5. Flush: Any five cards of the same suit (not in sequence). Example: A, K, 10 7, 3 of Clubs

6. Straight: Five consecutive cards of mixed suits. Example: Q of Spades, J of Hearts, 10 of Clubs, 9 of Diamonds, 8 of Clubs.

7. Three of a kind: Three cards of the same rank. Example:  5 of Spades, 5 of Heats, 5 of Diamonds, K of Clubs, Q of Diamonds

8: Two Pair: Two different pairs. Example: A of Diamonds, A of Clubs, 9 of Clubs, 9 of Hearts, K of Clubs.

9: One Pair: Two cards of the same rank. Example: K of Hearts, K of Spades, Q of Diamonds, 10 of Clubs, 8 of Hearts.

10: High Card: No made hand; highest single card wins. 

Note for Action representation: -1 for Fold, -2 for All-in. 0 for Call/Check. >0 for the amount you raise the bet. 

When placing a raise, the chips bet must be at least twice the current maximum bet of this round. If no player has bet before in this round, the raise must be at least equal to the big blind.

To call or raise, a player must have enough chips to cover the required bet. Otherwise, they can only fold or go all-in. An improper bet is considered an illegal action and will be treated as a fold.

Now is your turn, to your best ability, please select an action from your valid actions that maximize your probability of winning. If you have more chips than your opponent by the last hand of the game, you win the game.
Please briefly evaluate a few proimsing moves, provide reason for your final choice, and output the action with specified format.
    Your response format should be:
    Evaluation: [Your Evaluation]
    Reason: [Your Reason]
    Answer: [Your Answer] (should be a number)
"""


def extract_move(responsed_text, possible_actions):
    # 确保possible_actions是数字列表
    possible_set = set(possible_actions)
    max_val = max(possible_set)

    # 正则表达式模式，匹配各种格式的Answer: 数字
    patterns = [
        # 标准格式：Answer: 数字 (不区分大小写，冒号后可无空格或有多空格)
        r"(?i)answer\s*:\s*(-?\d+(?:\.\d+)?)",
        # 中文格式：答案: 数字
        r"答案\s*:\s*(-?\d+(?:\.\d+)?)",
        # 纯数字行（作为最后的手段）
        r"^\s*(-?\d+(?:\.\d+)?)\s*$",
    ]

    # 先尝试从整个文本中提取
    for pattern in patterns:
        matches = re.findall(pattern, responsed_text, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            try:
                # 尝试转换为整数
                num = int(float(match))
                if num in possible_set:
                    return 1, num
                if max_val > 0 and num >= max_val:
                    return 1, num
            except (ValueError, TypeError):
                pass

    # 如果没找到，尝试搜索响应末尾附近的数字
    # 提取响应最后几行（通常答案在末尾）
    lines = responsed_text.strip().split("\n")
    last_lines = lines[-5:] if len(lines) > 5 else lines  # 检查最后5行

    for line in reversed(last_lines):  # 从最后一行向前检查
        # 尝试提取该行中的数字
        numbers = re.findall(r"-?\d+(?:\.\d+)?", line)
        for num_str in numbers:
            try:
                num = int(float(num_str))
                if num in possible_set:
                    return 1, num
                if max_val > 0 and num >= max_val:
                    return 1, num
            except (ValueError, TypeError):
                continue

    # 如果还是没找到，尝试查找"Answer"关键字附近的文本
    lines_lower = responsed_text.lower()
    if "answer" in lines_lower or "答案" in lines_lower:
        # 找到包含Answer的行
        for line in lines:
            line_lower = line.lower()
            if "answer" in line_lower or "答案" in line_lower:
                # 提取该行中的数字
                numbers = re.findall(r"-?\d+(?:\.\d+)?", line)
                for num_str in numbers:
                    try:
                        num = int(float(num_str))
                        if num in possible_set:
                            return 1, num
                        if max_val > 0 and num >= max_val:
                            return 1, num
                    except (ValueError, TypeError):
                        continue

    return 0, None  # 无法提取有效数字


if __name__ == "__main__":
    access_mode, model_name = access_mode_and_llm()
    if access_mode == "local_vllm":
        api_base, api_key, query_api = local_vllm_info()
    elif access_mode == "silicon_flow":
        api_base, api_key, query_api = silicon_flow_info()
    elif access_mode == "lab_openai_foreign":
        api_base, api_key, query_api = openai_foreign_info()
    elif access_mode == "lab_openai_chinese":
        api_base, api_key, query_api = openai_chinese_info()

    bz_requests = json.loads(input())["requests"]
    # print(requests)
    possible_actions = get_valid_action(bz_requests[-1])
    state_prompt = interpret_request_for_llm(bz_requests[-1])
    valid_action_prompt = interpret_availble_actions_for_llm(possible_actions)

    # Fault Tolerance
    trial_count = 0
    while trial_count < 3:
        trial_count += 1
        user_prompt = state_prompt + valid_action_prompt

        responsed_text, reasoning_text = query_api(
            api_base,
            api_key,
            model_name,
            rule_prompt,
            user_prompt,
        )
        valid_signal, response = extract_move(responsed_text, possible_actions)
        if valid_signal:
            break

    print(
        json.dumps(
            {
                "response": response,
                "debug": {
                    "system_prompt": rule_prompt,
                    "user_prompt": user_prompt,
                    "reasoning": reasoning_text,
                    "output": responsed_text,
                },
            }
        )
    )
