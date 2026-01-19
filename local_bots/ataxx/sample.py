import json
import sys
import random

BOARD_SIZE = 7

# 24个方向（邻居 + 跳跃）
delta = [
    (1,1),(0,1),(-1,1),(-1,0),
    (-1,-1),(0,-1),(1,-1),(1,0),
    (2,0),(2,1),(2,2),(1,2),
    (0,2),(-1,2),(-2,2),(-2,1),
    (-2,0),(-2,-1),(-2,-2),(-1,-2),
    (0,-2),(1,-2),(2,-2),(2,-1)
]

def in_map(x, y):
    return 0 <= x < 7 and 0 <= y < 7

def proc_step(board, step, color):
    x0, y0, x1, y1 = step
    if x1 == -1:
        return True
    if not in_map(x0, y0) or not in_map(x1, y1):
        return False
    if board[x0][y0] != color:
        return False
    if board[x1][y1] != 0:
        return False

    dx, dy = abs(x0 - x1), abs(y0 - y1)
    if (dx == 0 and dy == 0) or dx > 2 or dy > 2:
        return False

    # clone / jump
    if dx == 2 or dy == 2:
        board[x0][y0] = 0
    board[x1][y1] = color

    # flip neighbors
    for i in range(8):
        nx = x1 + delta[i][0]
        ny = y1 + delta[i][1]
        if in_map(nx, ny) and board[nx][ny] == -color:
            board[nx][ny] = color
    return True


def main():
    # 初始化棋盘（完全仿 C++）
    board = [[0]*7 for _ in range(7)]
    board[0][0] = board[6][6] = 1
    board[6][0] = board[0][6] = -1

    # 读取 JSON
    data = json.loads(sys.stdin.readline().strip())
    requests = data["requests"]
    responses = data["responses"]

    turnID = len(responses)

    # C++ 的判断方式：第一回合 x0<0 → 我是黑方(1)，否则白方(-1)
    if requests[0]["x0"] < 0:
        my_color = 1
    else:
        my_color = -1

    # 复盘所有历史
    for i in range(turnID):
        # 对方
        r = requests[i]
        proc_step(board, (r["x0"], r["y0"], r["x1"], r["y1"]), -my_color)

        # 自己
        me = responses[i]
        proc_step(board, (me["x0"], me["y0"], me["x1"], me["y1"]), my_color)

    # 当前回合对手的输入
    cur = requests[turnID]
    proc_step(board, (cur["x0"], cur["y0"], cur["x1"], cur["y1"]), -my_color)

    # 找所有合法走法
    moves = []
    for x0 in range(7):
        for y0 in range(7):
            if board[x0][y0] != my_color:
                continue
            for dx, dy in delta:
                x1 = x0 + dx
                y1 = y0 + dy
                if in_map(x1, y1) and board[x1][y1] == 0:
                    moves.append((x0, y0, x1, y1))

    # 随机选择
    if moves:
        x0, y0, x1, y1 = random.choice(moves)
    else:
        x0 = y0 = x1 = y1 = -1

    # 输出
    print(json.dumps({
        "response": {
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1
        }
    }))

if __name__ == "__main__":
    main()
