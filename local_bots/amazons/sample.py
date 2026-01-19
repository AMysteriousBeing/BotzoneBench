import sys
import json
import random

GRIDSIZE = 8
OBSTACLE = 2
GRID_BLACK = 1
GRID_WHITE = -1

dx = [-1, -1, -1, 0, 0, 1, 1, 1]
dy = [-1,  0,  1, -1, 1, -1, 0, 1]

gridInfo = [[0] * GRIDSIZE for _ in range(GRIDSIZE)]
currBotColor = None


def in_map(x, y):
    return 0 <= x < GRIDSIZE and 0 <= y < GRIDSIZE


def ProcStep(x0, y0, x1, y1, x2, y2, color, check_only):
    if not (in_map(x0, y0) and in_map(x1, y1) and in_map(x2, y2)):
        return False
    
    if gridInfo[x0][y0] != color or gridInfo[x1][y1] != 0:
        return False
    
    if gridInfo[x2][y2] != 0 and not (x2 == x0 and y2 == y0):
        return False

    if not check_only:
        gridInfo[x0][y0] = 0
        gridInfo[x1][y1] = color
        gridInfo[x2][y2] = OBSTACLE

    return True


#   初始化棋盘
def init_board():
    # 与 C++ 版完全一致
    a = (GRIDSIZE - 1) // 3
    # 黑方四子
    gridInfo[0][a] = GRID_BLACK
    gridInfo[a][0] = GRID_BLACK
    gridInfo[GRIDSIZE - 1 - a][0] = GRID_BLACK
    gridInfo[GRIDSIZE - 1][a] = GRID_BLACK

    # 白方四子
    gridInfo[0][GRIDSIZE - 1 - a] = GRID_WHITE
    gridInfo[a][GRIDSIZE - 1] = GRID_WHITE
    gridInfo[GRIDSIZE - 1 - a][GRIDSIZE - 1] = GRID_WHITE
    gridInfo[GRIDSIZE - 1][GRIDSIZE - 1 - a] = GRID_WHITE

#  找到所有合法动作
def find_all_moves(color):
    beginPos = []
    movePos = []
    arrowPos = []

    for i in range(GRIDSIZE):
        for j in range(GRIDSIZE):
            if gridInfo[i][j] != color:
                continue

            # 八个方向走子
            for k in range(8):
                for d1 in range(1, GRIDSIZE):
                    xx = i + dx[k] * d1
                    yy = j + dy[k] * d1

                    if not in_map(xx, yy) or gridInfo[xx][yy] != 0:
                        break

                    # 从走后的点再射箭
                    for l in range(8):
                        for d2 in range(1, GRIDSIZE):
                            xxx = xx + dx[l] * d2
                            yyy = yy + dy[l] * d2

                            if not in_map(xxx, yyy):
                                break
                            if gridInfo[xxx][yyy] != 0 and not (xxx == i and yyy == j):
                                break

                            if ProcStep(i, j, xx, yy, xxx, yyy, color, True):
                                beginPos.append((i, j))
                                movePos.append((xx, yy))
                                arrowPos.append((xxx, yyy))

    return beginPos, movePos, arrowPos

#  主程序入口
def main():
    init_board()

    raw = sys.stdin.readline().strip()
    data = json.loads(raw)

    reqs = data["requests"]
    res = data["responses"]

    turnID = len(res)

    global currBotColor

    # 第一次 x0 = -1 → 黑方
    currBotColor = GRID_BLACK if reqs[0]["x0"] < 0 else GRID_WHITE

    # 回放历史
    for i in range(turnID):
        # 对手落子
        rq = reqs[i]
        if rq["x0"] >= 0:
            ProcStep(rq["x0"], rq["y0"], rq["x1"], rq["y1"], rq["x2"], rq["y2"], -currBotColor, False)

        # 我方落子
        rsp = res[i]
        if rsp["x0"] >= 0:
            ProcStep(rsp["x0"], rsp["y0"], rsp["x1"], rsp["y1"], rsp["x2"], rsp["y2"], currBotColor, False)

    # 当前回合对手动作
    rq = reqs[turnID]
    if rq["x0"] >= 0:
        ProcStep(rq["x0"], rq["y0"], rq["x1"], rq["y1"], rq["x2"], rq["y2"], -currBotColor, False)

    # 计算所有合法动作
    beginPos, movePos, arrowPos = find_all_moves(currBotColor)
    posCount = len(beginPos)

    #  决策（随机）
    if posCount > 0:
        idx = random.randint(0, posCount - 1)
        x0, y0 = beginPos[idx]
        x1, y1 = movePos[idx]
        x2, y2 = arrowPos[idx]
    else:
        x0 = y0 = x1 = y1 = x2 = y2 = -1

    # 输出 JSON
    out = {
        "response": {
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2
        },
        "debug": {
            "posCount": posCount
        }
    }

    print(json.dumps(out))


if __name__ == "__main__":
    main()
