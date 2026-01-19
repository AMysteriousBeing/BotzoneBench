import json
import time
import random
from enum import Enum
from typing import List, Tuple, Dict, Optional
import copy
import requests
import re

from data.conf import (
    access_mode_and_llm,
    openai_foreign_info,
    openai_chinese_info,
    silicon_flow_info,
    local_vllm_info,
)

BOARDSIZE = 8


class StoneType(Enum):
    NONE = 0
    KING = 1
    QUEEN = 2
    BISHOP = 3
    KNIGHT = 4
    ROOK = 5
    PAWN = 6


class ColorType(Enum):
    BLACK = 0
    WHITE = 1
    EMPTY = 2


stoneSym = "*kqbnrp"
charSym = {
    stoneSym[0]: StoneType.NONE,
    stoneSym[1]: StoneType.KING,
    stoneSym[2]: StoneType.QUEEN,
    stoneSym[3]: StoneType.BISHOP,
    stoneSym[4]: StoneType.KNIGHT,
    stoneSym[5]: StoneType.ROOK,
    stoneSym[6]: StoneType.PAWN,
}

dx = [-1, -1, -1, 0, 0, 1, 1, 1]
dy = [-1, 0, 1, -1, 1, -1, 0, 1]
dx_ob = [-1, 1, -1, 1]
dy_ob = [-1, -1, 1, 1]
dx_strai = [-1, 0, 0, 1]
dy_strai = [0, -1, 1, 0]
dx_lr = [-1, 1]
dx_knight = [-2, -2, -1, -1, 1, 1, 2, 2]
dy_knight = [-1, 1, -2, 2, -2, 2, -1, 1]
proOps = [StoneType.QUEEN, StoneType.KNIGHT, StoneType.BISHOP, StoneType.ROOK]


def pgnchar2int(c: str) -> int:
    return ord(c) - ord("a")


def pgnint2char(i: int) -> str:
    return chr(ord("a") + i)


def char2int(c: str) -> int:
    return ord(c) - ord("1")


def int2char(i: int) -> str:
    return chr(ord("1") + i)


class Move:
    def __init__(
        self,
        source_x: int = -1,
        source_y: int = -1,
        target_x: int = -1,
        target_y: int = -1,
        promoptionType: str = "*",
    ):
        self.source_x = source_x
        self.source_y = source_y
        self.target_x = target_x
        self.target_y = target_y
        self.promoptionType = promoptionType

    @classmethod
    def from_strings(cls, msource: str, mtarget: str, mpromp: str = "*"):
        source_x = pgnchar2int(msource[0])
        source_y = char2int(msource[1])
        target_x = pgnchar2int(mtarget[0])
        target_y = char2int(mtarget[1])
        promoptionType = mpromp[0]
        return cls(source_x, source_y, target_x, target_y, promoptionType)

    def __eq__(self, other):
        if not isinstance(other, Move):
            return False
        return (
            self.source_x == other.source_x
            and self.source_y == other.source_y
            and self.target_x == other.target_x
            and self.target_y == other.target_y
            and self.promoptionType == other.promoptionType
        )


def move_to_string(move: Move):
    """
    将Move对象转换为简洁字符串格式: e2-e4 或 e7-e8-q
    """
    source = f"{pgnint2char(move.source_x)}{int2char(move.source_y)}"
    target = f"{pgnint2char(move.target_x)}{int2char(move.target_y)}"
    internal_representation = {
        "promotion": move.promoptionType,
        "source_x": move.source_x,
        "source_y": move.source_y,
        "target_x": move.target_x,
        "target_y": move.target_y,
    }

    if move.promoptionType != "*":
        return f"{source}-{target}-{move.promoptionType}", internal_representation
    return f"{source}-{target}", internal_representation


class Grid:
    def __init__(
        self,
        mtype: StoneType = StoneType.NONE,
        mcolor: ColorType = ColorType.EMPTY,
        mlastIs2Grid: bool = False,
        mnotMovedYet: bool = True,
    ):
        self.type = mtype
        self.color = mcolor
        self.lastIs2Grid = mlastIs2Grid
        self.notMovedYet = mnotMovedYet

    def to_serializable(self) -> list:
        """
        将Grid转换为可JSON序列化的列表
        """
        stone_type_str = self.type.name if self.type != StoneType.NONE else "NONE"
        color_str = self.color.name
        return [stone_type_str, color_str, self.lastIs2Grid, self.notMovedYet]


def grid_to_list(grid: Grid) -> list:
    """
    将Grid对象转换为可JSON序列化的列表
    格式: [棋子类型字符串, 颜色字符串, lastIs2Grid, notMovedYet]
    """
    # 处理棋子类型
    if grid.type == StoneType.NONE:
        stone_str = ""  # 空格子用空字符串表示
    elif grid.type == StoneType.KING:
        stone_str = "K"  # King
    elif grid.type == StoneType.QUEEN:
        stone_str = "Q"  # Queen
    elif grid.type == StoneType.BISHOP:
        stone_str = "B"  # Bishop
    elif grid.type == StoneType.KNIGHT:
        stone_str = "N"  # kNight (K已经被King使用)
    elif grid.type == StoneType.ROOK:
        stone_str = "R"  # Rook
    elif grid.type == StoneType.PAWN:
        stone_str = "P"  # Pawn
    else:
        stone_str = "?"  # 未知类型

    # 处理颜色
    if grid.color == ColorType.BLACK:
        color_str = "B"  # Black
    elif grid.color == ColorType.WHITE:
        color_str = "W"  # White
    elif grid.color == ColorType.EMPTY:
        color_str = ""  # 空格子用空字符串表示
    else:
        color_str = "?"  # 未知颜色

    # 如果格子是空的，返回简化的表示
    if grid.color == ColorType.EMPTY or grid.type == StoneType.NONE:
        # 对于空位置，可以只返回空字符串或特殊标记
        return ["", "", False, False]  # 或者 return []

    return [stone_str, color_str, grid.lastIs2Grid, grid.notMovedYet]


def print_board(board_info):
    """
    打印棋盘，原点在左下角，黑方在上方，白方在下方
    每个格子用|分割，格子内容格式：类型颜色+两步标记+移动标记
    例如：KWFN 表示白王(未走两步，未移动过)
    """
    str_representation = "\n"
    # 棋子类型到字母的映射
    stone_to_char = {
        StoneType.NONE: " ",
        StoneType.KING: "K",
        StoneType.QUEEN: "Q",
        StoneType.BISHOP: "B",
        StoneType.KNIGHT: "N",
        StoneType.ROOK: "R",
        StoneType.PAWN: "P",
    }

    # 颜色到字母的映射
    color_to_char = {ColorType.EMPTY: " ", ColorType.WHITE: "W", ColorType.BLACK: "B"}

    # 布尔值到字母的映射
    bool_to_char = {True: "T", False: "F"}
    moved_to_char = {True: "0", False: "1"}  # 注意：notMovedYet=True表示未移动

    # 打印列坐标
    str_representation += "  "
    for x in range(BOARDSIZE):
        str_representation += f"   {pgnint2char(x)} "
    str_representation += "\n"

    # 打印分隔线
    str_representation += "  "
    for _ in range(BOARDSIZE):
        str_representation += "+----"
    str_representation += "+\n"

    # 从第8行到第1行（从顶部到底部）
    for y in range(BOARDSIZE - 1, -1, -1):
        # 打印行号
        str_representation += f"{y+1} "

        # 打印棋子和棋盘线
        for x in range(BOARDSIZE):
            grid = board_info[x][y]

            # 构建格子内容
            if grid.type == StoneType.NONE or grid.color == ColorType.EMPTY:
                # 空位置用空格填充到固定宽度
                cell_content = "    "
            else:
                # 有棋子的位置
                stone_char = stone_to_char[grid.type]
                color_char = color_to_char[grid.color]
                last_2grid_char = bool_to_char[grid.lastIs2Grid]
                not_moved_char = moved_to_char[grid.notMovedYet]
                cell_content = (
                    f"{stone_char}{color_char}{last_2grid_char}{not_moved_char}"
                )

            # 打印格子
            str_representation += f"|{cell_content:^4}"

        # 行结束
        str_representation += f"| {y+1}\n"

    # 打印分隔线
    str_representation += "  "
    for _ in range(BOARDSIZE):
        str_representation += "+----"
    str_representation += "+\n"

    # 打印底部列坐标
    str_representation += "  "
    for x in range(BOARDSIZE):
        str_representation += f"   {pgnint2char(x)} "
    str_representation += "\n"
    return str_representation


class Chess:
    def __init__(self):
        self.boardInfo = [[Grid() for _ in range(BOARDSIZE)] for _ in range(BOARDSIZE)]
        self.currColor = ColorType.WHITE
        self.continuePeaceTurn = 0
        self.resetBoard()

    def resetBoard(self):
        # Clear the board
        for x in range(BOARDSIZE):
            for y in range(2, 6):
                self.boardInfo[x][y] = Grid(StoneType.NONE, ColorType.EMPTY, False)

        # White pieces
        self.boardInfo[0][0] = Grid(StoneType.ROOK, ColorType.WHITE, False)
        self.boardInfo[1][0] = Grid(StoneType.KNIGHT, ColorType.WHITE, False)
        self.boardInfo[2][0] = Grid(StoneType.BISHOP, ColorType.WHITE, False)
        self.boardInfo[3][0] = Grid(StoneType.QUEEN, ColorType.WHITE, False)
        self.boardInfo[4][0] = Grid(StoneType.KING, ColorType.WHITE, False)
        self.boardInfo[5][0] = Grid(StoneType.BISHOP, ColorType.WHITE, False)
        self.boardInfo[6][0] = Grid(StoneType.KNIGHT, ColorType.WHITE, False)
        self.boardInfo[7][0] = Grid(StoneType.ROOK, ColorType.WHITE, False)

        for x in range(BOARDSIZE):
            self.boardInfo[x][1] = Grid(StoneType.PAWN, ColorType.WHITE, False)

        # Black pieces
        self.boardInfo[0][7] = Grid(StoneType.ROOK, ColorType.BLACK, False)
        self.boardInfo[1][7] = Grid(StoneType.KNIGHT, ColorType.BLACK, False)
        self.boardInfo[2][7] = Grid(StoneType.BISHOP, ColorType.BLACK, False)
        self.boardInfo[3][7] = Grid(StoneType.QUEEN, ColorType.BLACK, False)
        self.boardInfo[4][7] = Grid(StoneType.KING, ColorType.BLACK, False)
        self.boardInfo[5][7] = Grid(StoneType.BISHOP, ColorType.BLACK, False)
        self.boardInfo[6][7] = Grid(StoneType.KNIGHT, ColorType.BLACK, False)
        self.boardInfo[7][7] = Grid(StoneType.ROOK, ColorType.BLACK, False)

        for x in range(BOARDSIZE):
            self.boardInfo[x][6] = Grid(StoneType.PAWN, ColorType.BLACK, False)

    def get_board_info(self):
        # board_data = []
        # for x in range(BOARDSIZE):
        #     row = []
        #     for y in range(BOARDSIZE):
        #         grid = self.boardInfo[x][y]
        #         row.append(grid_to_list(grid))
        #     board_data.append(row)
        board_data = print_board(self.boardInfo)
        return board_data

    @staticmethod
    def inBoard(mx: int, my: int) -> bool:
        return 0 <= mx < BOARDSIZE and 0 <= my < BOARDSIZE

    def oppColor(self) -> ColorType:
        return ColorType.WHITE if self.currColor == ColorType.BLACK else ColorType.BLACK

    def generateMoves(self, legalMoves: List[Move], mustDefend: bool = True):
        legalMoves.clear()

        for x in range(BOARDSIZE):
            for y in range(BOARDSIZE):
                if self.boardInfo[x][y].color != self.currColor:
                    continue

                piece_type = self.boardInfo[x][y].type

                if piece_type == StoneType.KING:
                    # King moves
                    for dir_idx in range(8):
                        tx = x + dx[dir_idx]
                        ty = y + dy[dir_idx]
                        if (
                            not self.inBoard(tx, ty)
                            or self.boardInfo[tx][ty].color == self.currColor
                        ):
                            continue

                        if mustDefend:
                            if not self.isKingAttackedAfterMove(Move(x, y, tx, ty)):
                                legalMoves.append(Move(x, y, tx, ty))
                        else:
                            legalMoves.append(Move(x, y, tx, ty))

                    # Castling
                    if self.boardInfo[x][y].notMovedYet:
                        kingLine = 7 if self.currColor == ColorType.BLACK else 0
                        if x == 4 and y == kingLine:
                            # Queenside castling
                            if (
                                self.boardInfo[0][kingLine].color == self.currColor
                                and self.boardInfo[0][kingLine].type == StoneType.ROOK
                                and self.boardInfo[0][kingLine].notMovedYet
                            ):
                                if (
                                    self.boardInfo[1][kingLine].color == ColorType.EMPTY
                                    and self.boardInfo[2][kingLine].color
                                    == ColorType.EMPTY
                                    and self.boardInfo[3][kingLine].color
                                    == ColorType.EMPTY
                                    and not self.attacked(self.oppColor(), 2, kingLine)
                                    and not self.attacked(self.oppColor(), 3, kingLine)
                                    and not self.attacked(self.oppColor(), 4, kingLine)
                                ):
                                    if mustDefend:
                                        if not self.isKingAttackedAfterMove(
                                            Move(4, kingLine, 2, kingLine)
                                        ):
                                            legalMoves.append(
                                                Move(4, kingLine, 2, kingLine)
                                            )
                                    else:
                                        legalMoves.append(
                                            Move(4, kingLine, 2, kingLine)
                                        )

                            # Kingside castling
                            if (
                                self.boardInfo[7][kingLine].color == self.currColor
                                and self.boardInfo[7][kingLine].type == StoneType.ROOK
                                and self.boardInfo[7][kingLine].notMovedYet
                            ):
                                if (
                                    self.boardInfo[5][kingLine].color == ColorType.EMPTY
                                    and self.boardInfo[6][kingLine].color
                                    == ColorType.EMPTY
                                    and not self.attacked(self.oppColor(), 4, kingLine)
                                    and not self.attacked(self.oppColor(), 5, kingLine)
                                    and not self.attacked(self.oppColor(), 6, kingLine)
                                ):
                                    if mustDefend:
                                        if not self.isKingAttackedAfterMove(
                                            Move(4, kingLine, 6, kingLine)
                                        ):
                                            legalMoves.append(
                                                Move(4, kingLine, 6, kingLine)
                                            )
                                    else:
                                        legalMoves.append(
                                            Move(4, kingLine, 6, kingLine)
                                        )

                elif piece_type == StoneType.QUEEN:
                    # Queen moves
                    for dir_idx in range(8):
                        tx = x + dx[dir_idx]
                        ty = y + dy[dir_idx]
                        while self.inBoard(tx, ty):
                            if self.boardInfo[tx][ty].color == self.currColor:
                                break
                            elif self.boardInfo[tx][ty].color == self.oppColor():
                                if mustDefend:
                                    if not self.isKingAttackedAfterMove(
                                        Move(x, y, tx, ty)
                                    ):
                                        legalMoves.append(Move(x, y, tx, ty))
                                else:
                                    legalMoves.append(Move(x, y, tx, ty))
                                break
                            else:
                                if mustDefend:
                                    if not self.isKingAttackedAfterMove(
                                        Move(x, y, tx, ty)
                                    ):
                                        legalMoves.append(Move(x, y, tx, ty))
                                else:
                                    legalMoves.append(Move(x, y, tx, ty))
                            tx += dx[dir_idx]
                            ty += dy[dir_idx]

                elif piece_type == StoneType.PAWN:
                    # Pawn moves 2 squares
                    if self.boardInfo[x][y].notMovedYet:
                        if self.boardInfo[x][y].color == ColorType.BLACK:
                            assert y == 6
                        else:
                            assert y == 1

                        tx = x
                        ty = (
                            y - 2
                            if self.boardInfo[x][y].color == ColorType.BLACK
                            else y + 2
                        )
                        nx = x
                        ny = (
                            y - 1
                            if self.boardInfo[x][y].color == ColorType.BLACK
                            else y + 1
                        )

                        if (
                            self.boardInfo[nx][ny].color == ColorType.EMPTY
                            and self.boardInfo[tx][ty].color == ColorType.EMPTY
                        ):
                            if mustDefend:
                                if not self.isKingAttackedAfterMove(Move(x, y, tx, ty)):
                                    legalMoves.append(Move(x, y, tx, ty))
                            else:
                                legalMoves.append(Move(x, y, tx, ty))

                    # En passant
                    for dir in dx_lr:
                        tx = x + dir
                        ty = y
                        ox = x + dir
                        oy = y + (-1 if self.currColor == ColorType.BLACK else 1)

                        if (
                            self.inBoard(tx, ty)
                            and self.boardInfo[tx][ty].color == self.oppColor()
                            and self.boardInfo[tx][ty].type == StoneType.PAWN
                            and self.boardInfo[tx][ty].lastIs2Grid
                            and self.boardInfo[ox][oy].color == ColorType.EMPTY
                        ):
                            if mustDefend:
                                if not self.isKingAttackedAfterMove(Move(x, y, tx, oy)):
                                    legalMoves.append(Move(x, y, tx, oy))
                            else:
                                legalMoves.append(Move(x, y, tx, oy))

                    # Diagonal capture
                    for dir in dx_lr:
                        tx = x + dir
                        ty = y + (-1 if self.currColor == ColorType.BLACK else 1)
                        canProm = (
                            (ty == 0)
                            if self.currColor == ColorType.BLACK
                            else (ty == 7)
                        )

                        if (
                            self.inBoard(tx, ty)
                            and self.boardInfo[tx][ty].color == self.oppColor()
                        ):
                            if canProm:
                                for op in proOps:
                                    if mustDefend:
                                        if not self.isKingAttackedAfterMove(
                                            Move(x, y, tx, ty, stoneSym[op.value])
                                        ):
                                            legalMoves.append(
                                                Move(x, y, tx, ty, stoneSym[op.value])
                                            )
                                    else:
                                        legalMoves.append(
                                            Move(x, y, tx, ty, stoneSym[op.value])
                                        )
                            else:
                                if mustDefend:
                                    if not self.isKingAttackedAfterMove(
                                        Move(x, y, tx, ty)
                                    ):
                                        legalMoves.append(Move(x, y, tx, ty))
                                else:
                                    legalMoves.append(Move(x, y, tx, ty))

                    # Forward move
                    tx = x
                    ty = y + (-1 if self.currColor == ColorType.BLACK else 1)
                    canProm = (
                        (ty == 0) if self.currColor == ColorType.BLACK else (ty == 7)
                    )

                    if (
                        self.inBoard(tx, ty)
                        and self.boardInfo[tx][ty].color == ColorType.EMPTY
                    ):
                        if canProm:
                            for op in proOps:
                                if mustDefend:
                                    if not self.isKingAttackedAfterMove(
                                        Move(x, y, tx, ty, stoneSym[op.value])
                                    ):
                                        legalMoves.append(
                                            Move(x, y, tx, ty, stoneSym[op.value])
                                        )
                                else:
                                    legalMoves.append(
                                        Move(x, y, tx, ty, stoneSym[op.value])
                                    )
                        else:
                            if mustDefend:
                                if not self.isKingAttackedAfterMove(Move(x, y, tx, ty)):
                                    legalMoves.append(Move(x, y, tx, ty))
                            else:
                                legalMoves.append(Move(x, y, tx, ty))

                elif piece_type == StoneType.KNIGHT:
                    # Knight moves
                    for dir_idx in range(8):
                        tx = x + dx_knight[dir_idx]
                        ty = y + dy_knight[dir_idx]
                        if (
                            self.inBoard(tx, ty)
                            and self.boardInfo[tx][ty].color != self.currColor
                        ):
                            if mustDefend:
                                if not self.isKingAttackedAfterMove(Move(x, y, tx, ty)):
                                    legalMoves.append(Move(x, y, tx, ty))
                            else:
                                legalMoves.append(Move(x, y, tx, ty))

                elif piece_type == StoneType.BISHOP:
                    # Bishop moves
                    for dir_idx in range(4):
                        tx = x + dx_ob[dir_idx]
                        ty = y + dy_ob[dir_idx]
                        while self.inBoard(tx, ty):
                            if self.boardInfo[tx][ty].color == self.currColor:
                                break
                            elif self.boardInfo[tx][ty].color == self.oppColor():
                                if mustDefend:
                                    if not self.isKingAttackedAfterMove(
                                        Move(x, y, tx, ty)
                                    ):
                                        legalMoves.append(Move(x, y, tx, ty))
                                else:
                                    legalMoves.append(Move(x, y, tx, ty))
                                break
                            else:
                                if mustDefend:
                                    if not self.isKingAttackedAfterMove(
                                        Move(x, y, tx, ty)
                                    ):
                                        legalMoves.append(Move(x, y, tx, ty))
                                else:
                                    legalMoves.append(Move(x, y, tx, ty))
                            tx += dx_ob[dir_idx]
                            ty += dy_ob[dir_idx]

                elif piece_type == StoneType.ROOK:
                    # Rook moves
                    for dir_idx in range(4):
                        tx = x + dx_strai[dir_idx]
                        ty = y + dy_strai[dir_idx]
                        while self.inBoard(tx, ty):
                            if self.boardInfo[tx][ty].color == self.currColor:
                                break
                            elif self.boardInfo[tx][ty].color == self.oppColor():
                                if mustDefend:
                                    if not self.isKingAttackedAfterMove(
                                        Move(x, y, tx, ty)
                                    ):
                                        legalMoves.append(Move(x, y, tx, ty))
                                else:
                                    legalMoves.append(Move(x, y, tx, ty))
                                break
                            else:
                                if mustDefend:
                                    if not self.isKingAttackedAfterMove(
                                        Move(x, y, tx, ty)
                                    ):
                                        legalMoves.append(Move(x, y, tx, ty))
                                else:
                                    legalMoves.append(Move(x, y, tx, ty))
                            tx += dx_strai[dir_idx]
                            ty += dy_strai[dir_idx]

                elif piece_type == StoneType.NONE:
                    raise RuntimeError("color is not empty but type is none")

    def isLegalMove(self, move: Move) -> bool:
        currLegalMoves = []
        self.generateMoves(currLegalMoves)
        return move in currLegalMoves

    def makeMoveAssumeLegal(self, move: Move) -> bool:
        self.continuePeaceTurn += 1

        sourceGrid = self.boardInfo[move.source_x][move.source_y]
        targetGrid = self.boardInfo[move.target_x][move.target_y]

        if targetGrid.color == self.oppColor():
            self.continuePeaceTurn = 0

        oritarColor = targetGrid.color

        # Move the piece
        targetGrid.type = sourceGrid.type
        targetGrid.color = sourceGrid.color
        targetGrid.notMovedYet = False

        dex = move.target_x - move.source_x
        dey = move.target_y - move.source_y

        # Handle en passant capture
        if sourceGrid.type == StoneType.PAWN:
            nx = move.target_x
            ny = move.source_y
            if abs(dex) == 1 and abs(dey) == 1 and oritarColor == ColorType.EMPTY:
                if (
                    self.boardInfo[nx][ny].type == StoneType.PAWN
                    and self.boardInfo[nx][ny].color == self.oppColor()
                    and self.boardInfo[nx][ny].lastIs2Grid
                ):
                    self.boardInfo[nx][ny].color = ColorType.EMPTY
                    self.boardInfo[nx][ny].type = StoneType.NONE
                    self.boardInfo[nx][ny].lastIs2Grid = False
                    self.boardInfo[nx][ny].notMovedYet = False
                self.continuePeaceTurn = 0

        # Handle castling
        if sourceGrid.type == StoneType.KING and abs(dex) == 2:
            assert abs(dey) == 0

            if move.target_x < move.source_x:  # Queenside
                rookX = 0
                rookToX = 3
            else:  # Kingside
                rookX = 7
                rookToX = 5

            kingLine = 7 if self.currColor == ColorType.BLACK else 0

            # Move the rook
            self.boardInfo[rookToX][kingLine].color = self.currColor
            self.boardInfo[rookToX][kingLine].type = StoneType.ROOK
            self.boardInfo[rookToX][kingLine].notMovedYet = False
            self.boardInfo[rookToX][kingLine].lastIs2Grid = False

            # Clear the rook's original position
            self.boardInfo[rookX][kingLine].color = ColorType.EMPTY
            self.boardInfo[rookX][kingLine].type = StoneType.NONE
            self.boardInfo[rookX][kingLine].notMovedYet = False
            self.boardInfo[rookX][kingLine].lastIs2Grid = False

        # Update pawn's two-square move flag
        if sourceGrid.type == StoneType.PAWN:
            ymoveDist = move.target_y - move.source_y
            if ymoveDist == 2 or ymoveDist == -2:
                targetGrid.lastIs2Grid = True
                self.markAllPawn(move.target_x, move.target_y)
            else:
                self.markAllPawn(-1, -1)
            self.continuePeaceTurn = 0
        else:
            self.markAllPawn(-1, -1)

        # Clear source square
        self.boardInfo[move.source_x][move.source_y].color = ColorType.EMPTY
        self.boardInfo[move.source_x][move.source_y].type = StoneType.NONE
        self.boardInfo[move.source_x][move.source_y].notMovedYet = False
        self.boardInfo[move.source_x][move.source_y].lastIs2Grid = False

        # Handle promotion
        if move.promoptionType != "*":
            targetGrid.type = charSym[move.promoptionType]

        # Switch turn
        self.currColor = self.oppColor()
        return True

    def attacked(self, color: ColorType, mx: int, my: int) -> bool:
        for x in range(BOARDSIZE):
            for y in range(BOARDSIZE):
                if self.boardInfo[x][y].color != color:
                    continue

                dex = mx - x
                dey = my - y
                piece_type = self.boardInfo[x][y].type

                if piece_type == StoneType.KING:
                    if abs(dex) <= 1 and abs(dey) <= 1 and not (dex == 0 and dey == 0):
                        return True

                elif piece_type == StoneType.QUEEN:
                    if self.inSameLine(x, y, mx, my) and self.betweenIsEmpty(
                        x, y, mx, my
                    ):
                        return True

                elif piece_type == StoneType.KNIGHT:
                    if (abs(dex) == 1 and abs(dey) == 2) or (
                        abs(dex) == 2 and abs(dey) == 1
                    ):
                        return True

                elif piece_type == StoneType.BISHOP:
                    if self.inSameObiqueLine(x, y, mx, my) and self.betweenIsEmpty(
                        x, y, mx, my
                    ):
                        return True

                elif piece_type == StoneType.ROOK:
                    if self.inSameStraightLine(x, y, mx, my) and self.betweenIsEmpty(
                        x, y, mx, my
                    ):
                        return True

                elif piece_type == StoneType.PAWN:
                    if (color == ColorType.WHITE and dey == 1 and abs(dex) == 1) or (
                        color == ColorType.BLACK and dey == -1 and abs(dex) == 1
                    ):
                        return True

                elif piece_type == StoneType.NONE:
                    raise RuntimeError("color is not empty but type is none")

        return False

    def betweenIsEmpty(self, sx: int, sy: int, ex: int, ey: int) -> bool:
        assert self.inSameLine(sx, sy, ex, ey)

        dex = 1 if ex > sx else (-1 if ex < sx else 0)
        dey = 1 if ey > sy else (-1 if ey < sy else 0)

        tx = sx + dex
        ty = sy + dey

        while self.inBoard(tx, ty) and not (tx == ex and ty == ey):
            if self.boardInfo[tx][ty].color != ColorType.EMPTY:
                return False
            tx += dex
            ty += dey

        return True

    @staticmethod
    def inSameLine(sx: int, sy: int, ex: int, ey: int) -> bool:
        dex = ex - sx
        dey = ey - sy
        return dex == dey or dex == -dey or dex == 0 or dey == 0

    @staticmethod
    def inSameStraightLine(sx: int, sy: int, ex: int, ey: int) -> bool:
        return sx == ex or sy == ey

    @staticmethod
    def inSameObiqueLine(sx: int, sy: int, ex: int, ey: int) -> bool:
        dex = ex - sx
        dey = ey - sy
        return abs(dex) == abs(dey)

    def isKingAttackedAfterMove(self, move: Move) -> bool:
        copyChess = copy.deepcopy(self)
        copyChess.makeMoveAssumeLegal(move)

        # Find the king
        kingX, kingY = -1, -1
        for x in range(BOARDSIZE):
            for y in range(BOARDSIZE):
                if (
                    copyChess.boardInfo[x][y].color == self.currColor
                    and copyChess.boardInfo[x][y].type == StoneType.KING
                ):
                    kingX, kingY = x, y
                    break
            if kingX != -1:
                break

        return copyChess.attacked(self.oppColor(), kingX, kingY)

    def isMoveValid(self, move: Move, mustDefend: bool = True) -> bool:
        if not (
            self.inBoard(move.source_x, move.source_y)
            and self.inBoard(move.target_x, move.target_y)
        ):
            return False

        source = self.boardInfo[move.source_x][move.source_y]
        target = self.boardInfo[move.target_x][move.target_y]

        if source.color != self.currColor or target.color == self.currColor:
            return False

        dex = move.target_x - move.source_x
        dey = move.target_y - move.source_y

        if source.type == StoneType.KING:
            # Castling
            if dex == -2:
                kingLine = 7 if self.currColor == ColorType.BLACK else 0
                if (
                    move.source_x == 4
                    and move.source_y == kingLine
                    and move.target_x == 2
                    and move.target_y == kingLine
                    and source.notMovedYet
                    and self.boardInfo[0][kingLine].color == self.currColor
                    and self.boardInfo[0][kingLine].type == StoneType.ROOK
                    and self.boardInfo[0][kingLine].notMovedYet
                    and self.boardInfo[1][kingLine].color == ColorType.EMPTY
                    and self.boardInfo[2][kingLine].color == ColorType.EMPTY
                    and self.boardInfo[3][kingLine].color == ColorType.EMPTY
                    and not self.attacked(self.oppColor(), 2, kingLine)
                    and not self.attacked(self.oppColor(), 3, kingLine)
                    and not self.attacked(self.oppColor(), 4, kingLine)
                ):
                    return True

            elif dex == 2:
                kingLine = 7 if self.currColor == ColorType.BLACK else 0
                if (
                    move.source_x == 4
                    and move.source_y == kingLine
                    and move.target_x == 6
                    and move.target_y == kingLine
                    and source.notMovedYet
                    and self.boardInfo[7][kingLine].color == self.currColor
                    and self.boardInfo[7][kingLine].type == StoneType.ROOK
                    and self.boardInfo[7][kingLine].notMovedYet
                    and self.boardInfo[5][kingLine].color == ColorType.EMPTY
                    and self.boardInfo[6][kingLine].color == ColorType.EMPTY
                    and not self.attacked(self.oppColor(), 4, kingLine)
                    and not self.attacked(self.oppColor(), 5, kingLine)
                    and not self.attacked(self.oppColor(), 6, kingLine)
                ):
                    return True

            # Normal king move
            elif abs(dex) <= 1 and abs(dey) <= 1 and not (dex == 0 and dey == 0):
                if not mustDefend or (
                    mustDefend and not self.isKingAttackedAfterMove(move)
                ):
                    return True

        elif source.type == StoneType.QUEEN:
            if self.inSameLine(
                move.source_x, move.source_y, move.target_x, move.target_y
            ) and self.betweenIsEmpty(
                move.source_x, move.source_y, move.target_x, move.target_y
            ):
                if not mustDefend or (
                    mustDefend and not self.isKingAttackedAfterMove(move)
                ):
                    return True

        elif source.type == StoneType.BISHOP:
            if self.inSameObiqueLine(
                move.source_x, move.source_y, move.target_x, move.target_y
            ) and self.betweenIsEmpty(
                move.source_x, move.source_y, move.target_x, move.target_y
            ):
                if not mustDefend or (
                    mustDefend and not self.isKingAttackedAfterMove(move)
                ):
                    return True

        elif source.type == StoneType.ROOK:
            if self.inSameStraightLine(
                move.source_x, move.source_y, move.target_x, move.target_y
            ) and self.betweenIsEmpty(
                move.source_x, move.source_y, move.target_x, move.target_y
            ):
                if not mustDefend or (
                    mustDefend and not self.isKingAttackedAfterMove(move)
                ):
                    return True

        elif source.type == StoneType.KNIGHT:
            if (abs(dex) == 1 and abs(dey) == 2) or (abs(dex) == 2 and abs(dey) == 1):
                if not mustDefend or (
                    mustDefend and not self.isKingAttackedAfterMove(move)
                ):
                    return True

        elif source.type == StoneType.PAWN:
            # Two-square move
            if (
                (source.color == ColorType.BLACK and dey == -2)
                or (source.color == ColorType.WHITE and dey == 2)
            ) and dex == 0:
                nx = move.source_x
                ny = move.source_y + (-1 if source.color == ColorType.BLACK else 1)
                if (
                    source.notMovedYet
                    and self.boardInfo[nx][ny].color == ColorType.EMPTY
                    and target.color == ColorType.EMPTY
                ):
                    if not mustDefend or (
                        mustDefend and not self.isKingAttackedAfterMove(move)
                    ):
                        return True

            # One-square or capture move
            elif (source.color == ColorType.BLACK and dey == -1) or (
                source.color == ColorType.WHITE and dey == 1
            ):
                promtLine = 0 if self.currColor == ColorType.BLACK else 7

                # Check promotion
                if move.promoptionType != "*" and move.target_y != promtLine:
                    return False
                if move.target_y == promtLine and move.promoptionType not in [
                    "q",
                    "b",
                    "n",
                    "r",
                ]:
                    return False

                # Diagonal capture
                if abs(dex) == 1:
                    if target.color == self.oppColor():
                        if not mustDefend or (
                            mustDefend and not self.isKingAttackedAfterMove(move)
                        ):
                            return True
                    elif target.color == ColorType.EMPTY:
                        # En passant
                        nx = move.source_x + dex
                        ny = move.source_y
                        if (
                            self.boardInfo[nx][ny].color == self.oppColor()
                            and self.boardInfo[nx][ny].type == StoneType.PAWN
                            and self.boardInfo[nx][ny].lastIs2Grid
                        ):
                            if not mustDefend or (
                                mustDefend and not self.isKingAttackedAfterMove(move)
                            ):
                                return True

                # Forward move
                elif abs(dex) == 0:
                    if target.color == ColorType.EMPTY:
                        if not mustDefend or (
                            mustDefend and not self.isKingAttackedAfterMove(move)
                        ):
                            return True

        elif source.type == StoneType.NONE:
            raise RuntimeError("color is not empty but type is none")

        return False

    def markAllPawn(self, except_x: int, except_y: int):
        for x in range(BOARDSIZE):
            for y in range(BOARDSIZE):
                if (
                    self.boardInfo[x][y].color == self.currColor
                    and self.boardInfo[x][y].type == StoneType.PAWN
                    and not (x == except_x and y == except_y)
                ):
                    self.boardInfo[x][y].lastIs2Grid = False

    def winAfterMove(self, move: Move) -> bool:
        copyChess = copy.deepcopy(self)
        copyChess.makeMoveAssumeLegal(move)
        oppLegalMoves = []
        copyChess.generateMoves(oppLegalMoves)
        return len(oppLegalMoves) == 0

    def currKingAttacked(self) -> bool:
        kingX, kingY = -1, -1
        for x in range(BOARDSIZE):
            for y in range(BOARDSIZE):
                if (
                    self.boardInfo[x][y].color == self.currColor
                    and self.boardInfo[x][y].type == StoneType.KING
                ):
                    kingX, kingY = x, y
                    break
            if kingX != -1:
                break

        return self.attacked(self.oppColor(), kingX, kingY)

    def isOppKingAttackedAfterMove(self, move: Move) -> bool:
        copyChess = copy.deepcopy(self)
        copyChess.makeMoveAssumeLegal(move)

        kingX, kingY = -1, -1
        for x in range(BOARDSIZE):
            for y in range(BOARDSIZE):
                if (
                    copyChess.boardInfo[x][y].color == self.oppColor()
                    and copyChess.boardInfo[x][y].type == StoneType.KING
                ):
                    kingX, kingY = x, y
                    break
            if kingX != -1:
                break

        return copyChess.attacked(self.currColor, kingX, kingY)

    def exceedMaxPeaceState(self) -> bool:
        return self.continuePeaceTurn >= 50


def getInputBotzone(chess: Chess):
    import sys

    str_input = sys.stdin.readline().strip()
    input_data = json.loads(str_input)

    turnID = len(input_data["responses"])

    # Determine bot color
    first_source = input_data["requests"][0]["source"]
    chess.myColor = ColorType.WHITE if first_source == "-1" else ColorType.BLACK

    for i in range(turnID):
        # Opponent's move
        curSource = input_data["requests"][i]["source"]
        curTarget = input_data["requests"][i]["target"]
        curPromp = input_data["requests"][i]["promotion"]

        if curSource != "-1":
            curMove = Move.from_strings(curSource, curTarget, curPromp)
            if not chess.isMoveValid(curMove):
                raise RuntimeError("input is not valid!")
            chess.makeMoveAssumeLegal(curMove)

        # Bot's previous move
        curSource = input_data["responses"][i]["source"]
        curTarget = input_data["responses"][i]["target"]
        curPromp = input_data["responses"][i]["promotion"]

        curMove = Move.from_strings(curSource, curTarget, curPromp)
        if not chess.isMoveValid(curMove):
            raise RuntimeError("input is not valid!")
        chess.makeMoveAssumeLegal(curMove)

    # Current opponent's move
    curSource = input_data["requests"][turnID]["source"]
    curTarget = input_data["requests"][turnID]["target"]
    curPromp = input_data["requests"][turnID]["promotion"]

    if curSource != "-1":
        curMove = Move.from_strings(curSource, curTarget, curPromp)
        if not chess.isMoveValid(curMove):
            raise RuntimeError("input is not valid!")
        chess.makeMoveAssumeLegal(curMove)


def giveOutputBotzone(chess: Chess):
    retMoves = []
    chess.generateMoves(retMoves)

    ret = {"response": {}}

    if not retMoves:
        ret["response"]["source"] = "-1"
        ret["response"]["target"] = "-1"
        ret["response"]["promotion"] = "*"
    else:
        random.seed(time.time())
        choice = random.randint(0, len(retMoves) - 1)
        selMove = retMoves[choice]

        ret["response"]["source"] = pgnint2char(selMove.source_x) + int2char(
            selMove.source_y
        )
        ret["response"]["target"] = pgnint2char(selMove.target_x) + int2char(
            selMove.target_y
        )
        ret["response"]["promotion"] = selMove.promoptionType

    print(json.dumps(ret))


def get_chess_type_name(chess, move_info) -> str:
    """
    根据move_info中的source坐标，获取棋子类型的首字母

    Args:
        chess: Chess对象
        move_info: 包含source_x和source_y的字典

    Returns:
        棋子类型的首字母字符串
    """
    # 获取坐标
    source_x = move_info["source_x"]
    source_y = move_info["source_y"]

    # 验证坐标是否在棋盘内
    if not Chess.inBoard(source_x, source_y):
        return ""

    # 获取格子
    grid = chess.boardInfo[source_x][source_y]

    # 棋子类型到首字母的映射
    type_to_letter = {
        StoneType.KING: "K",
        StoneType.QUEEN: "Q",
        StoneType.ROOK: "R",
        StoneType.BISHOP: "B",
        StoneType.KNIGHT: "N",  # 注意：Knight通常用N表示，因为K已经被King用了
        StoneType.PAWN: "P",
        StoneType.NONE: "",
    }

    # 返回对应的首字母
    return type_to_letter.get(grid.type, "")


def extract_move(response_text: str, valid_moves: list) -> dict:
    """
    从LLM响应中提取移动信息，匹配有效的走法

    Args:
        response_text: LLM的响应文本
        valid_moves: 有效的走法字符串列表（如 ["a2-a4", "e2e4q", "b1c3"]）

    Returns:
        包含source, target, promotion的字典，或None如果未找到有效走法
    """
    # 默认响应
    default_response = {"source": "-1", "target": "-1", "promotion": "*"}

    if not response_text or not valid_moves:
        return 0, default_response

    # 清理响应文本：转换为小写，移除多余空白
    cleaned_text = response_text.lower().strip()

    # 尝试多种模式匹配
    pattern = r"\b([a-h][1-8])\s*[-]?\s*([a-h][1-8])\s*(?:[-=]?\s*([qbnr]))?\b"
    src = None

    matches = re.findall(pattern, cleaned_text)
    if matches:
        for match in matches:
            if isinstance(match, tuple):
                if len(match) >= 2:
                    # 从元组中提取
                    src, dst = match[0], match[1]
                    promotion = match[2] if len(match) > 2 and match[2] else "*"
                    match_type = "tuple"

    if src:
        move = src + "-" + dst
        if promotion != "*":
            move += "-" + promotion
        if move in valid_moves:
            return 1, {"source": src, "target": dst, "promotion": promotion}
    return 0, default_response


def extract_answer(response_text: str) -> str:
    """
    提取answer/Answer后面的所有内容

    Args:
        response_text: 响应文本

    Returns:
        answer后面的内容字符串，如果没有找到则返回空字符串
    """
    if not response_text:
        return ""

    # 清理文本
    text = response_text.strip()

    # 匹配模式：不区分大小写，匹配"answer:"后面的所有内容
    patterns = [
        # 模式1: Answer: 后面所有内容（包含空格和换行）
        r"(?:answer|Answer|ANSWER|回答|answer is|Answer is)[\s:]*([\s\S]*)",
        # 模式2: 冒号或空格后的内容
        r"[:：]\s*([^\n]*)",
        # 模式3: 最后一行的内容（如果没有明确标记）
        r"(?:\n|^)([^\n]+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            if content:  # 确保内容不为空
                return content

    # 如果没有找到明确的answer标记，返回整个文本
    return text


rule_prompt = """
        You are a Chess player. Chess is a 2-player game playing on a 8x8 board, and the goal is to checkmate your opponent's king.
        ## Pieces & Movement:

        * King (K): Moves one square in any direction.

        * Queen (Q): Moves any distance in any straight or diagonal line.

        * Rook (R): Moves any distance horizontally or vertically.

        * Bishop (B): Moves any distance diagonally.

        * Knight (N): Moves in "L" shape: 2 squares one way + 1 square perpendicular.

        * Pawn (P):

            * Forward 1 square (never backward)

            * First move: optionally 2 squares forward

            * Captures diagonally forward

            * Promotion: Reaches last rank → any piece (except king)
        
        ## Special rules: 
        * Castling: King moves 2 squares toward rook, rook jumps over. Conditions:

            * Neither piece has moved

            * No pieces between

            * King not in check

            * King doesn't pass through attacked squares

        * En Passant: Pawn that moved 2 squares can be captured by adjacent enemy pawn as if it moved 1 square.

        * Check: King under attack must escape immediately.

        * Checkmate: King in check with no legal moves → game ends.

        * Stalemate: King not in check but has no legal moves → draw.

        ## Board and Chess piece Representation:
        * Board is represented as [a-h][1-8]
        * Origin: bottom-left corner (a1) 
        * White side: Bottom (ranks 1-2)
        * Black side: Top (ranks 7-8)
        * X-axis: Files `a` to `h` (left to right)
        * Y-axis: Ranks `1` to `8` (bottom to top)

        ## Piece encoding format: `[Type][Color][2Step][Moved]`
        
        * Type (Piece Type):
            * `K` - King
            * `Q`- Queen
            * `R`- Rook
            * `B` - Bishop
            * `K` - Knight
            * `P` - Pawn
        * Color (Player):
            * `W` - White (moves first)
            * `B` - Black
        * 2Step (En Passant flag)
            * `F` - Did NOT move 2 squares last turn
            * `T` - Moved 2 squares last turn (en passant eligible)
        * Moved (Movement flag)
            * `1` - Has moved before
            * `0` - Has NOT moved yet
        
        ### Examples: 
            * PWF1: White Pawn, not available for en passant, already moved; 
            * RBF0: Black Rook, never moved (castling eligible);
            * KWT1: White king, irrelevant 2-step flag, has moved;
            * QWF0 = White queen, irrelevant 2-step flag, never moved.

        Now is your turn, to your best ability, choose your move to maximize your chances of winning.
        Please briefly evaluate a few proimsing moves, provide reason for your final choice, and output one of the valid actions with specified format.
        Your response format should be:
        Evaluation: [Your Evaluation]
        Reason: [Your Reason]
        Answer: [Your Answer]
        """

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
    else:
        print(
            json.dumps(
                {"response": {"x": -1, "y": -1}, "debug": "Invalid access mode."}
            )
        )
    if access_mode:
        chess = Chess()
        getInputBotzone(chess)
        # get color
        if chess.myColor == ColorType.WHITE:
            color_prompt = "You are playing as White.\n"
        else:
            color_prompt = "You are playing as Black.\n"

        # get board
        state_prompt = (
            f"Current state representation is as follows:{chess.get_board_info()}"
        )
        # get valid moves
        retMoves = []
        chess.generateMoves(retMoves)
        move_str_list = []
        move_info_list = []
        move_type_list = []
        for mv in retMoves:
            mv_str, internal_rep = move_to_string(mv)
            move_info_list.append(internal_rep)
            move_str_list.append(mv_str)
            chess_type = get_chess_type_name(chess, internal_rep)
            move_type_list.append(chess_type)
        valid_move_info = list(zip(move_type_list, move_str_list, move_info_list))
        valid_move_prompt = "Your valid moves are (src-dst-promotion, or src-dst):\n["
        valid_move_prompt += ", ".join(
            [f"{valid_move[0]}: {valid_move[1]}" for valid_move in valid_move_info]
        )
        valid_move_prompt += "]\n"
        answer_template_prompt = (
            "Your answer format should be: Answer: piece-name: move. \n"
            "Piece-name and move (src-dst-promotion or src-dst) should be directly copied EXACTLY from valid move list.\n"
            "Example of valid output format: N: a1-b3; P: e7-e8-q; Piece B: g5-f4.\n"
            "Please select a move from your valid moves that maximize your probability of winning.\n"
        )

        ret = {"response": {}}
        # Fault Tolerance
        trial_count = 0
        if len(retMoves) == 0:
            ret["response"]["source"] = "-1"
            ret["response"]["target"] = "-1"
            ret["response"]["promotion"] = "*"
            print(json.dumps(ret))
            trial_count = 3

        invalid_responses = []

        while trial_count < 3:
            trial_count += 1
            if len(invalid_responses) == 0:
                invalid_prompt = ""
            else:
                invalid_prompt = f"Your previous invalid answers are: {', '.join(invalid_responses)}."
            user_prompt = (
                color_prompt
                + state_prompt
                + valid_move_prompt
                + answer_template_prompt
                + invalid_prompt
            )

            # gether response from llm
            responsed_text, reasoning_text = query_api(
                api_base,
                api_key,
                model_name,
                rule_prompt,
                user_prompt,
            )
            answer_text = extract_answer(responsed_text)
            valid_signal, response = extract_move(answer_text, move_str_list)
            if valid_signal:
                break
            invalid_responses.append(answer_text)

        if len(retMoves) != 0:
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
