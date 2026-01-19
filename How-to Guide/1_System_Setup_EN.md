## Setup Guide for BotzoneBench4LLM

### System/Environment Preparation

Pre-requisite: Windows/Linux, Git, Anaconda/Miniconda, and Docker

On **Windows**, we recommend using any WSL2 distros with **CgroupV1**; on **Linux**, we recommend using Ubuntu 22.04/24.04 LTS with **CgroupV1** for better compatibility with the tools used in this guide.

WSL installation Guide is available at: https://learn.microsoft.com/zh-cn/windows/wsl/install (CN)and https://learn.microsoft.com/en-us/windows/wsl/install (EN). We recommend using Ubuntu 22.04/24.04 LTS Distro for WSL2. 

Note: in WSL2, you can access your files under windows with: `cd /mnt/c/your-file-path` for files in C or `cd /mnt/d/your-file-path` for files in D disks.

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