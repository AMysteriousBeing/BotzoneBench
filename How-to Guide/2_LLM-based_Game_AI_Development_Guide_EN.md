## LLM-based Game AI Development Guide
This guide outlines the process of developing an LLM-based Game AI for BotzoneBench4LLM.

### Game Environment Information
1. Available game environments are listed in: `botzone/envs/README.md`. Games listed in Section Projects but not listed in `README.md` will soon be updated here. 

2. Detailed game rules and input/output formats are available at: `https://wiki.botzone.org.cn/index.php?title=%E6%B8%B8%E6%88%8F`.

3. Download the reference bot from the game information page. 

4. If no Python version is available, convert the reference bot to Python.

5. Verify the bot runs correctly using the provided Docker image. 

6. Develop the LLM-based AI for the game:
- Provide a concise rule explanation for the LLM. (System Prompt)
- Define the LLM’s output format. (System Prompt)
- Convert game state into natural language. (User Prompt)
- Compute legal moves and supply them to the LLM. (User Prompt)
- Parse the LLM’s response into the Botzone-standard format. 

7. Ensure the LLM-based AI can complete a game without errors (in most cases).

### Sample LLM-based AI 

* A sample implementation is available for Reversi.

* Run the game with:  `test_local_reversi_with_llm.py'

* The LLM-based bot file is located at: `local_reversi_bot/reversi_with_llm.py`.

### Note

* Environment names are listed in lines 278–300 of `botzone/online/games.py`
* The `BotConfig` path parameter should point to your bot’s file. 
* For simplicity, each bot should be contained in a single file.
* As the final paper is in English, **prompts must include an English version**. You may develop in Chinese first, but verify the English translation works correctly.
* Please document your implementation and add code comments for future debugging and maintenance.

### Projects
* Proposed games with estimated difficulty (in parentheses):
    - Amazons (Simple)
    - Ataxx (Simple)
    - Reversi (Simple, Chinese prompt implemented)
    - TicTacToe (Simple, Done)
    - Snake (Simple, **CANCELLED**)
    - Hex (Simple)
    - TexasHold'em (Simple)
    - Gomoku (Simple+)
    - Kingz (Simple+, **CANCELLED**)
    - Go-v19 (Simple+)
    - ChineseStandardMahjong-dup (Hard)
    - FightTheLandlord (Hard)
    - Chess (Hard)
    - Tractor (Hard)
    - ChineseChess (Hard)
* The main difficulties involve handling game logic, processing the game state, calculating legal moves, and translating the output. When constructing the prompt, you should enumerate all possible legal moves. Note:
    * Full legal move list required: ChineseChess, Chess;
    * No leval move list required: Gomoku, Go (any empty point is a valid move)

* Each participant should implement:
    - 1–2 Simple games
    - 2 Hard game
* Start with a simple game to familiarize yourself with the process.
    


