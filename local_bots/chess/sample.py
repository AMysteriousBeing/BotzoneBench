import json
import time
import random
from enum import Enum
from typing import List, Tuple, Dict, Optional
import copy

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
    currBotColor = ColorType.WHITE if first_source == "-1" else ColorType.BLACK

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


def main():
    chess = Chess()
    getInputBotzone(chess)
    giveOutputBotzone(chess)


if __name__ == "__main__":
    main()
