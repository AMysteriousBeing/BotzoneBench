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
import re

from data.conf import (
    access_mode_and_llm,
    openai_foreign_info,
    openai_chinese_info,
    silicon_flow_info,
    local_vllm_info,
)

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
        wind_order = ["East Wind", "South Wind", "West Wind", "North Wind"]
        game_wind_prompt = f"The Prevailing Wind is: {wind_order[normal_obs[0]]}."

        seat_wind = f"Your Seat Wind is: {wind_order[normal_obs[1]]}.\n"
        # print(game_wind_prompt, seat_wind)
        # feature[0, normal_obs[0]] = 1
        # feature[1, normal_obs[1]] = 1

        unshown_tile_list = []
        for j in range(34):
            feature[2, j] = normal_obs[j + 2]
            unshown_tile_list.append(TILE_LIST[j] + ": " + str(normal_obs[j + 2]))
        unshown_tile_prompt = f"Unshown tiles are: [{'; '.join(unshown_tile_list)}].\n"
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
        hand_tile_prompt = f"Your hand tiles are: [{'; '.join(hand_tile_list)}].\n"
        pack_prompt_names = [
            "Your melds are: {}.\n",
            "The melds of the next player: {}.\n",
            "The melds of the player sitting across: {}.\n",
            "The melds of the previous player: {}.\n",
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
            "Your game history is: {}.\n",
            "The game history of the next player is: {}.\n",
            "The game history of the player sitting across is: {}.\n",
            "The game history of the previous player is: {}.\n",
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
        "answer:",
        "answer：",
        "Answer:",
        "Answer：",
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
            if "Peng" in action:
                return 1, "Peng"
            if "AnGang" in clean_action:
                return 1, clean_action[2:]
            elif "BuGang" in clean_action:
                return 1, clean_action
            elif "Gang" in clean_action:
                return 1, "Gang"
            return 1, action
    return 0, clean_action


def normalize_text(text):
    return re.sub(r"\r?\n|\r", " ", text)


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


def obs2response(model, obs):
    rule_prompt = """
    You are a Chinese Standard Mahjong (国标麻将, or MCR Mahjong) player. It is a four-player game, and it is played with a basic set of 136 tiles with Chinese characters and symbols.
    Players draw and discard tiles in turn until they complete a winning hand with a 14th tile. The basic type of winning hand consists of four melds and a pair, while there exist winning hands with several special patterns.
    **Tiles and Representation**
    * There are 4 identical copies of each suited tile and honored tiles.
    * Tiles are represented using Letter+Number, i.e. W7, T2, B4, F1, J3, etc.  
    * Suited tiles are divided into 3 suits: Characters(万), Bamboos(条), and Dots(饼), each numbered from 1 to 9.
    * Letter 'W' represents Character suit(万),  'T' for Bamboo suit(条), 'B' for Dots(饼), for example, W3 is Character-3, T8 is Bamboo-8, and B5 is Dot-5.
    * Honor tiles are divided into two sets: Wind tiles of four directions and Dragon tiles of three colors. 
    * Letter 'F' represents Wind tiles(风), specifically, 'F1' is East Wind, 'F2' is South Wind, 'F3' is West Wind, 'F4' is North Wind.
    * Letter 'J' represents Dragon tiles(箭), specifically, 'J1' is Red Dragon, 'J2' is Green Dragon, 'J3' is White Dragon.
    **Melds**
    Melds are groups of tiles within players' hands, which are essential components to form a winning hand. There are three kinds of melds: Pung, Kong, and Chow.
    * A Pung is three identical tiles, either suited tiles or honor tiles. Action 'Peng' means forming Pung with a just discarded tile.
    * A Kong is a set of four identical tiles. While it occupies four physical tiles, it counts as a completed meld (like a Pung) for hand formation and scores additional points. Action 'Gang' means forming Kong with a just discarded tile.
    * A Chow is three suited tiles of the same suit in a consecutive numerical sequence. Action 'Chi' means forming a Chow using a tile just discarded by the player immediately before you (your left-hand player).
    'Chi Tile' maybe contained in valid actions or histories. It means that a player uses two tiles from his hand tiles, and a tile just discards to form a Chow [Tile-1, Tile, Tile+1].
    
    **Important Note on 'Chi' Action Notation:**
    In the context of valid actions or game history, you may encounter a notation like 'Chi W2'. 
    This is a **compact representation** meaning that the player can perform or have performed a 'Chi' action to complete the specific Chow sequence **[W1, W2, W3]**. 
    Crucially, the tile they actually claimed from the previous player's discard could have been **any one of the three tiles** in that sequence (W1, W2, or W3), depending on which tile completed the Chow given the two tiles they already held in hand.
    The notation 'Chi X' (e.g., 'Chi W2') always identifies the **completed Chow sequence** (e.g., [W1, W2, W3]), not the discarded tile taken. 

    Chinese Standard Mahjong specifies 80 different scoring patterns, each worth some points, and a player can only win when their hand is worth no less than 8 points.
    Below are the explanation and examples for scoring patterns.
    **Explanation and Examples for Scoring Patterns**
    Patterns worth 88 points:
        * Big Four Winds: A hand with pungs or kongs of all four winds. Example: [F1, F1, F1, F2, F2, F2, F3, F3, F3, F4, F4, F4, B3, B3]
        * Big Three Dragons: A hand with pungs or kongs of all three dragons. Example: [J1, J1, J1, J2, J2, J2, J3, J3, J3, T6, T7, T8, W2, W2]
        * All Green: A hand consisting of only green tiles, which are: T2, T3, T4, T6, T8, J2. Example: [T2, T3, T4, T4, T4, T4, T6, T6, T6, T8, T8, J2, J2, J2]
        * Nine Gates: First collect 13 number tiles 1112345678999 of one suit with no exposed melds. The 14th tile can be any tile of the same suit. Example: [T1, T1, T1, T2, T3, T4, T5, T6, T7, T8, T9, T9, T9] + T2
        * Four Kongs: A hand with four kongs, regardless of whether they are exposed or concealed. Example: Hand: [W7, W7], Melds: [[T7, T7, T7, T7], [W8, W8, W8, W8], [B3, B3, B3, B3], [B5, B5, B5, B5]]
        * Seven Shifted Pairs: A hand of seven pairs in the same suit with consecutive numbers. Example: [B1, B1, B2, B2, B3, B3, B4, B4, B5, B5, B6, B6, B7, B7]
        * Thirteen Orphans: One of each terminal tile (number one and nine of each suit), one of each honor tile, plus one duplicate tile of any of those thirteen tiles. Example: [T1, T9, W1, W9, B1, B9, F1, F2, F3, F4, J1, J2, J3, J3]
    Patterns worth 64 points:
        * All Terminals: A hand consisting of only terminal tiles, i.e., number 1 or 9 of each suit. Example: [T1, T1, T1, B1, B1, B1, W9, W9, W9, B9, B9, B9, T9, T9]
        * Little Four Winds: A hand with melds of three winds and a pair of the other wind. Example: [F1, F1, F1, F2, F2, F2, F3, F3, F3, F4, F4, T7, T7, T7]
        * Little Three Dragons: A hand with melds of two dragons and a pair of the other dragon. Example: [J1, J1, J1, J2, J2, J2, J3, J3, B2, B2, B2, W5, W5, W5]
        * All Honors: A hand consisting of only honor tiles. [J1, J1, J1, J2, J2, J2, W1, W1, W2, W2, W2, W3, W3, W3]
        * Four Concealed Pungs: A hand with four concealed pungs or kongs.
        * Pure Terminal Chows: A hand with two chows of number 1, 2, 3, two chows of number 7, 8, 9, and a pair of number 5, all in the same suit, i.e., 12312378978955 in one suit. [B1, B2, B3, B7, B8, B9, B1, B2, B3, B7, B8, B9, B5, B5]
    Patterns worth 48 points:
        * Quadruple Chow: A hand with four identical chows. Example: [W2, W3, W4, W2, W3, W4, W2, W3, W4, W2, W3, W4, B6, B6]
        * Four Pure Shifted Pungs: A hand with four pungs or kongs in the same suit with consecutive numbers. Example: [B3, B3, B3, B4, B4, B4, B5, B5, B5, B6, B6, B6, T8, T8]
    Patterns worth 32 points:
        * Four Pure Shifted Chows: A hand with four successive chows in the same suit with a fixed interval of either one or two, but not a combination of both. Example: [T1, T2, T3, T3, T4, T5, T5, T6, T7, T7, T8, T9, W3, W3]
        * Three Kongs: A hand with three kongs, regardless of whether they are exposed or concealed. Example: Hand: [W1, W2, W3, B4, B4], Melds: [[T2, T2, T2, T2], [B3, B3, B3, B3], [W4, W4, W4, W4]]
        * All Terminals and Honors: A hand consisting of only terminal (number 1 or 9 of each suit) and honor tiles. Exmample: [W1, W1, W1, B1, B1, B1, T9, T9, T9, J1, J1, J1, F2, F2]
    Patterns worth 24 points:
        * Seven Pairs: A hand with seven pairs. Four identical tiles can be treated as two pairs, in which case “Tile Hog“ is counted. Example: [T1, T1, T6, T6, W4, W4, W7, W7, B9, B9, F3, F3, J2, J2]
        * Greater Honors and Knitted Tiles: A hand consisting of one of each honor tile, and seven tiles out of a knitted straight. A knitted straight is made up of number 1, 4, 7 of one suit, number 2, 5, 8 of second suit, and number 3, 6, 9 of a third suit. Example: [W1, W4, B2, B8, W3, W6, W9, F1, F2, F3, F4, J1, J2, J3]
        * All Even Pungs: A hand consisting of four pungs or kongs and a pair, where all tiles are suited tiles of even numbers. Example: [B2, B2, B2, B8, B8, B8, T6, T6, T6, T8, T8, T8, W4, W4]
        * Full Flush: A hand consisting of only suited tiles of the same suit. Example: [T1, T2, T3, T3, T4, T5, T6, T6, T6, T9, T9, T9, T7, T7]
        * Pure Triple Chow: A hand with three identical chows. Example: [B1, B2, B3, B1, B2, B3, B1, B2, B3, W8, W8, W8, J2, J2]
        * Pure Shifted Pungs: A hand with three pungs or kongs in the same suit with consecutive numbers. Example: [T5, T5, T5, T6, T6, T6, T7, T7, T7, B2, B3, B4, F2, F2]
        * Upper Tiles: A hand consisting of only suited tiles of number 7, 8, and 9. Example: [W7, W8, W9, B7, B7, B7, T7, T8, T9, T8, T8, T8, B9, B9]
        * Middle Tiles: A hand consisting of only suited tiles of number 4, 5, and 6. Example: [B4, B4, B4, T5, T5, T5, W6, W6, W6, B4, B5, B6, T6, T6]
        * Lower Tiles: A hand consisting of only suited tiles of number 1, 2, and 3. Example: [W1, W2, W3, B1, B1, B1, T1, T2, T3, T2, T2, T2, B3, B3]
    Patterns worth 16 points:
        * Pure Straight: A hand with three chows in the same suit of numbers 1, 2, 3; 4, 5, 6; 7, 8, 9. Example: [B1, B2, B3, B4, B5, B6, B7, B8, B9, T2, T3, T4, J2, J2]
        * Three-Suited Terminal Chows: A hand with two chows of number 1, 2, 3 and 7, 8, 9 in one suit, another two chows of the same number in a second suit, and a pair of number 5 in a third suit. Example: [W1, W2, W3, W7, W8, W9, B1, B2, B3, B7, B8, B9, T5, T5]
        * Pure Shifted Chows: A hand with three successive chows in the same suit with a fixed interval of either one or two, but not a combination of both. Example: [T3, T4, T5, T4, T5, T6, T5, T6, T7, W4, W5, W6, F1, F1]
        * All Fives: A hand with suited tiles of number five in all four melds and the pair. Example: [W3, W4, W5, B4, B5, B6, T5, T6, T7, T5, T5, T5, W5, W5]
        * Triple Pung: A hand with three pungs or kongs in different suits with the same number. Example: [W4, W4, W4, B4, B4, B4, T4, T4, T4, T7, T8, T9, W2, W2]
    Patterns worth 12 points:
        * Lesser Honors and Knitted Tiles: A hand consisting of 14 tiles from these 16 tiles: number 1, 4, 7 of one suit; number 2, 5, 8 of a second suit; number 3, 6, 9 of a third suit; and all honor tiles. Example: [T1, T4, T7, W2, W8, B3, B6, B9, F1, F2, F3, F4, J1, J3]
        * Knitted Straight: A hand consisting of number 1, 4, 7 of one suit, number 2, 5, 8 of a second suit, and number 3, 6, 9 of a third suit, plus a meld and a pair. Example: [B1, B4, B7, T2, T5, T8, W3, W6, W9, T6, T6, T6, J2, J2]
        * Upper Four: A hand consisting of only suited tiles of number 6, 7, 8, and 9.
        * Lower Four: A hand consisting of only suited tiles of number 1, 2, 3, and 4.
        * Big Three Winds: A hand with three pungs or kongs of wind tiles. Example: [F1, F1, F1, F2, F2, F2, F4, F4, F4, B2, B3, B4, W8, W8]
    Patterns worth 8 points:
        * Mixed Straight: A hand with three chows of numbers 1, 2, 3; 4, 5, 6; 7, 8, 9 in different suits. Example: [B1, B2, B3, W4, W5, W6, T7, T8, T9, F2, F2, F2, B5, B5]
        * Reversible Tiles: A hand consisting of only tiles whose shape is point-symmetric regardless of colors. Available tiles are: B1, B2, B3, B4. B5, B8, B9, T2, T4, T5, T6, T8, T9, J3. Example: [B3, B4, B5, B9, B9, B9, T4, T5, T6, T9, T9, T9, J3, J3]
        * Mixed Triple Chow: A hand with three chows in different suits with the same numbers. Example: [T6, T7, T8, B6, B7, B8, W6, W7, W8, T2, T2, T2, F3, F3]
        * Mixed Shifted Pungs: A hand with three pungs or kongs in different suits with consecutive numbers. Example: [W7, W7, W7, B8, B8, B8, T9, T9, T9, B2, B3, B4, W1, W1]
        * Chicken Hand: A hand which would otherwise be worth of zero fans, with flower tiles not included. Example: Hand: [W1, W2, W3, T7, T8, J2, J2] + T9, Melds: [[W3, W4, W5], [B2, B2, B2]]
        * Last Tile Draw: The winning hand is completed by drawing the last tile of the wall.
        * Last Tile Claim: The winning hand is completed by seizing a tile from another player when the tile wall is empty.
        * Out With Replacement Tile: The winning hand is completed when drawing a tile right after making a concealed kong or a promoted kong.
        * Robbing the Kong: The winning hand is completed by robbing the tile which another player adds to an exposed pung to form a kong.
    Patterns worth 6 points:
        * All Pungs: A hand with four pungs or kongs, regardless of whether they are exposed or concealed.
        * Half Flush: A hand consisting of only honor tiles and suited tiles of one suit. Example: [W1, W2, W3, W5, W5, W5, W6, W7, W8, F1, F1, F1, J3, J3]
        * Mixed Shifted Chows: A hand with three consecutive chows in different suits, each shifted up one number from the one before it. Example: [W3, W4, W5, B4, B5, B6, T5, T6, T7, W5, W5, W5, B9, B9]
        * All Types: A hand containing tiles of all three suits, wind tiles and dragon tiles. Example: [W1, W2, W3, B4, B4, B4, T7, T8, T9, F2, F2, F2, J1, J1]
        * Melded Hand: Every meld and pair in the hand must be completed by tiles from other players, which means that all melds must be exposed, and one tile of the pair is the 14th winning tile from other players.
        * Two Concealed Kongs: A hand with two concealed kongs.
        * Two Dragon Pungs: A hand with two pungs or kongs of dragon tiles.
    Patterns worth 4 points:
        * Outside Hand: A hand with terminals (number 1 or 9 of suited tiles) and honor tiles in every meld and the pair.
        * Fully Concealed Hand: A hand with no tiles from other players, which means that all melds must be concealed, and the winning tile is drawn by the winner.
        * Two Melded Kongs: A hand with two exposed kongs.
        * Last Tile: The winning tile is the last tile of the same tile that has not been revealed to all players, which means three of the same tile has been exposed in melds or discarded on the table.
    Patterns worth 2 points:
        * Dragon Pung: A hand with a pung or kong of dragon tiles. This pattern can be counted more than once if there are multiple melds meeting this requirement.
        * Prevalent Wind: A hand with a pung or kong of the prevalent wind of this game.
        * Seat Wind: A hand with a pung or kong of the seat wind of the current player.
        * Concealed Hand: A hand with no tiles from other players except the winning tile, which means that all melds must be concealed, while the winning tile is seized from other players.
        * All Chows: A hand with four chows and a pair of suited tiles.
        * Tile Hog: A hand with four identical tiles without forming a kong. This pattern can be counted more than once if there are multiple tiles meeting this requirement.
        * Mixed Double Pung: A hand with two pungs or kongs in different suits with the same number. This pattern can be counted more than once if there are multiple melds meeting this requirement.
        * Two Concealed Pungs: A hand with two concealed pungs or kongs.
        * Concealed Kong: A hand with a concealed kong.
        * All Simples: A hand with no terminal tiles (number 1 or 9 of suited tiles) and honor tiles.
    Patterns worth 1 points:
        * Pure Double Chow: A hand with two identical chows. This pattern can be counted more than once if there are multiple melds meeting this requirement.
        * Mixed Double Chow: A hand with two chows in different suits with the same number. This pattern can be counted more than once if there are multiple melds meeting this requirement.
        * Short Straight: A hand with two chows in the same suit with successive numbers, like 234 and 567. This pattern can be counted more than once if there are multiple melds meeting this requirement.
        * Two Terminal Chows: A hand with two chows in the same suit with numbers 1, 2, 3 and 7, 8, 9. This pattern can be counted more than once if there are multiple melds meeting this requirement.
        * Pung of Terminals or Honors: A hand with a pung or kong of terminal tiles (number 1 or 9 of suited tiles) or honor tiles. This pattern can be counted more than once if there are multiple melds meeting this requirement.
        * Melded Kong: A hand with one exposed kong.
        * One Voided Suit: A hand with exactly two of the three suits of tiles.
        * No Honors: A hand with no honor tiles.
        * Edge Wait: The winning tile must be a suited tile of number 3 to complete a chow of 1, 2, 3, or number 7 to complete a chow of 7, 8, 9. This pattern is not counted if there exists multiple tiles to complete a winning pattern.
        * Closed Wait: The winning tile must be a suited tile to complete a chow as the middle number. This pattern is not counted if there exists multiple tiles to complete a winning pattern.
        * Single Wait: The winning tile must be the tile to complete a pair. This pattern is not counted if there exists multiple tiles to complete a winning pattern.
        * Self Drawn: The winning tile must be drawn by the winner.
    Now is your turn, to your best ability, please briefly evaluate a few proimsing moves, provide reason for your final choice, and output one of the valid actions with specified format, such as Play B5.
        Your response format should be exactly:
        Evaluation: [Your Evaluation]
        Reason: [Your Reason]
        Answer: [Your Answer]
    """
    access_mode, model_name = access_mode_and_llm()
    if access_mode == "local_vllm":
        api_base, api_key, query_api = local_vllm_info()
    elif access_mode == "silicon_flow":
        api_base, api_key, query_api = silicon_flow_info()
    elif access_mode == "lab_openai_foreign":
        api_base, api_key, query_api = openai_foreign_info()
    elif access_mode == "lab_openai_chinese":
        api_base, api_key, query_api = openai_chinese_info()

    llm_valid_move_list = obs["action_mask_llm"]
    if len(llm_valid_move_list) == 1:
        # pass
        return llm_valid_move_list[0], None
    else:
        llm_state_info = obs["observation_llm"]
        state_prompt = "The following is the state information: " + llm_state_info
        valid_move_prompt = f"The followings are your valid actions:[{'; '.join(llm_valid_move_list)}]。"

        # Fault Tolerance
        trial_count = 0
        previous_answers = []
        while trial_count < 3:
            trial_count += 1
            if len(previous_answers) == 0:

                prev_ans_prompt = ""
            else:
                prev_ans_prompt = (
                    "Your previous invalid answers are: "
                    + ", ".join(previous_answers)
                    + "."
                )
            user_prompt = state_prompt + valid_move_prompt + prev_ans_prompt
            # gether response from llm
            responsed_text, reasoning_text = query_api(
                api_base,
                api_key,
                model_name,
                rule_prompt,
                user_prompt,
            )
            answer_text = extract_answer(responsed_text)
            valid_signal, response = extract_move(
                "Answer:" + answer_text, llm_valid_move_list
            )
            if valid_signal:
                break
            previous_answers.append(answer_text)

        return response, json.dumps(
            {
                "system_prompt": rule_prompt,
                "user_prompt": user_prompt,
                "reasoning": reasoning_text,
                "output": responsed_text,
            }
        )


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
            response, debug_info = obs2response(None, obs)
            response = response.split()
            if response[0] == "Hu":
                print("HU")
            elif response[0] == "Play":
                print("PLAY {}\n{}".format(response[1], debug_info))
            elif response[0] == "Gang":
                print("GANG {}\n{}".format(response[1], debug_info))
                angang = response[1]
            elif response[0] == "BuGang":
                print("BUGANG {}\n{}".format(response[1], debug_info))
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
                    response, debug_info = obs2response(None, obs)
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
                    response, debug_info = obs2response(None, obs)
                    response = response.split()
                    if response[0] == "Hu":
                        print("HU")
                    elif response[0] == "Pass":
                        if debug_info:
                            print("PASS" + "\n{}".format(debug_info))
                        else:
                            print("PASS")
                    elif response[0] == "Gang":
                        print("GANG")
                        angang = None
                    elif response[0] in ("Peng", "Chi"):
                        obs = agent.request2obs(
                            "Player %d " % seatWind + " ".join(response)
                        )
                        response2, debug_info2 = obs2response(None, obs)
                        print(
                            " ".join(
                                [
                                    response[0].upper(),
                                    *response[1:],
                                    response2.split()[-1],
                                ]
                            )
                            + "\n{}".format(
                                json.dumps({"action": debug_info, "tile": debug_info2})
                            )
                        )
                        agent.request2obs(
                            "Player %d Un" % seatWind + " ".join(response)
                        )
        print(">>>BOTZONE_REQUEST_KEEP_RUNNING<<<")
        sys.stdout.flush()
