#include <iostream>
#include <string>
#include <vector>
#include <cmath>
#include <map>
#include <cassert>
#include <algorithm>
#include "jsoncpp/json.h"


using std::string;
using std::vector;
using std::map;
using std::cin;
using std::cout;
using std::endl;

#define stoneTypeNum 7
#define BOARDSIZE 8
enum stoneType {None = 0, King=1, Queen=2, Bishop=3, Knight=4, Rook=5, Pawn=6};
enum colorType {BLACK=0, WHITE=1, EMPTY = 2};
char stoneSym[] = "*kqbnrp";
map<char,stoneType> charSym = {{stoneSym[0], None}, {stoneSym[1], King},
                               {stoneSym[2], Queen}, {stoneSym[3], Bishop},
                               {stoneSym[4], Knight}, {stoneSym[5], Rook},
                               {stoneSym[6], Pawn}};

int dx[] = {-1,-1,-1,0,0,1,1,1};
int dy[] = {-1,0,1,-1,1,-1,0,1};
int dx_ob[] = {-1,1,-1,1};
int dy_ob[] = {-1,-1,1,1};
int dx_strai[] = {-1,0,0,1};
int dy_strai[] = {0,-1,1,0};
int dx_hor[] = {-1,1};
int dy_hor[] = {0,0};
int dx_lr[] = {-1,1};
int dx_knight[] = {-2,-2,-1,-1,1,1,2,2};
int dy_knight[] = {-1,1,-2,2,-2,2,-1,1};
stoneType proOps[] = {Queen, Knight, Bishop, Rook};


int pgnchar2int(char c) {
    return (int)c - (int)'a';
}

char pgnint2char(int i) {
    return (char)((int)'a' + i);
}

int char2int(char c) {
    return (int)c - (int)'1';
}

char int2char(int i) {
    return (char)((int)'1' + i);
}

struct Move {
    int source_x, source_y, target_x, target_y;
    char promoptionType;
    Move() {source_x = -1; source_y = -1; target_x = -1; target_y = -1; promoptionType = '*';};
    Move(int msx, int msy, int mtx, int mty, char mtype = '*'): source_x(msx), source_y(msy),
                                                                target_x(mtx), target_y(mty), promoptionType(mtype) {;}
    Move(string msource, string mtarget, string mpromp="*") {
        source_x = pgnchar2int(msource[0]);
        source_y = char2int(msource[1]);
        target_x = pgnchar2int(mtarget[0]);
        target_y = char2int(mtarget[1]);
        promoptionType = mpromp[0];
    }
    bool operator ==(const Move& other) {
        return source_x == other.source_x && source_y == other.source_y && target_x == other.target_x
               && target_y == other.target_y && promoptionType == other.promoptionType;
    }
};

struct Grid {
    stoneType type;
    colorType color;
    bool lastIs2Grid;
    bool notMovedYet;
    Grid () : type(None), color(EMPTY), lastIs2Grid(false), notMovedYet(true) {;}
    Grid (stoneType mtype, colorType mcolor, bool mlastIs2Grid = false, bool mnotMovedYet= true):
            type(mtype), color(mcolor), lastIs2Grid(mlastIs2Grid), notMovedYet(mnotMovedYet) {;}
};

class Chess {
private:
    Grid boardInfo[BOARDSIZE][BOARDSIZE];
    colorType currColor;
    int continuePeaceTurn = 0;
public:
    Chess();
    void resetBoard();
    void generateMoves(vector<Move> &legalMoves, bool mustDefend=true);
    static bool inBoard(int mx, int my);
    colorType oppColor();
    bool isMoveValid(const Move& move, bool mustDefend=true);
    bool isLegalMmove(const Move& move);
    bool makeMoveAssumeLegal(const Move& move);
    void markAllPawn(int except_x, int except_y);
    bool attacked(colorType color, int mx, int my);
    bool betweenIsEmpty(int sx, int sy, int ex, int ey);
    static bool inSameLine(int sx, int sy, int ex, int ey);
    static bool inSameStraightLine(int sx, int sy, int ex, int ey);
    static bool inSameObiqueLine(int sx, int sy, int ex, int ey);
    bool isKingAttackedAfterMove(const Move& move);
    bool isOppKingAttackedAfterMove(const Move& move);
    bool currKingAttacked(const Move& move);
    bool winAfterMove(const Move& move);
    Chess& operator = (const Chess& other);
    Chess(const Chess& other);
    bool exceedMaxPeaceState();
};

void getInputBotzone(Chess& chess);
void giveOutputBotzone(Chess& chess);

int main() {
    Chess chess;
    getInputBotzone(chess);
    giveOutputBotzone(chess);
    return 0;
}


void giveOutputBotzone(Chess& chess) {
    vector<Move> retMoves;
    chess.generateMoves(retMoves);
    Json::Value ret;

    if (retMoves.empty()) {
        ret["response"]["source"] = string("-1");
        ret["response"]["target"] = string("-1");
        ret["response"]["promotion"] = string("*");
    } else {
        srand(time(nullptr));
        int choice = rand() % retMoves.size();
        auto selMove = retMoves[choice];
        ret["response"]["source"] = string(1, pgnint2char(selMove.source_x)) + string(1, int2char(selMove.source_y));
        ret["response"]["target"] = string(1, pgnint2char(selMove.target_x)) + string(1, int2char(selMove.target_y));
        ret["response"]["promotion"] = string(1, selMove.promoptionType);
    }
    Json::FastWriter writer;
    cout << writer.write(ret) << endl;
}

void getInputBotzone(Chess& chess) {
    string str;
    getline(cin, str);
    Json::Reader reader;
    Json::Value input;
    reader.parse(str, input);
    int turnID = input["responses"].size();
    // 第一回合收到的起点是"-1", 说明我是白方
    colorType currBotColor =
            input["requests"][(Json::Value::UInt) 0]["source"].asString() == "-1" ?  WHITE: BLACK;
    string curSource, curTarget, curPromp;
    for (int i = 0; i < turnID; i++)
    {
        // 根据这些输入输出逐渐恢复状态到当前回合
        curSource = input["requests"][i]["source"].asString();
        curTarget = input["requests"][i]["target"].asString();
        curPromp = input["requests"][i]["promotion"].asString();
        if (curSource != "-1") {
            Move curMove(curSource, curTarget, curPromp);
            if (!chess.isMoveValid(curMove)) {
                throw std::runtime_error("input is not valid!");
            }
            chess.makeMoveAssumeLegal(curMove);
        }

        curSource = input["responses"][i]["source"].asString();
        curTarget = input["responses"][i]["target"].asString();
        curPromp = input["responses"][i]["promotion"].asString();
        Move curMove(curSource, curTarget, curPromp);
        if (!chess.isMoveValid(curMove)) {
            throw std::runtime_error("input is not valid!");
        }
        chess.makeMoveAssumeLegal(curMove);
    }

    curSource = input["requests"][turnID]["source"].asString();
    curTarget = input["requests"][turnID]["target"].asString();
    curPromp = input["requests"][turnID]["promotion"].asString();
    if (curSource != "-1") {
        Move curMove(curSource, curTarget, curPromp);
        if (!chess.isMoveValid(curMove)) {
            throw std::runtime_error("input is not valid!");
        }
        chess.makeMoveAssumeLegal(curMove);
    }

}

void Chess::resetBoard() {
    for (int x = 0; x < BOARDSIZE; x++) {
        for (int y = 2; y <= 5; y++) {
            boardInfo[x][y] = Grid(None, EMPTY, false);
        }
    }

    boardInfo[0][0] = Grid(Rook, WHITE, false);
    boardInfo[1][0] = Grid(Knight, WHITE, false);
    boardInfo[2][0] = Grid(Bishop, WHITE, false);
    boardInfo[3][0] = Grid(Queen, WHITE, false);
    boardInfo[4][0] = Grid(King, WHITE, false);
    boardInfo[5][0] = Grid(Bishop, WHITE, false);
    boardInfo[6][0] = Grid(Knight, WHITE, false);
    boardInfo[7][0] = Grid(Rook, WHITE, false);

    boardInfo[0][1] = Grid(Pawn, WHITE, false);
    boardInfo[1][1] = Grid(Pawn, WHITE, false);
    boardInfo[2][1] = Grid(Pawn, WHITE, false);
    boardInfo[3][1] = Grid(Pawn, WHITE, false);
    boardInfo[4][1] = Grid(Pawn, WHITE, false);
    boardInfo[5][1] = Grid(Pawn, WHITE, false);
    boardInfo[6][1] = Grid(Pawn, WHITE, false);
    boardInfo[7][1] = Grid(Pawn, WHITE, false);

    boardInfo[0][7] = Grid(Rook, BLACK, false);
    boardInfo[1][7] = Grid(Knight, BLACK, false);
    boardInfo[2][7] = Grid(Bishop, BLACK, false);
    boardInfo[3][7] = Grid(Queen, BLACK, false);
    boardInfo[4][7] = Grid(King, BLACK, false);
    boardInfo[5][7] = Grid(Bishop, BLACK, false);
    boardInfo[6][7] = Grid(Knight, BLACK, false);
    boardInfo[7][7] = Grid(Rook, BLACK, false);

    boardInfo[0][6] = Grid(Pawn, BLACK, false);
    boardInfo[1][6] = Grid(Pawn, BLACK, false);
    boardInfo[2][6] = Grid(Pawn, BLACK, false);
    boardInfo[3][6] = Grid(Pawn, BLACK, false);
    boardInfo[4][6] = Grid(Pawn, BLACK, false);
    boardInfo[5][6] = Grid(Pawn, BLACK, false);
    boardInfo[6][6] = Grid(Pawn, BLACK, false);
    boardInfo[7][6] = Grid(Pawn, BLACK, false);
}

Chess::Chess() {
    resetBoard();
    currColor = WHITE;
    continuePeaceTurn = 0;
}

void Chess::generateMoves(vector<Move> &legalMoves, bool mustDefend) {
    legalMoves.clear();
    for (int x = 0; x < BOARDSIZE; x++) {
        for (int y = 0; y < BOARDSIZE; y++) {
            if (boardInfo[x][y].color == currColor) {
                switch (boardInfo[x][y].type) {
                    case King: {
                        for (int dir = 0; dir < 8; dir++) {
                            int tx = x + dx[dir];
                            int ty = y + dy[dir];
                            if (!inBoard(tx, ty) || boardInfo[tx][ty].color == currColor)
                                continue;
                            if (mustDefend) {
                                if (!isKingAttackedAfterMove(Move(x,y,tx,ty))) {
                                    legalMoves.emplace_back(x, y, tx, ty);
                                }
                            } else {
                                legalMoves.emplace_back(x, y, tx, ty);
                            }
                        }
                        // my king not moved, position exchange check
                        if (boardInfo[x][y].notMovedYet && boardInfo[x][y].color == currColor) {
                            int kingLine = currColor == BLACK ? 7 : 0;
                            assert(x == 4 && y == kingLine);
                            if (boardInfo[0][kingLine].color == currColor &&
                                boardInfo[0][kingLine].type == Rook &&
                                boardInfo[0][kingLine].notMovedYet)   {
                                if (boardInfo[1][kingLine].color == EMPTY
                                    && boardInfo[2][kingLine].color == EMPTY
                                    && boardInfo[3][kingLine].color == EMPTY
                                    && !attacked(oppColor(), 2, kingLine)
                                    && !attacked(oppColor(), 3, kingLine)
                                    && !attacked(oppColor(), 4, kingLine)) {
                                    if (mustDefend) {
                                        if (!isKingAttackedAfterMove(Move(4, kingLine, 2, kingLine))) {
                                            legalMoves.emplace_back(4, kingLine, 2, kingLine);
                                        }
                                    } else {
                                        legalMoves.emplace_back(4, kingLine, 2, kingLine);
                                    }
                                }
                            } else if (boardInfo[7][kingLine].color == currColor &&
                                       boardInfo[7][kingLine].type == Rook &&
                                       boardInfo[7][kingLine].notMovedYet) {
                                if (boardInfo[5][kingLine].color == EMPTY
                                    && boardInfo[6][kingLine].color == EMPTY
                                    && !attacked(oppColor(), 4, kingLine)
                                    && !attacked(oppColor(), 5, kingLine)
                                    && !attacked(oppColor(), 6, kingLine)) {
                                    if (mustDefend) {
                                        if (!isKingAttackedAfterMove(Move(4, kingLine, 6, kingLine))) {
                                            legalMoves.emplace_back(4, kingLine, 6, kingLine);
                                        }
                                    } else {
                                        legalMoves.emplace_back(4, kingLine, 6, kingLine);
                                    }
                                }
                            }
                        }
                        break;
                    }
                    case Queen: {
                        for (int dir = 0; dir < 8; dir++) {
                            int tx = x + dx[dir], ty = y + dy[dir];
                            while (inBoard(tx, ty)) {
                                if (boardInfo[tx][ty].color == currColor) {
                                    break;
                                } else if (boardInfo[tx][ty].color == oppColor()) {
                                    if (mustDefend) {
                                        if (!isKingAttackedAfterMove(Move(x,y,tx,ty))) {
                                            legalMoves.emplace_back(x, y, tx, ty);
                                        }
                                    } else {
                                        legalMoves.emplace_back(x, y, tx, ty);
                                    }
                                    break;
                                } else {
                                    assert(boardInfo[tx][ty].color == EMPTY);
                                    if (mustDefend) {
                                        if (!isKingAttackedAfterMove(Move(x,y,tx,ty))) {
                                            legalMoves.emplace_back(x, y, tx, ty);
                                        }
                                    } else {
                                        legalMoves.emplace_back(x, y, tx, ty);
                                    }
                                }
                                tx += dx[dir];
                                ty += dy[dir];
                            }
                        }
                        break;
                    }
                    case Pawn: {
                        // can move 2 grids?
                        if (boardInfo[x][y].notMovedYet) {
                            if (boardInfo[x][y].color == BLACK) {
                                assert(y == 6);
                            } else {
                                assert(y == 1);
                            }
                            int tx = x, ty = boardInfo[x][y].color==BLACK ? y - 2 : y + 2;
                            int nx = x, ny = boardInfo[x][y].color==BLACK ? y - 1 : y + 1;
                            if (boardInfo[nx][ny].color == EMPTY && boardInfo[tx][ty].color == EMPTY) {
                                if (mustDefend) {
                                    if (!isKingAttackedAfterMove(Move(x,y,tx,ty))) {
                                        legalMoves.emplace_back(x, y, tx, ty);
                                    }
                                } else {
                                    legalMoves.emplace_back(x, y, tx, ty);
                                }
                            }
                        }

                        // can move obique(ep), imposibble for promption in this case
                        for (int dir : dx_lr) {
                            int tx = x + dir, ty = y;
                            int ox = x + dir, oy = y + (currColor == BLACK ? -1 : 1);
                            if (inBoard(tx, ty) && boardInfo[tx][ty].color == oppColor()
                                && boardInfo[tx][ty].type == Pawn
                                && boardInfo[tx][ty].lastIs2Grid
                                && boardInfo[ox][oy].color == EMPTY) {
                                if (mustDefend) {
                                    if (!isKingAttackedAfterMove(Move(x, y, tx, y + (currColor == BLACK ? -1 : 1)))) {
                                        legalMoves.emplace_back(x, y, tx, y + (currColor == BLACK ? -1 : 1));
                                    }
                                } else {
                                    legalMoves.emplace_back(x, y, tx, y + (currColor == BLACK ? -1 : 1));
                                }
                            }
                        }

                        // can move obique(eat)?
                        for (int dir : dx_lr) {
                            int tx = x + dir, ty = y + (currColor == BLACK ? -1 : 1);
                            bool canProm = (currColor == BLACK ? (ty == 0) : (ty == 7));
                            if (inBoard(tx, ty) && boardInfo[tx][ty].color == oppColor()) {
                                if (canProm) {
                                    for (stoneType op : proOps) {
                                        if (mustDefend) {
                                            if (!isKingAttackedAfterMove(Move(x,y,tx,ty, stoneSym[op]))) {
                                                legalMoves.emplace_back(x, y, tx, ty, stoneSym[op]);
                                            }
                                        } else {
                                            legalMoves.emplace_back(x, y, tx, ty, stoneSym[op]);
                                        }
                                    }
                                } else {
                                    if (mustDefend) {
                                        if (!isKingAttackedAfterMove(Move(x,y,tx,ty))) {
                                            legalMoves.emplace_back(x, y, tx, ty);
                                        }
                                    } else {
                                        legalMoves.emplace_back(x, y, tx, ty);
                                    }
                                }
                            }
                        }

                        // can move 1 grid?
                        int tx = x, ty = y + (currColor == BLACK ? -1 : 1);
                        bool canProm = (currColor == BLACK ? (ty == 0) : (ty == 7));
                        if (inBoard(tx, ty) && boardInfo[tx][ty].color == EMPTY) {
                            if (canProm) {
                                for (stoneType op : proOps) {
                                    if (mustDefend) {
                                        if (!isKingAttackedAfterMove(Move(x,y,tx,ty, stoneSym[op]))) {
                                            legalMoves.emplace_back(x, y, tx, ty, stoneSym[op]);
                                        }
                                    } else {
                                        legalMoves.emplace_back(x, y, tx, ty, stoneSym[op]);
                                    }
                                }
                            } else {
                                if (mustDefend) {
                                    if (!isKingAttackedAfterMove(Move(x,y,tx,ty))) {
                                        legalMoves.emplace_back(x, y, tx, ty);
                                    }
                                } else {
                                    legalMoves.emplace_back(x, y, tx, ty);
                                }
                            }
                        }
                        break;
                    }
                    case Knight: {
                        for (int dir = 0; dir < 8; dir++) {
                            int tx = x + dx_knight[dir], ty = y + dy_knight[dir];
                            if (inBoard(tx, ty) && boardInfo[tx][ty].color != currColor) {
                                if (mustDefend) {
                                    if (!isKingAttackedAfterMove(Move(x,y,tx,ty))) {
                                        legalMoves.emplace_back(x, y, tx, ty);
                                    }
                                } else {
                                    legalMoves.emplace_back(x, y, tx, ty);
                                }
                            }
                        }
                        break;
                    }
                    case Bishop: {
                        for (int dir = 0; dir < 4; dir++) {
                            int tx = x + dx_ob[dir], ty = y + dy_ob[dir];
                            while (inBoard(tx, ty)) {
                                if (boardInfo[tx][ty].color == currColor) {
                                    break;
                                } else if (boardInfo[tx][ty].color == oppColor()) {
                                    if (mustDefend) {
                                        if (!isKingAttackedAfterMove(Move(x,y,tx,ty))) {
                                            legalMoves.emplace_back(x, y, tx, ty);
                                        }
                                    } else {
                                        legalMoves.emplace_back(x, y, tx, ty);
                                    }
                                    break;
                                } else {
                                    assert(boardInfo[tx][ty].color == EMPTY);
                                    if (mustDefend) {
                                        if (!isKingAttackedAfterMove(Move(x,y,tx,ty))) {
                                            legalMoves.emplace_back(x, y, tx, ty);
                                        }
                                    } else {
                                        legalMoves.emplace_back(x, y, tx, ty);
                                    }
                                }
                                tx += dx_ob[dir];
                                ty += dy_ob[dir];
                            }
                        }
                        break;
                    }
                    case Rook: {
                        for (int dir = 0; dir < 4; dir++) {
                            int tx = x + dx_strai[dir];
                            int ty = y + dy_strai[dir];
                            while (inBoard(tx, ty)) {
                                if (boardInfo[tx][ty].color == currColor) {
                                    break;
                                } else if (boardInfo[tx][ty].color == oppColor()) {
                                    if (mustDefend) {
                                        if (!isKingAttackedAfterMove(Move(x,y,tx,ty))) {
                                            legalMoves.emplace_back(x, y, tx, ty);
                                        }
                                    } else {
                                        legalMoves.emplace_back(x, y, tx, ty);
                                    }
                                    break;
                                } else {
                                    assert(boardInfo[tx][ty].color == EMPTY);
                                    if (mustDefend) {
                                        if (!isKingAttackedAfterMove(Move(x,y,tx,ty))) {
                                            legalMoves.emplace_back(x, y, tx, ty);
                                        }
                                    } else {
                                        legalMoves.emplace_back(x, y, tx, ty);
                                    }
                                }
                                tx += dx_strai[dir];
                                ty += dy_strai[dir];
                            }
                        }
                        break;
                    }
                    case None:
                        throw std::runtime_error("color is not empty but type is none");
                }
            }
        }
    }
}

bool Chess::inBoard(int mx, int my) {
    return mx >= 0 && mx < BOARDSIZE && my >= 0 && my < BOARDSIZE;
}

colorType Chess::oppColor() {
    return currColor == BLACK ? WHITE : BLACK;
}

bool Chess::isLegalMmove(const Move &move) {
    vector<Move> currLegalMoves;
    generateMoves(currLegalMoves);
    auto fi_iter = std::find(currLegalMoves.begin(), currLegalMoves.end(), move);
    return fi_iter != currLegalMoves.end();
}

bool Chess::makeMoveAssumeLegal(const Move &move) {

    continuePeaceTurn++;

    auto& sourceGrid = boardInfo[move.source_x][move.source_y];
    auto& targetGrid = boardInfo[move.target_x][move.target_y];

    if (targetGrid.color == oppColor()) {
        continuePeaceTurn = 0;
    }
    colorType oritarColor = targetGrid.color;

    targetGrid.type = sourceGrid.type;
    targetGrid.color = sourceGrid.color;
    targetGrid.notMovedYet = false;
    assert(sourceGrid.color == currColor);

    int dex = move.target_x - move.source_x;
    int dey = move.target_y - move.source_y;
    if (sourceGrid.type == Pawn) {
        int nx = move.target_x, ny = move.source_y;
        if (abs(dex) == 1 && abs(dey) == 1 && oritarColor == EMPTY) {
            assert((boardInfo[nx][ny].type == Pawn) && boardInfo[nx][ny].color == oppColor()
                   && boardInfo[nx][ny].lastIs2Grid);
            boardInfo[nx][ny].color = EMPTY;
            boardInfo[nx][ny].type = None;
            boardInfo[nx][ny].lastIs2Grid = false;
            boardInfo[nx][ny].notMovedYet = false;
        }
        continuePeaceTurn = 0;
    }

    if (sourceGrid.type == King && abs(dex) == 2) {
        assert(abs(dey) == 0);
        int rookX = -1, rookToX = -1;
        if (move.target_x < move.source_x) {
            assert(move.target_x == 2);
            rookX = 0;
            rookToX = 3;
        } else {
            assert(move.target_x == 6);
            rookX = 7;
            rookToX = 5;
        }
        int kingLine = (currColor == BLACK ? 7 : 0);
        assert(boardInfo[rookX][kingLine].color == currColor &&
               boardInfo[rookX][kingLine].type == Rook && boardInfo[rookX][kingLine].notMovedYet);
        auto& rookGrid = boardInfo[rookX][kingLine];
        auto& rookToGrid = boardInfo[rookToX][kingLine];
        rookGrid.color = EMPTY; rookGrid.type = None;
        rookGrid.notMovedYet = false; rookGrid.lastIs2Grid = false;
        rookToGrid.color = currColor; rookToGrid.type = Rook;
        rookToGrid.notMovedYet = false; rookToGrid.lastIs2Grid = false;
    }

    if (sourceGrid.type == Pawn) {
        int ymoveDist = move.target_y - move.source_y;
        if (ymoveDist == 2 || ymoveDist == -2) {
            targetGrid.lastIs2Grid = true;
            markAllPawn(move.target_x, move.target_y);
        } else {
            markAllPawn(-1,-1);
        }
    } else {
        markAllPawn(-1,-1);
    }
    sourceGrid.color = EMPTY;
    sourceGrid.type = None;
    sourceGrid.notMovedYet = false;
    sourceGrid.lastIs2Grid = false;

    if (move.promoptionType != '*') {
        targetGrid.type = charSym[move.promoptionType];
    }

    currColor = oppColor();
    return true;
}

bool Chess::attacked(colorType color, int mx, int my) {
    for (int x = 0; x < BOARDSIZE; x++) {
        for (int y = 0; y < BOARDSIZE; y++) {
            if (boardInfo[x][y].color != color) {
                continue;
            }
            int dex = mx - x, dey = my - y;
            switch (boardInfo[x][y].type) {
                case King: {
                    if (abs(dex) <= 1 && abs(dey) <= 1
                        && !(dex == 0 && dey == 0)) {
                        return true;
                    }
                    break;
                }
                case Queen: {
                    if (inSameLine(x, y, mx, my) && betweenIsEmpty(x, y, mx, my)) {
                        return true;
                    }
                    break;
                }
                case Knight: {
                    if ((abs(dex) == 1 && abs(dey) == 2)
                        || (abs(dex) == 2 && abs(dey) == 1)) {
                        return true;
                    }
                    break;
                }
                case Bishop: {
                    if (inSameObiqueLine(x, y, mx, my) && betweenIsEmpty(x, y, mx, my)) {
                        return true;
                    }
                    break;
                }
                case Rook: {
                    if (inSameStraightLine(x, y, mx, my) && betweenIsEmpty(x, y, mx, my)) {
                        return true;
                    }
                    break;
                }
                case Pawn: {
                    if ((dey == 1  && color == WHITE && abs(dex) == 1)
                        || (dey == -1 && color == BLACK && abs(dex) == 1)) {
                        return true;
                    }
                    break;
                }
                case None: {
                    throw std::runtime_error("color is not empty but type is none");
                    break;
                }
            }
        }
    }
    return false;
}

bool Chess::betweenIsEmpty(int sx, int sy, int ex, int ey) {
    assert(inSameLine(sx, sy, ex, ey));
    int dex = ex > sx ? 1 : (ex == sx ? 0 : -1);
    int dey = ey > sy ? 1 : (ey == sy ? 0 : -1);
    int tx = sx + dex, ty = sy + dey;
    while (inBoard(tx, ty) && !(tx == ex && ty == ey)) {
        if (boardInfo[tx][ty].color != EMPTY)
            return false;
        tx += dex; ty += dey;
    }
    return true;
}

bool Chess::inSameLine(int sx, int sy, int ex, int ey) {
    int dex = ex - sx, dey = ey - sy;
    return dex == dey || dex == -dey || dex == 0 || dey == 0;
}

bool Chess::inSameStraightLine(int sx, int sy, int ex, int ey) {
    int dex = ex - sx, dey = ey - sy;
    return dex == 0 || dey == 0;
}

bool Chess::inSameObiqueLine(int sx, int sy, int ex, int ey) {
    int dex = ex - sx, dey = ey - sy;
    return dex == dey || dex == -dey;
}

Chess& Chess::operator= (const Chess &other) {
    if (this != &other) {
        currColor = other.currColor;
        continuePeaceTurn = other.continuePeaceTurn;
        for (int x = 0; x < BOARDSIZE; x++) {
            for (int y = 0; y < BOARDSIZE; y++) {
                boardInfo[x][y] = other.boardInfo[x][y];
            }
        }
    }
    return *this;
}

Chess::Chess(const Chess &other) {
    currColor = other.currColor;
    continuePeaceTurn = other.continuePeaceTurn;
    for (int x = 0; x < BOARDSIZE; x++) {
        for (int y = 0; y < BOARDSIZE; y++) {
            boardInfo[x][y] = other.boardInfo[x][y];
        }
    }
}

bool Chess::isKingAttackedAfterMove(const Move &move) {
    Chess copyChess(*this);
    copyChess.makeMoveAssumeLegal(move);
    int kingX = -1, kingY = -1;
    for (int x = 0; x < BOARDSIZE; x++) {
        for (int y = 0; y < BOARDSIZE; y++) {
            if (copyChess.boardInfo[x][y].color == currColor
                && copyChess.boardInfo[x][y].type == King) {
                kingX = x; kingY = y;
                break;
            }
        }
    }
    return copyChess.attacked(oppColor(), kingX, kingY);
}

bool Chess::isMoveValid(const Move& move, bool mustDefend) {
    if (!inBoard(move.source_x, move.source_y) || !inBoard(move.target_x, move.target_y)) {
        return false;
    }
    auto& source = boardInfo[move.source_x][move.source_y];
    auto& target = boardInfo[move.target_x][move.target_y];
    if (source.color != currColor || target.color == currColor) {
        return false;
    }
    int dex = move.target_x - move.source_x;
    int dey = move.target_y - move.source_y;
    switch (source.type) {
        case King: {
            if (dex == -2) {
                int kingLine = currColor == BLACK ? 7 : 0;
                if (move.source_x == 4 && move.source_y == kingLine
                    && move.target_x == 2 && move.target_y == kingLine
                    && source.notMovedYet && boardInfo[0][kingLine].color == currColor
                    && boardInfo[0][kingLine].type == Rook && boardInfo[0][kingLine].notMovedYet
                    && boardInfo[1][kingLine].color == EMPTY
                    && boardInfo[2][kingLine].color == EMPTY
                    && boardInfo[3][kingLine].color == EMPTY
                    && !attacked(oppColor(), 2, kingLine)
                    && !attacked(oppColor(), 3, kingLine)
                    && !attacked(oppColor(), 4, kingLine)) {
                    return true;
                }
            } else if (dex == 2) {
                int kingLine = currColor == BLACK ? 7 : 0;
                if (move.source_x == 4 && move.source_y == kingLine
                    && move.target_x == 6 && move.target_y == kingLine
                    && source.notMovedYet && boardInfo[7][kingLine].color == currColor
                    && boardInfo[7][kingLine].type == Rook && boardInfo[7][kingLine].notMovedYet
                    && boardInfo[5][kingLine].color == EMPTY
                    && boardInfo[6][kingLine].color == EMPTY
                    && !attacked(oppColor(), 4, kingLine)
                    && !attacked(oppColor(), 5, kingLine)
                    && !attacked(oppColor(), 6, kingLine)) {
                    return true;
                }

            } else if (abs(dex) <= 1 && abs(dey) <= 1 && !(dex == 0 && dey == 0)) {
                if (!mustDefend || (mustDefend && !isKingAttackedAfterMove(move))) {
                    return true;
                }
            }
            break;
        }
        case Queen: {
            if (inSameLine(move.source_x, move.source_y, move.target_x, move.target_y)
                && betweenIsEmpty(move.source_x, move.source_y, move.target_x, move.target_y)) {
                if (!mustDefend || (mustDefend && !isKingAttackedAfterMove(move))) {
                    return true;
                }
            }
            break;
        }
        case Bishop: {
            if (inSameObiqueLine(move.source_x, move.source_y, move.target_x, move.target_y)
                && betweenIsEmpty(move.source_x, move.source_y, move.target_x, move.target_y)) {
                if (!mustDefend || (mustDefend && !isKingAttackedAfterMove(move))) {
                    return true;
                }
            }
            break;
        }
        case Rook: {
            if (inSameStraightLine(move.source_x, move.source_y, move.target_x, move.target_y)
                && betweenIsEmpty(move.source_x, move.source_y, move.target_x, move.target_y)) {
                if (!mustDefend || (mustDefend && !isKingAttackedAfterMove(move))) {
                    return true;
                }
            }
            break;
        }
        case Knight: {
            if ((abs(dex) == 1 && abs(dey) == 2)
                || (abs(dex) == 2 && abs(dey) == 1)) {
                if (!mustDefend || (mustDefend && !isKingAttackedAfterMove(move))) {
                    return true;
                }
            }
            break;
        }
        case Pawn: {
            if (((source.color == BLACK && dey == -2)
                 || (source.color == WHITE && dey == 2)) && dex == 0) {
                int nx = move.source_x, ny = move.source_y + (source.color == BLACK ? -1 : 1);
                if (source.notMovedYet && boardInfo[nx][ny].color == EMPTY && target.color == EMPTY) {
                    if (!mustDefend || (mustDefend && !isKingAttackedAfterMove(move))) {
                        return true;
                    }
                }
            } else if ((source.color == BLACK && dey == -1)
                       || (source.color == WHITE && dey == 1)) {
                int promtLine = currColor == BLACK ? 0 : 7;
                if (move.promoptionType != '*' && move.target_y != promtLine) {
                    return false;
                }
                if (move.target_y == promtLine && (move.promoptionType != 'q'
                                                   && move.promoptionType != 'b' && move.promoptionType != 'n'
                                                   && move.promoptionType != 'r')) {
                    return false;
                }
                if (abs(dex) == 1) {
                    if (target.color == oppColor()) {
                        if (!mustDefend || (mustDefend && !isKingAttackedAfterMove(move))) {
                            return true;
                        }
                    } else if (target.color == EMPTY) {
                        // ep
                        int nx = move.source_x + dex, ny = move.source_y;
                        if (boardInfo[nx][ny].color == oppColor()
                            && boardInfo[nx][ny].type == Pawn
                            && boardInfo[nx][ny].lastIs2Grid) {
                            if (!mustDefend || (mustDefend && !isKingAttackedAfterMove(move))) {
                                return true;
                            }
                        }
                    }
                } else if (abs(dex) == 0) {
                    if (target.color == EMPTY) {
                        if (!mustDefend || (mustDefend && !isKingAttackedAfterMove(move))) {
                            return true;
                        }
                    }
                }
            }
            break;
        }
        case None: {
            throw std::runtime_error("color is not empty but type is none");
            break;
        }
    }
    return false;
}

void Chess::markAllPawn(int except_x, int except_y) {
    for (int x = 0; x < BOARDSIZE; x++) {
        for (int y = 0; y < BOARDSIZE; y++) {
            if (boardInfo[x][y].color == currColor
                && boardInfo[x][y].type == Pawn
                && !(x == except_x && y == except_y)) {
                boardInfo[x][y].lastIs2Grid = false;
            }
        }
    }
}

bool Chess::winAfterMove(const Move &move) {
    Chess copyChess(*this);
    copyChess.makeMoveAssumeLegal(move);
    vector<Move> oppLegalMoves;
    copyChess.generateMoves(oppLegalMoves);
    return oppLegalMoves.empty();
}

bool Chess::currKingAttacked(const Move &move) {
    int kingX = -1, kingY = -1;
    for (int x = 0; x < BOARDSIZE; x++) {
        for (int y = 0; y < BOARDSIZE; y++) {
            if (boardInfo[x][y].color == currColor && boardInfo[x][y].type == King) {
                kingX = x; kingY = y;
            }
        }
    }
    return attacked(oppColor(), kingX, kingY);
}

bool Chess::isOppKingAttackedAfterMove(const Move &move) {
    Chess copyChess(*this);
    copyChess.makeMoveAssumeLegal(move);
    int kingX = -1, kingY = -1;
    for (int x = 0; x < BOARDSIZE; x++) {
        for (int y = 0; y < BOARDSIZE; y++) {
            if (copyChess.boardInfo[x][y].color == oppColor()
                && copyChess.boardInfo[x][y].type == King) {
                kingX = x; kingY = y;
                break;
            }
        }
    }
    return copyChess.attacked(currColor, kingX, kingY);
}

bool Chess::exceedMaxPeaceState() {
    return continuePeaceTurn >= 50;
}