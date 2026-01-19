from collections import defaultdict
import numpy as np

try:
    from MahjongGB import MahjongFanCalculator
except:
    print(
        "MahjongGB library required! Please visit https://github.com/ailab-pku/PyMahjongGB for more information."
    )
    raise

# Botzone interaction
import numpy as np
import torch
import sys
import requests
import json

## Main llm-related logics are in  dunction obs2response.

TILE_LIST = [
    *("W%d" % (i + 1) for i in range(9)),
    *("T%d" % (i + 1) for i in range(9)),
    *("B%d" % (i + 1) for i in range(9)),
    *("F%d" % (i + 1) for i in range(4)),
    *("J%d" % (i + 1) for i in range(3)),
    "PUBLIC",
    "CONCEALED",
]


class MahjongGBAgent:

    def __init__(self, seatWind):
        pass

    """
    Wind 0..3
    Deal XX XX ...
    Player N Draw
    Player N Gang
    Player N(me) Play XX
    Player N(me) BuGang XX
    Player N(not me) Peng
    Player N(not me) Chi XX
    Player N(me) UnPeng
    Player N(me) UnChi XX
    
    Player N Hu
    Huang
    Player N Invalid
    Draw XX
    Player N(not me) Play XX
    Player N(not me) BuGang XX
    Player N(me) Peng
    Player N(me) Chi XX
    """

    def request2obs(self, request):
        pass

    """
    Hu
    Play XX
    (An)Gang XX
    BuGang XX
    Gang
    Peng
    Chi XX
    Pass
    """

    def action2response(self, action):
        pass


def convert_to_fixed_length_binary(number, length):
    if number > 36:
        return [1] * 6
    binary = bin(number)[2:]
    binary_length = len(binary)

    if binary_length < length:
        binary = "0" * (length - binary_length) + binary
    elif binary_length > length:
        binary = binary[binary_length - length :]
    binary = [int(item) for item in binary]
    return binary


class FeatureAgent2Adapted(MahjongGBAgent):

    # quan1+men1+unseen34+hand14+wall10+(history29+meld4*4)*4
    normal_obs_space = (240,)
    # quan1+men1+unseen34+(history29+meld4*4+hand14+wall10)*4
    oracle_obs_space = (312,)

    # unimplemented
    oracle_feature_space = (0, 4, 9)
    # pass1+hu1+play34+chi63+peng34+gang34+angang34+bugang34
    action_space = (235,)

    # quan1+men1+unseen1+hand1+ meld4*4 +(history29)*4
    normal_feature_space = (136, 4, 9)

    OFFSET_OBS = {
        "PREVALENT_WIND": 0,
        "SEAT_WIND": 1,
        "UNSHOWN": 2,
        "HAND": 36,
        "WALL": 50,
        "PLAYER_START": 60,
        "PLAYER_LEN": 45,
        "MELD_START": 29,
        "MELD_LEN": 4,
    }
    OFFSET_ACT = {
        "Pass": 0,
        "Hu": 1,
        "Play": 2,
        "Chi": 36,
        "Peng": 99,
        "Gang": 133,
        "AnGang": 167,
        "BuGang": 201,
    }
    TILE_LIST = [
        *("W%d" % (i + 1) for i in range(9)),
        *("T%d" % (i + 1) for i in range(9)),
        *("B%d" % (i + 1) for i in range(9)),
        *("F%d" % (i + 1) for i in range(4)),
        *("J%d" % (i + 1) for i in range(3)),
    ]
    OFFSET_TILE = {c: i for i, c in enumerate(TILE_LIST)}
    OFFSET_TILE["PUBLIC"] = 34
    OFFSET_TILE["CONCEALED"] = 35

    def __init__(self, seatWind):
        self.duplicate = True
        self.seatWind = seatWind
        self.packs = [[] for i in range(4)]
        self.history = [[] for i in range(4)]
        self.tileWall = [21] * 4 if self.duplicate else 92
        self.wall = []
        self.shownTiles = defaultdict(int)
        self.knownTiles = defaultdict(int)
        self.flower = 0
        self.wallLast = False
        self.myWallLast = False
        self.isAboutKong = False
        self.obs = np.full(self.normal_obs_space, 255, np.uint8)
        self.obs[self.OFFSET_OBS["SEAT_WIND"]] = self.seatWind

    """
    Wind 0..3
    Deal XX XX ...
    Player N Draw
    Player N Gang
    Player N BuHua
    Player N(me) AnGang XX
    Player N(me) Play XX
    Player N(me) BuGang XX
    Player N(not me) Peng
    Player N(not me) Chi XX
    Player N(not me) AnGang
    
    Player N Hu
    Huang
    Player N Invalid
    Draw XX
    Player N(not me) Play XX
    Player N(not me) BuGang XX
    Player N(me) Peng
    Player N(me) Chi XX
    """

    def request2obs(self, request):
        t = request.split()
        if t[0] == "Wind":
            self.prevalentWind = int(t[1])
            self.obs[self.OFFSET_OBS["PREVALENT_WIND"]] = self.prevalentWind
            return
        if t[0] == "Deal":
            self.hand = t[1:]
            self._hand_embedding_update()
            self._unshown_embedding_update()
            return
        if t[0] == "Wall":
            self.wall = t[1:]
            self._wall_embedding_update()
            return
        if t[0] == "Huang":
            self.valid = []
            self.valid_llm = []
            return self._obs()
        if t[0] == "Draw":
            # Available: Hu, Play, AnGang, BuGang
            if self.duplicate:
                self.tileWall[0] -= 1
                self.wallLast = self.tileWall[1] == 0
                self.myWallLast = self.tileWall[0] == 0
            else:
                self.tileWall -= 1
                self.myWallLast = self.wallLast = self.tileWall == 0
            if self.wall:
                self.wall.pop(0)
                self._wall_embedding_update()
            tile = t[1]
            self.valid = []
            self.valid_llm = []
            if self._check_mahjong(
                tile, isSelfDrawn=True, isAboutKong=self.isAboutKong
            ):
                self.valid.append(self.OFFSET_ACT["Hu"])
                self.valid_llm.append("Hu")
            self.isAboutKong = False
            self.hand.append(tile)
            self._hand_embedding_update()
            for tile in set(self.hand):
                self.valid.append(self.OFFSET_ACT["Play"] + self.OFFSET_TILE[tile])
                self.valid_llm.append("Play " + tile)
                if (
                    self.hand.count(tile) == 4
                    and not self.wallLast
                    and not self.myWallLast
                ):
                    self.valid.append(
                        self.OFFSET_ACT["AnGang"] + self.OFFSET_TILE[tile]
                    )
                    self.valid_llm.append("AnGang " + tile)
            if not self.wallLast and not self.myWallLast:
                for packType, tile, offer in self.packs[0]:
                    if packType == "PENG" and tile in self.hand:
                        self.valid.append(
                            self.OFFSET_ACT["BuGang"] + self.OFFSET_TILE[tile]
                        )
                        self.valid_llm.append("BuGang " + tile)
            return self._obs()
        # Player N Invalid/Hu/Draw/Play/Chi/Peng/Gang/AnGang/BuGang XX
        p = (int(t[1]) + 4 - self.seatWind) % 4
        if t[2] == "BuHua":
            assert not self.duplicate
            if p == 0:
                self.flower += 1
            self.tileWall -= 1
            self.myWallLast = self.wallLast = self.tileWall == 0
            self.isAboutKong = False
        if t[2] == "Draw":
            if self.duplicate:
                self.tileWall[p] -= 1
                self.wallLast = self.tileWall[(p + 1) % 4] == 0
            else:
                self.tileWall -= 1
                self.myWallLast = self.wallLast = self.tileWall == 0
            return
        if t[2] == "Invalid":
            self.valid = []
            self.valid_llm = []
            return self._obs()
        if t[2] == "Hu":
            self.valid = []
            self.valid_llm = []
            return self._obs()
        if t[2] == "Play":
            self.tileFrom = p
            self.curTile = t[3]
            self.shownTiles[self.curTile] += 1
            self._unshown_embedding_update()
            self.history[p].append(
                self.OFFSET_ACT["Play"] + self.OFFSET_TILE[self.curTile]
            )
            self._history_embedding_append(p)
            if p == 0:
                self.hand.remove(self.curTile)
                self._hand_embedding_update()
                return
            else:
                # Available: Hu/Gang/Peng/Chi/Pass
                self.valid = []
                self.valid_llm = []
                if self._check_mahjong(self.curTile):
                    self.valid.append(self.OFFSET_ACT["Hu"])
                    self.valid_llm.append("Hu")
                if not self.wallLast:
                    if self.hand.count(self.curTile) >= 2:
                        self.valid_llm.append("Peng " + self.curTile)
                        self.valid.append(
                            self.OFFSET_ACT["Peng"] + self.OFFSET_TILE[self.curTile]
                        )
                        if self.hand.count(self.curTile) == 3 and not self.myWallLast:
                            self.valid_llm.append("Gang " + self.curTile)
                            self.valid.append(
                                self.OFFSET_ACT["Gang"] + self.OFFSET_TILE[self.curTile]
                            )
                    color = self.curTile[0]
                    if p == 3 and color in "WTB":
                        num = int(self.curTile[1])
                        tmp = []
                        for i in range(-2, 3):
                            tmp.append(color + str(num + i))
                        if tmp[0] in self.hand and tmp[1] in self.hand:
                            self.valid_llm.append("Chi " + color + str(num - 1))
                            self.valid.append(
                                self.OFFSET_ACT["Chi"]
                                + "WTB".index(color) * 21
                                + (num - 3) * 3
                                + 2
                            )
                        if tmp[1] in self.hand and tmp[3] in self.hand:
                            self.valid_llm.append("Chi " + color + str(num))
                            self.valid.append(
                                self.OFFSET_ACT["Chi"]
                                + "WTB".index(color) * 21
                                + (num - 2) * 3
                                + 1
                            )
                        if tmp[3] in self.hand and tmp[4] in self.hand:
                            self.valid_llm.append("Chi " + color + str(num + 1))
                            self.valid.append(
                                self.OFFSET_ACT["Chi"]
                                + "WTB".index(color) * 21
                                + (num - 1) * 3
                            )
                self.valid_llm.append("Pass")
                self.valid.append(self.OFFSET_ACT["Pass"])
                return self._obs()
        if t[2] == "Chi":
            tile = t[3]
            color = tile[0]
            num = int(tile[1])
            self.packs[p].append(("CHI", tile, int(self.curTile[1]) - num + 2))
            self._pack_embedding_append(p)
            self.shownTiles[self.curTile] -= 1
            for i in range(-1, 2):
                self.shownTiles[color + str(num + i)] += 1
            self._unshown_embedding_update()
            self.history[p].append(
                self.OFFSET_ACT["Chi"]
                + "WTB".index(color) * 7 * 3
                + (num - 2) * 3
                + int(self.curTile[1])
                - num
                + 1
            )
            self._history_embedding_append(p)
            if self.duplicate:
                self.wallLast = self.tileWall[(p + 1) % 4] == 0
            if p == 0:
                # Available: Play
                self.valid = []
                self.valid_llm = []
                self.hand.append(self.curTile)
                for i in range(-1, 2):
                    self.hand.remove(color + str(num + i))
                self._hand_embedding_update()
                for tile in set(self.hand):
                    self.valid_llm.append("Play " + tile)
                    self.valid.append(self.OFFSET_ACT["Play"] + self.OFFSET_TILE[tile])
                return self._obs()
            else:
                return
        if t[2] == "UnChi":
            tile = t[3]
            color = tile[0]
            num = int(tile[1])
            self.packs[p].pop()
            self._pack_embedding_pop(p)
            self.shownTiles[self.curTile] += 1
            for i in range(-1, 2):
                self.shownTiles[color + str(num + i)] -= 1
            self._unshown_embedding_update()
            self.history[p].pop()
            self._history_embedding_pop(p)
            if p == 0:
                for i in range(-1, 2):
                    self.hand.append(color + str(num + i))
                self.hand.remove(self.curTile)
                self._hand_embedding_update()
            return
        if t[2] == "Peng":
            self.packs[p].append(("PENG", self.curTile, (4 + p - self.tileFrom) % 4))
            self._pack_embedding_append(p)
            self.shownTiles[self.curTile] += 2
            self._unshown_embedding_update()
            self.history[p].append(
                self.OFFSET_ACT["Peng"] + self.OFFSET_TILE[self.curTile]
            )
            self._history_embedding_append(p)
            if self.duplicate:
                self.wallLast = self.tileWall[(p + 1) % 4] == 0
            if p == 0:
                # Available: Play
                self.valid = []
                self.valid_llm = []
                for i in range(2):
                    self.hand.remove(self.curTile)
                self._hand_embedding_update()
                for tile in set(self.hand):
                    self.valid_llm.append("Play " + tile)
                    self.valid.append(self.OFFSET_ACT["Play"] + self.OFFSET_TILE[tile])
                return self._obs()
            else:
                return
        if t[2] == "UnPeng":
            self._pack_embedding_pop(p)
            self.packs[p].pop()
            self.shownTiles[self.curTile] -= 2
            self._unshown_embedding_update()
            self.history[p].pop()
            self._history_embedding_pop(p)
            if p == 0:
                for i in range(2):
                    self.hand.append(self.curTile)
                self._hand_embedding_update()
            return
        if t[2] == "Gang":
            self.packs[p].append(("GANG", self.curTile, (4 + p - self.tileFrom) % 4))
            self._pack_embedding_append(p)
            self.shownTiles[self.curTile] += 3
            self._unshown_embedding_update()
            self.history[p].append(
                self.OFFSET_ACT["Gang"] + self.OFFSET_TILE[self.curTile]
            )
            self._history_embedding_append(p)
            if p == 0:
                for i in range(3):
                    self.hand.remove(self.curTile)
                self._hand_embedding_update()
                self.isAboutKong = True
            return
        if t[2] == "AnGang":
            tile = "CONCEALED" if p else t[3]
            self.packs[p].append(("GANG", tile, 0))
            self._pack_embedding_append(p)
            self.history[p].append(self.OFFSET_ACT["AnGang"] + self.OFFSET_TILE[tile])
            self._history_embedding_append(p)
            if p == 0:
                self.isAboutKong = True
                for i in range(4):
                    self.hand.remove(tile)
            else:
                self.isAboutKong = False
            return
        if t[2] == "BuGang":
            tile = t[3]
            for i in range(len(self.packs[p])):
                if tile == self.packs[p][i][1]:
                    self.packs[p][i] = ("GANG", tile, self.packs[p][i][2])
                    offset = (
                        self.OFFSET_OBS["PLAYER_START"]
                        + self.OFFSET_OBS["PLAYER_LEN"] * p
                        + self.OFFSET_OBS["MELD_START"]
                        + self.OFFSET_OBS["MELD_LEN"] * i
                    )
                    self.obs[offset + 3] = self.OFFSET_TILE[tile]
                    break
            self.shownTiles[tile] += 1
            self._unshown_embedding_update()
            self.history[p].append(self.OFFSET_ACT["BuGang"] + self.OFFSET_TILE[tile])
            self._history_embedding_append(p)
            if p == 0:
                self.hand.remove(tile)
                self._hand_embedding_update()
                self.isAboutKong = True
                return
            else:
                # Available: Hu/Pass
                self.valid = []
                self.valid_llm = []
                if self._check_mahjong(tile, isSelfDrawn=False, isAboutKong=True):
                    self.valid_llm.append("Hu")
                    self.valid.append(self.OFFSET_ACT["Hu"])
                self.valid_llm.append("Pass")
                self.valid.append(self.OFFSET_ACT["Pass"])
                return self._obs()
        raise NotImplementedError("Unknown request %s!" % request)

    """
    Pass
    Hu
    Play XX
    Chi XX
    Peng
    Gang
    (An)Gang XX
    BuGang XX
    """

    def action2response(self, action):
        if action < self.OFFSET_ACT["Hu"]:
            return "Pass"
        if action < self.OFFSET_ACT["Play"]:
            return "Hu"
        if action < self.OFFSET_ACT["Chi"]:
            return "Play " + self.TILE_LIST[action - self.OFFSET_ACT["Play"]]
        if action < self.OFFSET_ACT["Peng"]:
            t = (action - self.OFFSET_ACT["Chi"]) // 3
            return "Chi " + "WTB"[t // 7] + str(t % 7 + 2)
        if action < self.OFFSET_ACT["Gang"]:
            return "Peng"
        if action < self.OFFSET_ACT["AnGang"]:
            return "Gang"
        if action < self.OFFSET_ACT["BuGang"]:
            return "Gang " + self.TILE_LIST[action - self.OFFSET_ACT["AnGang"]]
        return "BuGang " + self.TILE_LIST[action - self.OFFSET_ACT["BuGang"]]

    @staticmethod
    def action2response_static(action, prev_tile):
        if action < FeatureAgent2Adapted.OFFSET_ACT["Hu"]:
            return "Pass"
        if action < FeatureAgent2Adapted.OFFSET_ACT["Play"]:
            return "Hu"
        if action < FeatureAgent2Adapted.OFFSET_ACT["Chi"]:
            return (
                "Play "
                + FeatureAgent2Adapted.TILE_LIST[
                    action - FeatureAgent2Adapted.OFFSET_ACT["Play"]
                ]
            )
        if action < FeatureAgent2Adapted.OFFSET_ACT["Peng"]:
            t = (action - FeatureAgent2Adapted.OFFSET_ACT["Chi"]) // 3
            return "Chi " + prev_tile + " " + "WTB"[t // 7] + str(t % 7 + 2)
        if action < FeatureAgent2Adapted.OFFSET_ACT["Gang"]:
            return (
                "Peng "
                + FeatureAgent2Adapted.TILE_LIST[
                    action - FeatureAgent2Adapted.OFFSET_ACT["Peng"]
                ]
            )
        if action < FeatureAgent2Adapted.OFFSET_ACT["AnGang"]:
            return (
                "Gang "
                + FeatureAgent2Adapted.TILE_LIST[
                    action - FeatureAgent2Adapted.OFFSET_ACT["Gang"]
                ]
            )
        if action < FeatureAgent2Adapted.OFFSET_ACT["BuGang"]:
            return (
                "AnGang "
                + FeatureAgent2Adapted.TILE_LIST[
                    action - FeatureAgent2Adapted.OFFSET_ACT["AnGang"]
                ]
            )
        return (
            "BuGang "
            + FeatureAgent2Adapted.TILE_LIST[
                action - FeatureAgent2Adapted.OFFSET_ACT["BuGang"]
            ]
        )

    """
    Pass
    Hu
    Play XX
    Chi XX XX
    Peng XX
    Gang XX
    (An)Gang XX
    BuGang XX
    """

    def response2action(self, response):
        t = response.split()
        if t[0] == "Pass":
            return self.OFFSET_ACT["Pass"]
        if t[0] == "Hu":
            return self.OFFSET_ACT["Hu"]
        if t[0] == "Play":
            return self.OFFSET_ACT["Play"] + self.OFFSET_TILE[t[1]]
        if t[0] == "Chi":
            return (
                self.OFFSET_ACT["Chi"]
                + "WTB".index(t[1][0]) * 7 * 3
                + (int(t[2][1]) - 2) * 3
                + int(t[1][1])
                - int(t[2][1])
                + 1
            )
        if t[0] == "Peng":
            return self.OFFSET_ACT["Peng"] + self.OFFSET_TILE[t[1]]
        if t[0] == "Gang":
            return self.OFFSET_ACT["Gang"] + self.OFFSET_TILE[t[1]]
        if t[0] == "BuGang":
            return self.OFFSET_ACT["BuGang"] + self.OFFSET_TILE[t[1]]
        if t[0] == "AnGang":
            return self.OFFSET_ACT["AnGang"] + self.OFFSET_TILE[t[1]]
        return self.OFFSET_ACT["Pass"]

    def _hand_embedding_update(self):
        self.obs[self.OFFSET_OBS["HAND"] : self.OFFSET_OBS["WALL"]] = 255
        # print(len(self.hand), self.hand)
        for i, tile in enumerate(self.hand):
            self.obs[self.OFFSET_OBS["HAND"] + i] = self.OFFSET_TILE[tile]

    def _wall_embedding_update(self):
        self.obs[self.OFFSET_OBS["WALL"] : self.OFFSET_OBS["PLAYER_START"]] = 255
        for i, tile in enumerate(
            self.wall[: self.OFFSET_OBS["PLAYER_START"] - self.OFFSET_OBS["WALL"]]
        ):
            self.obs[self.OFFSET_OBS["WALL"] + i] = self.OFFSET_TILE[tile]

    def _pack_embedding_append(self, p):
        l = len(self.packs[p]) - 1
        packType, tile, offer = self.packs[p][-1]
        offset = (
            self.OFFSET_OBS["PLAYER_START"]
            + self.OFFSET_OBS["PLAYER_LEN"] * p
            + self.OFFSET_OBS["MELD_START"]
            + self.OFFSET_OBS["MELD_LEN"] * l
        )
        if packType == "CHI":
            for i in range(-1, 2):
                self.obs[offset + i + 1] = self.OFFSET_TILE[tile] + i
        elif packType == "PENG":
            self.obs[offset : offset + 3] = self.OFFSET_TILE[tile]
        else:
            self.obs[offset : offset + 4] = self.OFFSET_TILE[tile]

    def _pack_embedding_pop(self, p):
        l = len(self.packs[p])
        offset = (
            self.OFFSET_OBS["PLAYER_START"]
            + self.OFFSET_OBS["PLAYER_LEN"] * p
            + self.OFFSET_OBS["MELD_START"]
            + self.OFFSET_OBS["MELD_LEN"] * l
        )
        self.obs[offset : offset + 4] = 255

    def _history_embedding_append(self, p):
        assert len(self.history[p]) <= 29
        l = len(self.history[p]) - 1
        action = self.history[p][-1]
        offset = self.OFFSET_OBS["PLAYER_START"] + self.OFFSET_OBS["PLAYER_LEN"] * p + l
        self.obs[offset] = action

    def _history_embedding_pop(self, p):
        l = len(self.history[p])
        offset = self.OFFSET_OBS["PLAYER_START"] + self.OFFSET_OBS["PLAYER_LEN"] * p + l
        self.obs[offset] = 255

    def _unshown_embedding_update(self):
        for i, tile in enumerate(self.TILE_LIST):
            self.obs[self.OFFSET_OBS["UNSHOWN"] + i] = 4 - self.shownTiles[tile]

    def _check_mahjong(self, winTile, isSelfDrawn=False, isAboutKong=False):
        try:
            fans = MahjongFanCalculator(
                pack=tuple(self.packs[0]),
                hand=tuple(self.hand),
                winTile=winTile,
                flowerCount=self.flower,
                isSelfDrawn=isSelfDrawn,
                is4thTile=(self.shownTiles[winTile] + isSelfDrawn) == 4,
                isAboutKong=isAboutKong,
                isWallLast=self.wallLast,
                seatWind=self.seatWind,
                prevalentWind=self.prevalentWind,
                verbose=True,
            )
            fanCnt = 0
            for fanPoint, cnt, fanName, fanNameEn in fans:
                fanCnt += fanPoint * cnt
            if fanCnt < 8:
                raise Exception("Not Enough Fans")
        except:
            return False
        return True

    # valid actions
    def action_mask_llm(self):
        if "Hu" in self.valid_llm:
            return ["Hu"]
        return self.valid_llm

    # valid actions
    def action_mask(self):
        mask = np.zeros(self.action_space, np.uint8)
        if 1 in self.valid:
            mask[1] = 1
            return mask
        for a in self.valid:
            mask[a] = 1
        return mask

    def _obs(self):
        return {
            "observation_llm": self.obs_normal_llm(),
            "observation": self.obs_normal(),
            "action_mask_llm": self.action_mask_llm(),
            "action_mask": self.action_mask(),
        }

    # normal_observation
    def obs_normal(self):
        return self.feature_normal_from_normal(self.obs.copy())

    # normal_observation
    def obs_normal_llm(self):
        return self.feature_normal_from_normal_llm(self.obs.copy())

    # oracle_observation
    def obs_oracle(self, obs_list):
        obs = np.zeros(self.oracle_obs_space, np.uint8)
        obs[:36] = obs_list[self.seatWind][:36]
        for i in range(4):
            obs[36 + i * 69 : 81 + i * 69] = obs_list[(i + self.seatWind) % 4][60:105]
            obs[81 + i * 69 : 105 + i * 69] = obs_list[(i + self.seatWind) % 4][36:60]
        return obs

    @staticmethod
    def feature_normal_from_normal_llm(normal_obs):
        # quan1+men1+unseen1+hand1+ meld4*4 +(history29)*4
        feature = np.zeros((FeatureAgent2Adapted.normal_feature_space[0], 36), np.uint8)
        # 8-bit coding for action, 29 actions, 4 players
        # 2-bit action: 00：play, 01: chi, 02: peng, 03: gang
        dense_feature = np.zeros((8 * 29 * 4), np.uint8)
        wind_order = ["东风", "南风", "西风", "北风"]
        game_wind_prompt = f"圈风为：{wind_order[normal_obs[0]]}。"

        seat_wind = f"门风为：{wind_order[normal_obs[1]]}。\n"
        # print(game_wind_prompt, seat_wind)
        # feature[0, normal_obs[0]] = 1
        # feature[1, normal_obs[1]] = 1

        unshown_tile_list = []
        for j in range(34):
            feature[2, j] = normal_obs[j + 2]
            unshown_tile_list.append(TILE_LIST[j] + ": " + str(normal_obs[j + 2]))
        unshown_tile_prompt = f"未出现的牌有：[{'; '.join(unshown_tile_list)}]。\n"
        tile_list = []
        for j in range(14):
            tile = normal_obs[36 + j]
            if tile != 255:
                tile_list.append(TILE_LIST[tile])
                feature[3, tile] += 1

        hand_tile_list = []
        for i in range(36):
            if feature[3, i] != 0:
                hand_tile_list.append(TILE_LIST[i] + ": " + str(feature[3, i]))
        hand_tile_prompt = f"你的手牌现在有：[{'; '.join(hand_tile_list)}]。\n"
        pack_prompt_names = [
            "你的副露有：{}。\n",
            "你下家的副露有：{}。\n",
            "你对家的副露有：{}。\n",
            "你上家的副露有：{}。\n",
        ]
        pack_prompt = ""
        # print(tile_list)
        for i in range(4):
            pack_list = []
            for j in range(4):
                offset = 89 + i * 45 + j * 4
                pack_element_list = []
                for k in range(4):
                    tile = normal_obs[offset + k]
                    if tile != 255:
                        feature[4 + i * 4 + j, tile] += 1
                        pack_element_list.append(TILE_LIST[tile])
                if len(pack_element_list) > 0:
                    pack_list.append(", ".join(pack_element_list))
            pack_info = f'[[{"],[".join(pack_list)}]]'
            pack_prompt += pack_prompt_names[i].format(pack_info)
        history_prompt_names = [
            "你的出牌历史为：{}。\n",
            "你下家的出牌历史为：{}。\n",
            "你对家的出牌历史为：{}。\n",
            "你上家的出牌历史为：{}。\n",
        ]
        history_prompt = ""
        for i in range(4):
            history_list = []
            for j in range(29):
                action = normal_obs[60 + i * 45 + j]
                if action < FeatureAgent2Adapted.OFFSET_ACT["Chi"]:
                    tile = action - FeatureAgent2Adapted.OFFSET_ACT["Play"]
                    feature[20 + i * 29 + j, tile] = 1
                    dense_feature[i * 8 * 29 + j : i * 8 * 29 + j + 2] = [0, 0]
                    dense_feature[i * 8 * 29 + j + 2 : i * 8 * 29 + j + 8] = (
                        convert_to_fixed_length_binary(tile, 6)
                    )
                    history_list.append("Play " + TILE_LIST[tile])
                elif action < FeatureAgent2Adapted.OFFSET_ACT["Peng"]:
                    t = (action - FeatureAgent2Adapted.OFFSET_ACT["Chi"]) // 3
                    color = "WTB"[t // 7]
                    num = t % 7 + 2
                    tile = "%s%d" % (color, num)
                    for k in range(-1, 2):
                        feature[
                            20 + i * 29 + j, FeatureAgent2Adapted.OFFSET_TILE[tile] + k
                        ] = 1
                    dense_feature[i * 8 * 29 + j : i * 8 * 29 + j + 2] = [0, 1]
                    dense_feature[i * 8 * 29 + j + 2 : i * 8 * 29 + j + 8] = (
                        convert_to_fixed_length_binary(
                            FeatureAgent2Adapted.OFFSET_TILE[tile], 6
                        )
                    )
                    history_list.append("Chi " + tile)

                elif action < FeatureAgent2Adapted.OFFSET_ACT["Gang"]:
                    tile = action - FeatureAgent2Adapted.OFFSET_ACT["Peng"]
                    feature[20 + i * 29 + j, tile] = 3
                    dense_feature[i * 8 * 29 + j : i * 8 * 29 + j + 2] = [1, 0]
                    dense_feature[i * 8 * 29 + j + 2 : i * 8 * 29 + j + 8] = (
                        convert_to_fixed_length_binary(tile, 6)
                    )
                    history_list.append("Peng " + TILE_LIST[tile])
                elif action < FeatureAgent2Adapted.OFFSET_ACT["AnGang"]:
                    tile = action - FeatureAgent2Adapted.OFFSET_ACT["Gang"]
                    feature[20 + i * 29 + j, tile] = 4
                    dense_feature[i * 8 * 29 + j : i * 8 * 29 + j + 2] = [1, 1]
                    dense_feature[i * 8 * 29 + j + 2 : i * 8 * 29 + j + 8] = (
                        convert_to_fixed_length_binary(tile, 6)
                    )
                    history_list.append("Gang " + TILE_LIST[tile])
                elif action < FeatureAgent2Adapted.OFFSET_ACT["BuGang"]:
                    tile = action - FeatureAgent2Adapted.OFFSET_ACT["AnGang"]
                    feature[20 + i * 29 + j, tile] = 4
                    dense_feature[i * 8 * 29 + j : i * 8 * 29 + j + 2] = [1, 1]
                    dense_feature[i * 8 * 29 + j + 2 : i * 8 * 29 + j + 8] = (
                        convert_to_fixed_length_binary(tile, 6)
                    )
                    history_list.append("AnGang " + TILE_LIST[tile])
                elif action != 255:
                    tile = action - FeatureAgent2Adapted.OFFSET_ACT["BuGang"]
                    feature[20 + i * 29 + j, tile] = 4
                    dense_feature[i * 8 * 29 + j : i * 8 * 29 + j + 2] = [1, 1]
                    dense_feature[i * 8 * 29 + j + 2 : i * 8 * 29 + j + 8] = (
                        convert_to_fixed_length_binary(tile, 6)
                    )
                    history_list.append("BuGang " + TILE_LIST[tile])
            history_prompt += history_prompt_names[i].format(", ".join(history_list))
        feature = feature.reshape(np.prod(FeatureAgent2Adapted.normal_feature_space))
        return (
            game_wind_prompt
            + seat_wind
            + unshown_tile_prompt
            + hand_tile_prompt
            + pack_prompt
            + history_prompt
        )

    @staticmethod
    def feature_normal_from_normal(normal_obs):
        feature = np.zeros((FeatureAgent2Adapted.normal_feature_space[0], 36), np.uint8)
        # 8-bit coding for action, 29 actions, 4 players
        # 2-bit action: 00：play, 01: chi, 02: peng, 03: gang
        dense_feature = np.zeros((8 * 29 * 4), np.uint8)
        feature[0, normal_obs[0]] = 1
        feature[1, normal_obs[1]] = 1
        for j in range(34):
            feature[2, j] = normal_obs[j + 2]
        tile_list = []
        for j in range(14):
            tile = normal_obs[36 + j]
            if tile != 255:
                tile_list.append(TILE_LIST[tile])
                feature[3, tile] += 1
        # print(tile_list)
        for i in range(4):
            for j in range(4):
                offset = 89 + i * 45 + j * 4
                for k in range(4):
                    tile = normal_obs[offset + k]
                    if tile != 255:
                        feature[4 + i * 4 + j, tile] += 1
        for i in range(4):
            for j in range(29):
                action = normal_obs[60 + i * 45 + j]
                if action < FeatureAgent2Adapted.OFFSET_ACT["Chi"]:
                    tile = action - FeatureAgent2Adapted.OFFSET_ACT["Play"]
                    feature[20 + i * 29 + j, tile] = 1
                    dense_feature[i * 8 * 29 + j : i * 8 * 29 + j + 2] = [0, 0]
                    dense_feature[i * 8 * 29 + j + 2 : i * 8 * 29 + j + 8] = (
                        convert_to_fixed_length_binary(tile, 6)
                    )
                elif action < FeatureAgent2Adapted.OFFSET_ACT["Peng"]:
                    t = (action - FeatureAgent2Adapted.OFFSET_ACT["Chi"]) // 3
                    color = "WTB"[t // 7]
                    num = t % 7 + 2
                    tile = "%s%d" % (color, num)
                    for k in range(-1, 2):
                        feature[
                            20 + i * 29 + j, FeatureAgent2Adapted.OFFSET_TILE[tile] + k
                        ] = 1
                    dense_feature[i * 8 * 29 + j : i * 8 * 29 + j + 2] = [0, 1]
                    dense_feature[i * 8 * 29 + j + 2 : i * 8 * 29 + j + 8] = (
                        convert_to_fixed_length_binary(
                            FeatureAgent2Adapted.OFFSET_TILE[tile], 6
                        )
                    )

                elif action < FeatureAgent2Adapted.OFFSET_ACT["Gang"]:
                    tile = action - FeatureAgent2Adapted.OFFSET_ACT["Peng"]
                    feature[20 + i * 29 + j, tile] = 3
                    dense_feature[i * 8 * 29 + j : i * 8 * 29 + j + 2] = [1, 0]
                    dense_feature[i * 8 * 29 + j + 2 : i * 8 * 29 + j + 8] = (
                        convert_to_fixed_length_binary(tile, 6)
                    )
                elif action < FeatureAgent2Adapted.OFFSET_ACT["AnGang"]:
                    tile = action - FeatureAgent2Adapted.OFFSET_ACT["Gang"]
                    feature[20 + i * 29 + j, tile] = 4
                    dense_feature[i * 8 * 29 + j : i * 8 * 29 + j + 2] = [1, 1]
                    dense_feature[i * 8 * 29 + j + 2 : i * 8 * 29 + j + 8] = (
                        convert_to_fixed_length_binary(tile, 6)
                    )
                elif action < FeatureAgent2Adapted.OFFSET_ACT["BuGang"]:
                    tile = action - FeatureAgent2Adapted.OFFSET_ACT["AnGang"]
                    feature[20 + i * 29 + j, tile] = 4
                    dense_feature[i * 8 * 29 + j : i * 8 * 29 + j + 2] = [1, 1]
                    dense_feature[i * 8 * 29 + j + 2 : i * 8 * 29 + j + 8] = (
                        convert_to_fixed_length_binary(tile, 6)
                    )
                elif action != 255:
                    tile = action - FeatureAgent2Adapted.OFFSET_ACT["BuGang"]
                    feature[20 + i * 29 + j, tile] = 4
                    dense_feature[i * 8 * 29 + j : i * 8 * 29 + j + 2] = [1, 1]
                    dense_feature[i * 8 * 29 + j + 2 : i * 8 * 29 + j + 8] = (
                        convert_to_fixed_length_binary(tile, 6)
                    )
        feature = feature.reshape(np.prod(FeatureAgent2Adapted.normal_feature_space))
        return np.concatenate((feature, dense_feature))


def extract_move(text, valid_action_list):
    answer_keywords = [
        "答案：",
        "答案:",
        "answer：",
        "answer:",
        "Answer：",
        "Answer:",
    ]
    start_idx = -1
    keyword_used = ""

    for keyword in answer_keywords:
        idx = text.find(keyword)
        if idx != -1:
            start_idx = idx
            keyword_used = keyword
            break
    answer_start = start_idx + len(keyword_used)
    answer_text = text[answer_start:].strip()

    # 3. 可能有多行答案，取第一行并去除多余空格和标点
    first_line = answer_text.split("\n")[0].strip()

    # 4. 清理可能的标点符号（如句号、冒号等）
    clean_action = first_line
    # 去除末尾的标点
    if (
        clean_action.endswith(".")
        or clean_action.endswith("。")
        or clean_action.endswith(";")
    ):
        clean_action = clean_action[:-1].strip()

    # 5. 检查是否在合法动作列表中
    if clean_action in valid_action_list:
        if "Peng" in clean_action:
            return 1, "Peng"
        if "AnGang" in clean_action:
            return 1, clean_action[2:]
        elif "BuGang" in clean_action:
            return 1, clean_action
        elif "Gang" in clean_action:
            return 1, "Gang"
        return 1, clean_action

    for action in valid_action_list:
        if clean_action in action or action in clean_action:
            if "Peng" in clean_action:
                return 1, "Peng"
            if "AnGang" in clean_action:
                return 1, clean_action[2:]
            elif "BuGang" in clean_action:
                return 1, clean_action
            elif "Gang" in clean_action:
                return 1, "Gang"
            return 1, action
    return 0, clean_action


def obs2response(model, obs):
    rule_prompt = """
    你是一名国标麻将玩家，这是一种四人游戏，使用136张牌：(1-9)万，(1-9)饼，(1-9)条，(东南西北)风，(中发白)箭，每种牌有4张，构成和牌牌型。
    除特殊牌型外，和牌牌型的基本结构为：4组面子（顺子/刻子/杠子） + 1对将牌。此外，国标麻将要求牌型达到至少8番才能和牌。
    顺子：类似一二三万，六七八条等；刻子：3个相同的牌；杠子：4个相同的牌。
    番种价值与介绍：
        - 1番：
            - 一般高：由一种花色2副相同的顺子组成的牌
            - 喜相逢：2种花色2副序数相同的顺子
            - 连六：一种花色6张相连接的序数牌
            - 老少副：一种花色牌的123、789两副顺子
            - 幺九刻：3张相同的一、九序数牌及字牌组成的刻子(或杠)
            - 明杠：自己有暗刻，碰别人打出的一张相同的牌开杠：或自己抓进一张与碰的明刻相同的牌开杠
            - 缺一门：和牌中缺少一种花色序数牌
            - 无字：和牌中没有风、箭牌
            - 边张：单和123的3及789的7或1233和3、7789和7都为张。手中有12345和3，56789和7不算边张
            - 坎张：和2张牌之间的牌。4556和5也为坎张，手中有45567和6不算坎张
            - 单钓将：钓单张牌作将成和
            - 自摸：自己抓进牌成和牌
        - 2番：
            - 断幺：和牌中没有一、九及字牌
            - 暗杠：自抓4张相同的牌开杠
            - 双暗刻：2个暗刻
            - 双同刻：2副序数相同的刻子
            - 四归一：和牌中，有4张相同的牌归于一家的顺、刻子、对、将牌中(不包括杠牌)
            - 平和：由4副顺子及序数牌作将组成的和牌，边、坎、钓不影响平和，不计无字
            - 门前清：没有吃、碰、明杠，和别人打出的牌
            - 门风刻：与本门风相同的风刻
            - 圈风刻：与圈风相同的风刻
            - 箭刻：由中、发、白3张相同的牌组成的刻子（或杠子）
        - 4番：
            - 全带幺：和牌时，每副牌、将牌都有幺牌（序数牌的1/9，以及风牌和箭牌）
            - 不求人：4副牌及将中没有吃牌、碰牌(包括明杠)，自摸和牌
            - 双明杠：2个明杠。不计明杠
            - 和绝张：和牌池、桌面已亮明的3张牌所剩的第4张牌(抢杠和不计和绝张)
        - 5番：
            - 明暗杠：1个明杠，1个暗杠。不计明杠、暗杠
        - 6番：
            - 双箭刻：2副箭刻(或杠)。不计箭刻
            - 双暗杠：2个暗杠。不计暗杠
            - 全求人：全靠吃牌、碰牌、单钓别人打出的牌和牌。不计单钓
            - 五门齐：和牌时3种序数牌、风、箭牌齐全
            - 三色三步高：3种花色3副依次递增一位序数的顺子
            - 混一色：由一种花色序数牌及字牌组成的和牌
            - 碰碰和：由4副刻子(或杠)、将牌组成的和牌
        - 8番：
            - 抢杠和：和别人自抓开明杠的牌。不计和绝张
            - 杠上开花：开杠抓进的牌成和牌(不包括补花)不计自摸
            - 海底捞月：和打出的最后一张牌
            - 妙手回春：自摸牌墙上最后一张牌和牌。不计自摸
            - 无番和：和牌后，数不出任何番种分(花牌不计算在内)（不可有相同的顺子和刻子、不可杠牌、不可自摸、不可绝张）
            - 三色三节高：和牌时，有3种花色3副依次递增一位数的刻子
            - 三色三同顺：和牌时，有3种花色3副序数相同的顺子
            - 推不倒：由牌面图形没有上下区别的牌组成的和牌，包括1234589饼、245689条、白板。不计缺一门
            - 花龙：3种花色的3副顺子连接成1-9的序数牌， 形如147条，258万，369饼这样，其中饼万条可以任意互换
        - 12番：
            - 三风刻：3个风刻
            - 小于五：由序数牌1-4的顺子、刻子、将牌组成的和牌。不计无字
            - 大于五：由序数牌6-9的顺子、刻子、将牌组成的和牌。不计无字
            - 组合龙：3种花色的147、258、369不能错位的序数牌，形如123条，456万，789饼这样，其中饼万条可以任意互换
            - 全不靠：由单张3种花色147、258、369不能错位的序数牌及东南西北中发白中的任何14张牌组成的和牌
        - 16番：
            - 三暗刻：3个暗刻（暗杠），不计双暗刻
            - 三同刻：3个序数相同的刻子(杠)，不计双同刻
            - 全带五：每副牌及将牌必须有5的序数牌。不计断幺
            - 一色三步高：和牌时，有一种花色3副依次递增一位或依次递增二位数字的顺子
            - 三色双龙会：2种花色2个老少副、另一种花色5作将的和牌。
            - 清龙：和牌时，有一种花色1-9相连接的序数牌
        - 24番：
            - 全小：由序数牌123组成的顺子、刻子(杠)、将牌的和牌。
            - 全中：由序数牌456组成的顺子、刻子(杠)、将牌的和牌
            - 全大：由序数牌789组成的顺子、刻子(杠)、将牌的和牌
            - 一色三节高：和牌时有一种花色3副依次递增一位数字的刻子
            - 一色三同顺：和牌时有一种花色3副序数相同的顺子
            - 清一色：由一种花色的序数牌组成和各牌
            - 全双刻：由2、4、6、8序数牌的刻子、将牌组成的和牌
            - 七星不靠：必须有7个单张的东西南北中发白，加上3种花色，数位按147、258、369中的7张序数牌组成没有将牌的和牌
            - 七对：由7个对子组成和牌
        - 32番：
            - 混幺九：由字牌和序数牌一、九的刻子用将牌组成的和牌
            - 三杠：3个杠
            - 一色四步高：一种花色4副依次递增一位数或依次递增二位数的顺子
        - 48番：
            - 一色四节高：一种花色4副依次递增一位数的刻子
            - 一色四同顺：一种花色4副序数相同的顺子
        - 64番
            - 清幺九：由序数牌一、九刻子组成的和牌
            - 小四喜：和牌时有风牌的3副刻子及将牌
            - 小三元：和牌时有箭牌的两副刻子及将牌
            - 字一色：由字牌的刻子(杠)、将组成的和牌
            - 四暗刻：4个暗刻(暗杠)
            - 一色双龙会：一种花色的两个老少副，5为将牌
        - 88番
            - 大四喜：和牌型中，由东南西北4副刻（杠）子
            - 大三元：和牌型中，有中发白3副刻（杠）子
            - 绿一色：由23468条及发中的任何牌组成顺子、刻子、将的和牌
            - 九莲宝灯：由一种花色序数牌子按1112345678999组成的听牌型，见同花色任何1张序数牌即成和牌
            - 四杠：和牌型中，有四个杠子
            - 连七对：由同一种花色的序数牌组成序数相连的7个对子的特殊和牌型
            - 十三幺：含有3种序数牌的一、九牌，7种字牌且其中一种成对组成的特殊和牌型
    牌的表示：序数牌（饼万条）表示为：B/W/T+数字，如一饼为B1, 四万为W4, 九条为T9。
    风牌由F表示，F1-F4分别表示东西南北，箭牌由J表示，J1-J3分别表示中发白。
    合法动作与出牌历史中的'Chi Tile'，意味着某位玩家用手牌中的两张牌，与之前打出的牌组成一个顺子[Tile-1, Tile, Tile+1]。
    比如'Chi W2'，可能是他的上家打出了W1/W2/W3, 然后这位玩家用手牌中的另外两张牌，组成[W1, W2, W3]这个顺子。
    现在是你的回合，请从你合法的动作中选一个进行操作，一般的思路是先找到几个距离比较近的番种，然后优先打出对这些番种没用的牌，进而提升胜率。
    你的回复格式应该是：
    分析：[你的分析]
    理由：[你的理由]
    答案：[动作]
    """

    llm_valid_move_list = obs["action_mask_llm"]
    if len(llm_valid_move_list) == 1:
        # pass
        return llm_valid_move_list[0]
    else:
        llm_state_info = obs["observation_llm"]
        user_prompt = "以下是现在的局面信息: " + llm_state_info
        valid_move_prompt = (
            f"以下是你现有的合法动作：[{'; '.join(llm_valid_move_list)}]。"
        )
        # for move in llm_valid_move_list:
        #     if "Chi" in move or "Peng" in move:

        # print(user_prompt.replace("\n", ""))
        # print(valid_move_prompt)

        # LLM API related
        url = "https://api.siliconflow.cn/v1/chat/completions"
        headers = {
            "Authorization": "Bearer sk-wegasvkuoirqeeghwmnrmpzgxnstzpsqldjnzlgstgsekjjs",
            "Content-Type": "application/json",
        }
        # Fault Tolerance
        trial_count = 0
        previous_answers = []
        while trial_count < 3:
            trial_count += 1
            if len(previous_answers) == 0:
                prev_response_prompt = ""
            else:
                prev_response_prompt = (
                    "你之前非法的输出有:" + "; ".join(previous_answers) + "。\n"
                )

            # 生成答案
            payload = {
                "model": "Qwen/Qwen3-8B",
                "messages": [
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "text",
                                "text": rule_prompt,
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                                + valid_move_prompt
                                + prev_response_prompt,
                            }
                        ],
                    },
                ],
                "stream": False,
                "max_tokens": 32768,
                "enable_thinking": False,
                "thinking_budget": 4096,
                "min_p": 0.00,
                "stop": [],
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 20,
                "frequency_penalty": 1,
                "n": 1,
                "response_format": {"type": "text"},
            }

            response = requests.post(url, json=payload, headers=headers)
            response_json = json.loads(response.text)
            # 提取答案
            responsed_text = response_json["choices"][0]["message"]["content"]
            valid_signal, response = extract_move(responsed_text, llm_valid_move_list)
            if valid_signal:
                break
            else:
                previous_answers.append(response)
        if not valid_signal:
            print(previous_answers)
        return response

    logits = torch.from_numpy(np.random.rand(235))
    mask = torch.from_numpy(obs["action_mask"]).type(torch.float32)
    inf_mask = torch.clamp(torch.log(mask), -1e20, 1e20)
    masked_logits = logits + inf_mask

    action = masked_logits.argmax()
    response = agent.action2response(action)
    return response


if __name__ == "__main__":
    input()  # 1
    while True:
        request = input()
        while not request.strip():
            request = input()
        request = request.split()
        if request[0] == "0":
            seatWind = int(request[1])
            agent = FeatureAgent2Adapted(seatWind)
            agent.request2obs("Wind %s" % request[2])
            print("PASS")
        elif request[0] == "1":
            agent.request2obs(" ".join(["Deal", *request[5:]]))
            print("PASS")
        elif request[0] == "2":
            obs = agent.request2obs("Draw %s" % request[1])
            response = obs2response(None, obs)
            response = response.split()
            if response[0] == "Hu":
                print("HU")
            elif response[0] == "Play":
                print("PLAY %s" % response[1])
            elif response[0] == "Gang":
                print("GANG %s" % response[1])
                angang = response[1]
            elif response[0] == "BuGang":
                print("BUGANG %s" % response[1])
        elif request[0] == "3":
            p = int(request[1])
            if request[2] == "DRAW":
                agent.request2obs("Player %d Draw" % p)
                zimo = True
                print("PASS")
            elif request[2] == "GANG":
                if p == seatWind and angang:
                    agent.request2obs("Player %d AnGang %s" % (p, angang))
                elif zimo:
                    agent.request2obs("Player %d AnGang" % p)
                else:
                    agent.request2obs("Player %d Gang" % p)
                print("PASS")
            elif request[2] == "BUGANG":
                obs = agent.request2obs("Player %d BuGang %s" % (p, request[3]))
                if p == seatWind:
                    print("PASS")
                else:
                    response = obs2response(None, obs)
                    if response == "Hu":
                        print("HU")
                    else:
                        print("PASS")
            else:
                zimo = False
                if request[2] == "CHI":
                    agent.request2obs("Player %d Chi %s" % (p, request[3]))
                elif request[2] == "PENG":
                    agent.request2obs("Player %d Peng" % p)
                obs = agent.request2obs("Player %d Play %s" % (p, request[-1]))
                if p == seatWind:
                    print("PASS")
                else:
                    response = obs2response(None, obs)
                    response = response.split()
                    if response[0] == "Hu":
                        print("HU")
                    elif response[0] == "Pass":
                        print("PASS")
                    elif response[0] == "Gang":
                        print("GANG")
                        angang = None
                    elif response[0] in ("Peng", "Chi"):
                        obs = agent.request2obs(
                            "Player %d " % seatWind + " ".join(response)
                        )
                        response2 = obs2response(None, obs)
                        print(
                            " ".join(
                                [
                                    response[0].upper(),
                                    *response[1:],
                                    response2.split()[-1],
                                ]
                            )
                        )
                        agent.request2obs(
                            "Player %d Un" % seatWind + " ".join(response)
                        )
        print(">>>BOTZONE_REQUEST_KEEP_RUNNING<<<")
        sys.stdout.flush()
