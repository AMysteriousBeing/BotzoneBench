## Usage Guide for BotzoneBench4LLM
### Deploy Baseline Bots
* Baseline bot information is available at `bot_info.py`.
* Upon first run of the code, you may directly download bot information from Botzone.
* Alternatively, obtain `bot.tar.gz` and place the decompressed `bot` folder under `botzone/online`

### Important Files
* `local_bots/game_name/llm_bot.py`: LLM-based bots.
* `local_bots/game_name/sample.py`: random-action bots.
* `bot_info.py`: The file in which baseline bots' information are saved.
* `evaluate_single_game.py`: Core evaluation functions for LLMs.
* `api_config/conf.py`: 
    * `access_mode_and_llm()`: This function tells LLM-based bots which config file to read. Defaults to `llm_config.json`.
    * `llm_config.json`: This file specifies LLM name and access-mode for the LLM. 
    * `xxx_conf.json`: This file specifies `api_base` and `api_key` for LLM-based bots.

### Trace for Any Calls to `evaluate_single_game.py`'s `batched_evaluation` Function
1. Resolve parameters and asynchronously call `evaluation()`.
2. Initiate `runMatch` and starts docker environments.
3. Each LLM-based bot reads `access_mode_and_llm()` from `api_config/conf.py` to determine config file.
4. Each LLM-based bot reads config file to determine LLM's API base and key. 
5. Run evaluation games. 

### Special Note on Botzone-local's Path System
During initialization for BotConfig, `userfile_path` parameter points to the root of the bot's `/data` folder.

Any path access within Botzone-local should be prefixed with `/data`.

