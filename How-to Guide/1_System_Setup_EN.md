## Setup Guide for BotzoneBench4LLM

### System/Environment Preparation

Pre-requisite: Windows/Linux, Git, Anaconda/Miniconda, and Docker

On **Windows**, we recommend using any WSL2 distros with **CgroupV1**; on **Linux**, we recommend using Ubuntu 22.04/24.04 LTS with **CgroupV1** for better compatibility with the tools used in this guide.

WSL installation Guide is available at: https://learn.microsoft.com/zh-cn/windows/wsl/install (CN)and https://learn.microsoft.com/en-us/windows/wsl/install (EN). We recommend using Ubuntu 22.04/24.04 LTS Distro for WSL2. 

Note: in WSL2, you can access your files under windows with: `cd /mnt/c/your-file-path` for files in C or `cd /mnt/d/your-file-path` for files in D disks.

Use command `mount | grep cgroup` to check Cgroup version. If the default version is **CgroupV2**, you can manually install https://github.com/microsoft/WSL/releases/tag/2.2.4 kernel for **CgroupV1**.

Anaconda/Miniconda can be installed via: https://www.anaconda.com/download

Docker for Ubuntu can be installed via: https://docs.docker.com/engine/install/ubuntu/

### Download Botzone-local repo

1. Git Clone the repo with: `git clone https://github.com/AMysteriousBeing/BotzoneBench.git`

2. Navigate to the directory: `cd BotzoneBench`

### Python Environment Preparation

1. Create a new conda environment for the project: `conda create -n your-name-for-env python=3.10`

2. Activate the environment: `conda activate your-name-for-env`


3. Install required packages using pip: `pip install -r requirements.txt`

4. Install NodeJS and npm: `pip install nodejs npm openai`

### Docker Image Setup

1. Download docker image Docker Hub: botzone/env-ale:latest

2. Add yourself to the group that owns the Docker daemon (usually `docker`): `sudo usermod -aG docker $USER`

3. Verify image by typing: `docker images` or `docker image list` and verify that the ID is: `8316c0d846a7`.

4. locate demo.py in botzone-local directory and comment out testMahjong() on line 142.

5. Run the script with `python demo.py` to ensure the image runs without problems. 

## Remote Large Model API Service
If you are developing using the API service of a remote large model, we recommend using SiliconFlow's Qwen3-8B for development, as it meets the minimum inference requirements and is free. Later, you can explore other platforms or other versions of large model API services on your own to achieve better performance.

1. Register for a SiliconFlow account: https://www.siliconflow.cn/

2. Obtain an API key: On the SiliconFlow account homepage, click "API Keys", create a new API key, and you will obtain the API key.

3. Configure the API key: In the api_config/silicon_flow_conf.json file, replace your-key with the API key you obtained.

4. Remember the model name you choose: You can find the model name in the Model Plaza. Click on any model, and there is a copy button next to each model name. Click it to copy the model name.

## Local Development/Local LLM Setup
The following guide is for setting up local LLM for local developemnt only. Choose one of VLLM or Ollama, we recommend using OLLama for its efficient resource use. 

### Ollama Setup

1. Install Ollama with: `curl -fsSL https://ollama.com/install.sh | sh`

2. Pull model and test speed: `ollama run qwen3:4b-instruct-2507-q4_K_M --verbose`

3. Modify network config so that ollama can be access by docker: `sudo nano /etc/systemd/system/ollama.service`

4. with in `ollama.service` file, add the following line:`Environment="OLLAMA_HOST=0.0.0.0:11434"`, then save and close the file

5. Restart ollama service with:
```
sudo systemctl daemon-reload
sudo systemctl restart ollama.service
```

6. Modify context length of model for Ollama: 
```
ollama show --modelfile qwen3:4b-instruct-2507-q4_K_M > Modelfile
nano Modelfile
```
    - Within Modelfile, add or modify the following line: `PARAMETER num_ctx 4096`

7. Export and create a new model: `ollama create qwen3:4b-15360 -f Modelfile`

8. Change line 20 and line 27 in file `test_api.py` to your deployed IP and model path/name
 
9. Verify the local llm is running and responding: `python path-to-file/test_api.py`

### VLLM Setup

1. Ensure you are in the conda environment: `conda activate your-name-for-env`

2. Install vllm and modelscope with: `pip install vllm modelscope`

3. Within a terminal session, download model
```
export MODELSCOPE_CACHE=/path/to/your/custom/dir
modelscope download Eslzzyl/Qwen3-4B-Instruct-2507-AWQ
```

 4. Modify the path to the model in `start_vllm.sh` and run it with: `path-to-file/start_vllm.sh` to start local llm service.

 5. Change line 20 and line 27 in file `test_api.py` to your deployed IP and model path/name.
 
 6. Verify the local llm is running and responding: `python path-to-file/test_api.py`.


### Confirm Docker-to-LLM Connection 

1. Locate `local_reversi_bot/reversi_with_llm.py`.

2. On line 194, confirm networking address; on line 218, confirm model name.

3. Run simulation with `python test_local_reversi_with_llm.py`.

## Code Repository Contents
1. api_config/: Contains configuration files for the local large model API service.

2. botzone/: Contains the code for the game environment (generally no need to modify).

3. local_bots/: Contains the locally developed AI agent code. Under each game folder, sample.py is a random action agent, and llm_bot.py is an agent based on a large model.

4. demo.py: Used to check if the botzone-ALE docker environment is running correctly.

5. evaluate_single_round.py: Used to evaluate the performance of a large model-based agent against a traditional agent for the Mahjong game.


6. evaluate_single_game.py: Used to batch compare the performance of large model-based agents against traditional agents. If using a remote API service, pay attention to the availability of the API used. Setting parallel_ct too high may cause API calls to fail, thus preventing the evaluation from completing. For domestic large model APIs, it can be set to 8-16; for foreign large model APIs, it is recommended to set it to 4-8.

7. evaluate_tournament.py: Used to evaluate the performance among large model-based agents.

8. bot_info.py: Contains agent configurations for the game environment, where Lvx_CONFIG_LIST lists configurations for traditional agents of different levels, and LLM_CONFIG_LIST lists configurations for large model-based agents.

9. demo_test/: Contains some test cases for testing the API, game bots, etc.

10. Obtain traditional agent baselines: https://github.com/AMysteriousBeing/BotzoneBench/releases/tag/BaselineBots. Extract the files into the botzone/online/bot directory.

## Path Mapping (Important)
During gameplay, Botzone-ALE copies the locally specified file directory to the /data directory in the Docker environment. The currently specified directory is: api_config. Therefore, files in the api_config directory will be accessible within the Docker environment, where their path will be /data/xxx.
For example, the path api_config/conf.py in the development environment becomes /data/conf.py in the Docker environment. Hence, the statement referencing conf.py in llm_bot.py should be: from data.conf import ....

In bot_info.py, the directory specified in the userfile_path parameter under the game name in LLM_CONFIG_LIST is currently set to api_config.

## Running Evaluation (using evaluate_single_round as an example)
1. Give a nickname to the model you have chosen, e.g., my_Qwen3-8B, and fill it into the online_llms and llm2config dictionaries in evaluate_xxx.py. In the online_llms dictionary, the key is the model nickname, and the value is the model name. In the llm2config dictionary, the key is the model nickname, and the value is the model configuration ("silicon_flow" -> api_config/silicon_flow_conf.json, "local_vllm" -> api_config/local_vllm_conf.json).
Of course, if you do not need to change the API frequently, you can hardcode the api_base and api_key directly into the agent file (local_bots/mahjong/llm_bot.py).

2. Modify bot_lvl to select the opponent: "lv0"-"lv4". Opponent information can be referenced in bot_info.py.

3. Run the evaluation: python evaluate_single_round.py.

4. (Optional) Enable or disable game rendering by modifying env.render() in the code; specify the game log output directory by modifying game_log_output_dir (or set it to None to disable this feature); enable or disable agent action display by modifying show_action.