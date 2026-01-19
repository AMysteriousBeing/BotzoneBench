from botzone.online.bot import BotConfig, Bot
from botzone.online.game import GameConfig

LV0_CONFIG_LIST = {
    "Ataxx": BotConfig(
        game=GameConfig.fromName("Ataxx"),
        path="local_bots/ataxx/sample.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config",
    ),
    "ChineseStandardMahjong": BotConfig(
        game=GameConfig.fromName("ChineseStandardMahjong"),
        path="local_bots/mahjong/sample.py",
        extension="py39",
        simpleio=True,  # bot是否使用简单输入
        keep_running=True,  # bot是否长时运行
        userfile_path="./api_config",
    ),
    "FightTheLandlord": BotConfig(
        game=GameConfig.fromName("FightTheLandlord"),
        path="local_bots/landlord/sample.py",
        extension="py39",
        simpleio=False,
        keep_running=False,
        userfile_path="./api_config",
    ),
    "Go": None,
    "Gomoku": BotConfig(
        game=GameConfig.fromName("Gomoku"),
        path="local_bots/gomoku/sample.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config",
    ),
    "Reversi": BotConfig(
        game=GameConfig.fromName("Reversi"),
        path="local_bots/reversi/sample.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config",
    ),
    "TicTacToe": BotConfig(
        game=GameConfig.fromName("TicTacToe"),
        path="local_bots/tictactoe/sample.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config",
    ),
    "Chess": BotConfig(
        game=GameConfig.fromName("Chess"),
        path="local_bots/chess/sample.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config",
    ),
    "TexasHoldem2p": BotConfig(
        game=GameConfig.fromName("TexasHoldem2p"),
        path="local_bots/texasholdem/sample.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config",
    ),
}

LV1_CONFIG_LIST = {
    "Reversi": [
        BotConfig.fromID("5677b2bd41c47e1a0f3622ad"),  # 水能载舟亦可赛艇 601
        BotConfig.fromID("5c8906d683652225021eca3e"),  # Prominance一号 599
        BotConfig.fromID("567ad752e98e37a623ef1d9d"),  # 傻儿子002 598
        BotConfig.fromID("5fe35b71d9383f7579a4c2d2"),  # othello 597
    ],
    "Gomoku": [
        BotConfig.fromID("61cb50238d8bd011d779c378"),  # py_不知道 487
        BotConfig.fromID("61c4d1428d8bd011d7748737"),  # 叉院RL2024_16组 486
        BotConfig.fromID("677b93c2d5b53605c84e2fc7", userfile=True),  # MCTS_naive 484
        BotConfig.fromID("6371c8de8d38157ab2ae4d5d"),  # Gomoku_MCTS_keep 483
    ],
    "TicTacToe": [
        BotConfig.fromID("63cb39e8ee1bce5e6c7f9d12", userfile=True),  # mcts最后测试 42
        BotConfig.fromID("63c684faee1bce5e6c7b68c8", userfile=True),  # FlareonMCTS 40
    ],
    "Ataxx": [
        BotConfig.fromID("586bcf62af944f3f232d615d"),  # lajifff 1037
        BotConfig.fromID("5a4841865a2fe258a9abf93e"),  # Ataxx 1031
        BotConfig.fromID("5a45d00c5a2fe258a9a5704a"),  # biscuit5 1029
        BotConfig.fromID("6808a80ba32ffa0bd4954e73"),  # 第一次提交测试 1034
    ],
    "Chess": BotConfig.fromID("682a9a90d870d24732ac84e4"),  # tester 4
    "TexasHoldem2p": BotConfig.fromID("63e4f8666ce79f4b2db33ecd"),  # Test 16
    "FightTheLandlord": [
        BotConfig.fromID("5af56457433be66904cd5fc9"),  # papertiger 448
        BotConfig.fromID("609e27f6f827b82eae68c497"),  # FightGroundOwner01 447
        BotConfig.fromID("5aefb5aca5858d0880e4b138"),  # practise 446
        BotConfig.fromID("5cef7583947c9c03d0a8856d"),  # 伞兵114514号卢本伟 445
    ],
    "ChineseStandardMahjong": [
        BotConfig.fromID("5ec4fab8703c1e22d93ec0c0"),  # P大第0搅屎棍 621
        BotConfig.fromID("5eb904a67deb2c02c4a623f2"),  # AmaneSuzuha_idiot 624
        BotConfig.fromID("5ec0b74c703c1e22d939edcf"),  # 麻将小队参赛版 622
        BotConfig.fromID("5eca3824e9dfff058425851b"),  # 爱吃麻酱 634
    ],
}

LV2_CONFIG_LIST = {
    "Reversi": [
        BotConfig.fromID("568e729f0e303a823144533b"),  # haha泥吼啊 548
        BotConfig.fromID("5685fc629aab81be75ae57d4"),  # 神们_求轻* 541
        BotConfig.fromID("5b23253f0edf94798cdc3d3e"),  # 虫子的第三个bot 546
        BotConfig.fromID("65a2ac235652b005b946e542"),  # 垃圾黑白32 547
    ],
    "Chess": BotConfig.fromID("675be019f8ef9f3aca87162d"),  # CLA94_Chess 3
    "Ataxx": [
        BotConfig.fromID("5a6737faf055de4894298bcb"),  # xyz 1021
        BotConfig.fromID("5a51b219fe46681ed44c4006"),  # wuming 1020
        BotConfig.fromID("61b5b1278d8bd011d760df70"),  # artificial_idiot 1016
        BotConfig.fromID("67fcb61543aaa306cc1adb77"),  # 超绝同化闪光 1013
    ],
    "Gomoku": [
        BotConfig.fromID("658c4d4926354d2b0ff6b6bd", userfile=True),  # trymcts 461
        BotConfig.fromID("6591134126354d2b0ffb7286"),  # boku 465
        BotConfig.fromID("5ce4e07ad2337e01c7a6a396"),  # skrskr 467
        BotConfig.fromID("6598021426354d2b0f01c91e"),  # MCTS_CPP 458
    ],
    "TexasHoldem2p": [
        BotConfig.fromID("63e384696ce79f4b2db20359"),  # test 9
        BotConfig.fromID("63f97abb6ce79f4b2dca6f49"),  # 德州扑克的尽头 8
    ],
    "FightTheLandlord": [
        BotConfig.fromID("5b14092f8472ec612b15720f"),  # 不为谁而作的bot 421
        BotConfig.fromID("5b2e9e336a209a1c864fcfc6"),  # idiot 420
        BotConfig.fromID("5b13f2aa8472ec612b154262"),  # 李重八 418
        BotConfig.fromID("5b13842720c3be3c79f942db"),  # 斗地主0 405
    ],
    "ChineseStandardMahjong": [
        BotConfig.fromID("5ec3e475703c1e22d93d658a"),  # eeee 454
        BotConfig.fromID("66817f37b54d400b70945271", userfile=True),  # aimj 474
        BotConfig.fromID("5eca8b62e9dfff0584261267"),  # Phoenix 461
        BotConfig.fromID("5eaaddfda96e206b64793d36"),  # xxx 458
    ],
}

LV3_CONFIG_LIST = {
    "Reversi": [
        BotConfig.fromID("568d41940e303a82314441ab"),  # Alpha 472
        BotConfig.fromID("6583232282ee46246bce44e7"),  # botjson1 481
        BotConfig.fromID("65a4194f5652b005b94906b5"),  # 风信子1 492
        BotConfig.fromID("65a15bff26354d2b0f0a883e"),  # reversi 478
    ],
    "Ataxx": [
        BotConfig.fromID("61d013048d8bd011d77ed3b1"),  # 鸡汤来喽 999
        BotConfig.fromID("586529704d074667e2accbfc"),  # pkuhgh 1002
        BotConfig.fromID("61cfe2348d8bd011d77eaff9"),  # 比尔的Bot 1003
        BotConfig.fromID("61d585198d8bd011d7839426"),  # 随便吧 1008
    ],
    "FightTheLandlord": [
        BotConfig.fromID("60c33170dce9141a1de3db33"),  # 靳博雅 187
        BotConfig.fromID("5b0563e1c57fa61d35cf63f5"),  # landlord_test 188
        BotConfig.fromID("5b12b95c20c3be3c79f8e95c"),  # 你是MM还是GG呀 182
        BotConfig.fromID("60cb300bdce9141a1d06f5a2"),  # 十七张牌你能秒我 194
    ],
    "Chess": BotConfig.fromID("61d6dcc799f5414277309c51"),  # ShadowOfRyouko 2
    "Gomoku": [
        BotConfig.fromID("61c46ae78d8bd011d773ef93"),  # Opprotoss 424
        # BotConfig.fromID("619c847363626007396506db"),  # Liaoguoqing 415
        BotConfig.fromID("6578544882ee46246bc5abf5"),  # aaaaa 431
        BotConfig.fromID("6566a5f482ee46246bb5857e"),  # trav 427
        BotConfig.fromID("5b1389aa20c3be3c79f94528"),  # gezifeiWZQ 428
    ],
    "TexasHoldem2p": BotConfig.fromID("63fc5cbe6ce79f4b2dcce80f"),  # 赌___神 1
    "ChineseStandardMahjong": [
        BotConfig.fromID("5fec394cd9383f7579add80f"),  # jsbsbsbsbsb 242
        BotConfig.fromID("694dfd233cb83c184cfd76df", userfile=True),  # TMahjong 251
        BotConfig.fromID("5fed742dd9383f7579af6982"),  # cpp 218
        BotConfig.fromID("64a11e7ba24a147da2ace510", userfile=True),  #  影流之主 209
    ],
}

LV4_CONFIG_LIST = {
    "Reversi": [
        BotConfig.fromID("5a5a1077fe46681ed451ecf1"),  # mcts_2 361
        BotConfig.fromID("6582f63982ee46246bce2dfa"),  # test 363
        BotConfig.fromID("658d836726354d2b0ff7deda"),  # 暂时不能给你明确的答复 366
        BotConfig.fromID("6590341526354d2b0ffa7d4b"),  # YS_Reversi_Bot 369
    ],
    "Ataxx": [
        BotConfig.fromID("5a5dc708fe46681ed45478a5"),  # Tinker 963
        BotConfig.fromID("680b78ae66c1f905d8bb14dc"),  # no1 908
        BotConfig.fromID("5864aaaba932ef1a41c32000"),  # nyanyanya 924
        BotConfig.fromID("61d558248d8bd011d7836f15"),  # 真心打不过2 918
    ],
    "Chess": BotConfig.fromID("61e9683f3e8ab26550c84f7e", userfile=True),  # stockfish 1
    "Gomoku": [
        BotConfig.fromID("63bd4cb0ee1bce5e6c7267b5"),  # RL2022难兄难弟 325
        BotConfig.fromID("6593b22b26354d2b0ffdf56d"),  # mctsGomoku 349
        BotConfig.fromID("5b0a17975de6fd5a623b683f"),  # Husky 362
        BotConfig.fromID("5b113d80b10ac8057afddc1b"),  # Nightfury 367
    ],
    "FightTheLandlord": [
        BotConfig.fromID(
            "692679b636184360c6ff49b9", userfile=True
        ),  # 为什么斗地主不能吃碰杠 3
        BotConfig.fromID("66a1c43238d75d2f025ab988", userfile=True),  # easydou 11
        BotConfig.fromID("630a0b4266467507cacb6f24", userfile=True),  # CZKwiS 19
        BotConfig.fromID("61f3c4973e8ab26550d3848b", userfile=True),  # Dou1Dou 4
    ],
    "ChineseStandardMahjong": [
        BotConfig.fromID("666bc4d8e185683ff83c0cbc", userfile=True),  # AI是啊不一 18
        BotConfig.fromID("67aa175c680c9a25f8d53f69", userfile=True),  # 人之爱 8
        BotConfig.fromID("684431e6c5819238f6729e70", userfile=True),  # test 13
        BotConfig.fromID("66883144b54d400b70a004fe", userfile=True),  # test 14
    ],
}

LV5_CONFIG_LIST = {
    "Reversi": [
        BotConfig.fromID("5e740a94e952081b8838758a"),  # AlphaMCTS 271
        BotConfig.fromID("5a5a4753fe46681ed4521299"),  # 羽默蓝 275
        BotConfig.fromID("5a5b50d3fe46681ed452cb00"),  # SEU_DongHan 270
        BotConfig.fromID("659ff01526354d2b0f093aea"),  # reversi2 269
    ],
    "Ataxx": [
        BotConfig.fromID("680ba82c66c1f905d8bb9ece"),  # 何嘉宸_梁子铎 781
        BotConfig.fromID("5a4092b65a2fe258a9964fad"),  # nedann 751
        BotConfig.fromID("585f84386d6c3d654a242342"),  # 散华礼弥就看看大佬们 721
        BotConfig.fromID("5a41093d5a2fe258a997caee"),  # 苗木诚 729
    ],
    "Gomoku": [
        BotConfig.fromID("5b51210cb69487015e06f615"),  # aa1111 154
        BotConfig.fromID("658d130726354d2b0ff78fff"),  # Soundz 156
        BotConfig.fromID("6185f8c5dc5aa23c13afa1f1"),  # alpharun214782 157
        BotConfig.fromID("61cc812c8d8bd011d77ac110"),  # aoo 159
    ],
}

LV6_CONFIG_LIST = {
    "Gomoku": [
        BotConfig.fromID("599b9ce3579ce9447f9f5843", userfile=True),  # 	Gomoku 31
        BotConfig.fromID("594c60df9f223932cc47841a"),  # Gomoku 26
        BotConfig.fromID("5b51c949b69487015e074936"),  # 专业**头抛光打蜡 23
        BotConfig.fromID("5ae5f3ec4623c5389913a399"),  # trueVeg 21
    ],
    "Ataxx": [
        BotConfig.fromID("61ab42617b65754c1d4f8477"),  # dale001 661
        BotConfig.fromID("58627e0d6d6c3d654a24beef"),  # hipugna 640
        BotConfig.fromID("5a3ca0ea5a2fe258a98cf036"),  # three 635
        BotConfig.fromID("5865eb624d074667e2ad0c1b"),  # 薛定谔的滑稽 633
    ],
    "Reversi": [
        BotConfig.fromID("65a1465526354d2b0f0a7424"),  # final_bot 151
        BotConfig.fromID("5ac1075cc5d5e3196fc6ea48"),  # 吵吵机器人Alter 127
        BotConfig.fromID("5c91cbf19f425613e1cf1b26"),  # 希望无bug 121
        BotConfig.fromID("68eb5c80dcee294b521c5162"),  # GlaceonNegamax00 126
    ],
}


LLM_CONFIG_LIST2 = {
    "Ataxx": BotConfig(
        game=GameConfig.fromName("Chess"),
        path="local_bots/ataxx/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config2",
    ),
    "ChineseStandardMahjong": BotConfig(
        game=GameConfig.fromName("ChineseStandardMahjong"),
        path="local_bots/mahjong/llm_bot.py",
        extension="py39",
        simpleio=True,  # bot是否使用简单输入
        keep_running=True,  # bot是否长时运行
        userfile_path="./api_config2",
    ),
    "FightTheLandlord": BotConfig(
        game=GameConfig.fromName("FightTheLandlord"),
        path="local_bots/landlord/llm_bot.py",
        extension="py39",
        simpleio=False,
        keep_running=False,
        userfile_path="./api_config2",
    ),
    "Go": BotConfig(
        game=GameConfig.fromName("Chess"),
        path="local_bots/go/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config2",
    ),
    "Gomoku": BotConfig(
        game=GameConfig.fromName("Chess"),
        path="local_bots/gomoku/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config2",
    ),
    "Reversi": BotConfig(
        game=GameConfig.fromName("Reversi"),
        path="local_bots/reversi/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config2",
    ),
    "TicTacToe": BotConfig(
        game=GameConfig.fromName("Chess"),
        path="local_bots/tictactoe/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config2",
    ),
    "Chess": BotConfig(
        game=GameConfig.fromName("Chess"),
        path="local_bots/chess/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config2",
    ),
    "TexasHoldem2p": BotConfig(
        game=GameConfig.fromName("TexasHoldem2p"),
        path="local_bots/texasholdem/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config2",
    ),
}

LLM_CONFIG_LIST = {
    "Ataxx": BotConfig(
        game=GameConfig.fromName("Chess"),
        path="local_bots/ataxx/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config",
    ),
    "ChineseStandardMahjong": BotConfig(
        game=GameConfig.fromName("ChineseStandardMahjong"),
        path="local_bots/mahjong/llm_bot.py",
        extension="py39",
        simpleio=True,  # bot是否使用简单输入
        keep_running=True,  # bot是否长时运行
        userfile_path="./api_config",
    ),
    "FightTheLandlord": BotConfig(
        game=GameConfig.fromName("FightTheLandlord"),
        path="local_bots/landlord/llm_bot.py",
        extension="py39",
        simpleio=False,
        keep_running=False,
        userfile_path="./api_config",
    ),
    "Go": BotConfig(
        game=GameConfig.fromName("Chess"),
        path="local_bots/go/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config",
    ),
    "Gomoku": BotConfig(
        game=GameConfig.fromName("Chess"),
        path="local_bots/gomoku/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config",
    ),
    "Reversi": BotConfig(
        game=GameConfig.fromName("Reversi"),
        path="local_bots/reversi/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config",
    ),
    "TicTacToe": BotConfig(
        game=GameConfig.fromName("Chess"),
        path="local_bots/tictactoe/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config",
    ),
    "Chess": BotConfig(
        game=GameConfig.fromName("Chess"),
        path="local_bots/chess/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config",
    ),
    "TexasHoldem2p": BotConfig(
        game=GameConfig.fromName("TexasHoldem2p"),
        path="local_bots/texasholdem/llm_bot.py",
        extension="py39",
        simpleio=False,  # bot是否使用简单输入
        keep_running=False,  # bot是否长时运行
        userfile_path="./api_config",
    ),
}
