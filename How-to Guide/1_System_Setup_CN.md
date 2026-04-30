## BotzoneBench4LLM 系统安装指南

### 系统/环境准备

前提条件：Windows/Linux 系统、Git、Anaconda/Miniconda 和 Docker。

在 **Windows** 上，我们建议使用基于CgroupV1的任何Linux WSL2发行版；在 **Linux** 上，我们建议使用基于CgroupV1的 Ubuntu 22.04/24.04 LTS，以获得与本指南所用工具更好的兼容性。

WSL 安装指南位于：https://learn.microsoft.com/zh-cn/windows/wsl/install (中文) 和 https://learn.microsoft.com/en-us/windows/wsl/install (英文)。我们建议在 WSL2 中使用 Ubuntu 22.04/24.04 LTS 发行版。

注意：在 WSL2 中，可以通过以下方式访问 Windows 下的文件：对于 C 盘文件使用 `cd /mnt/c/你的文件路径`，对于 D 盘文件使用 `cd /mnt/d/你的文件路径`。

使用命令 `mount | grep cgroup` 查看 Cgroup 版本. 如果默认版本为2, 可以通过下载并安装 https://github.com/microsoft/WSL/releases/tag/2.2.4 内核以获得**CgroupV1**.

Anaconda/Miniconda 可以通过以下链接安装：https://www.anaconda.com/download

Ubuntu 上的 Docker 可以通过以下链接安装：https://docs.docker.com/engine/install/ubuntu/


### Python 环境准备
1. 为项目创建一个新的 conda 环境：`conda create -n 你的环境名 python=3.10`

2. 激活环境：`conda activate 你的环境名`

3. 使用 pip 安装所需的包：`pip install -r requirements.txt`

4. 安装 NodeJS 和 npm：`pip install nodejs npm openai`

### Docker 镜像设置
1. 从Docker hub拉取镜像: botzone/env-ale:latest

2. (可选)通过链接下载：https://disk.pku.edu.cn/link/AA7DDF13A95EBA4D41A04891181F9D1CBE，解压并使用 Docker 加载镜像：`docker load -i 你的/路径/to/bz_updated.tar`

3. 将你自己添加到拥有 Docker 守护进程的组中（通常是 docker）：`sudo usermod -aG docker $USER`

4. 输入 docker images 或 docker image list 验证镜像，并确认其 ID 为：8316c0d846a7。

5. 定位到目录中的 demo.py 文件。

6. 运行脚本以确定镜像正常运行：`python demo.py`，如果脚本运行成功，可以在终端看到类似以下的输出：
┌─────────────────────┐
│   A B C    Round: 0 │
│ 1          Next: O  │
│ 2                   │
│ 3                   │
└─────────────────────┘

## 远程大模型API服务

如果使用远程大模型的API服务进行开发，我们建议使用SiliconFlow的Qwen3-8B进行开发，因为它满足最低的推理需求，而且免费。后续可以自行探索其他平台或者其它大模型版本的API服务，以获得更好的性能。

1. 注册SiliconFlow账号：https://www.siliconflow.cn/
2. 获得API密钥：在SiliconFlow账号主页中，点击“API密钥”，新建API密钥，即可获得API密钥。
3. 配置API密钥：在 `api_config/silicon_flow_conf.json` 文件中，将 `your-key` 替换为你获得的API密钥。
4. 记住你选用的模型名：模型名可以在模型广场，点开任意模型后，在每个模型名后有一个复制按钮，点击后即可复制模型名。

## 本地开发/本地大模型设置（优先考虑远程API）
以下指南仅用于本地开发时的大模型配置。请在 VLLM 和 Ollama 中任选一个，建议使用Ollama，因为Ollama占用资源较少。如果使用远程LLM API 服务（建议），可以跳过以下指南。

### Ollama 设置

1. 安装 Ollama：`curl -fsSL https://ollama.com/install.sh | sh`

2. 拉取模型并测试速度：`ollama run qwen3:4b-instruct-2507-q4_K_M --verbose`

3. 修改网络配置以便 Docker 可以访问 Ollama：`sudo nano /etc/systemd/system/ollama.service`

4. 在 `ollama.service` 文件中，添加以下行：`Environment="OLLAMA_HOST=0.0.0.0:11434"`，然后保存并关闭文件。

5. 重启 Ollama 服务：
```
sudo systemctl daemon-reload
sudo systemctl restart ollama.service
```

6. 更改Ollama的上下文长度设置: 
```
ollama show --modelfile qwen3:4b-instruct-2507-q4_K_M > Modelfile
nano Modelfile
```
    - 在 Modelfile里, 添加或者更改这一行: `PARAMETER num_ctx 4096`

7. 导出并生成新的模型文件: `ollama create qwen3:4b-15360 -f Modelfile`

8. 将 `test_api.py` 文件中的第 20 行和第 27 行改为您部署的 IP 地址和模型路径/名称。

9. 验证本地 LLM 正在运行并响应：`python path-to-file/test_api.py`

### VLLM 设置
1. 确保你位于 conda 环境中：`conda activate 你的环境名`

2. 安装 vllm 和 modelscope：`pip install vllm modelscope`

3. 在终端会话中，下载模型：

```
export MODELSCOPE_CACHE=/你的/自定义/缓存/路径
modelscope download Eslzzyl/Qwen3-4B-Instruct-2507-AWQ
```

4. 修改 start_vllm.sh 中的模型路径，并运行它来启动本地 llm 服务：文件路径/start_vllm.sh。

5. 将 `test_api.py` 文件中的第 20 行和第 27 行改为你部署的 IP 和模型路径/名称。

6. 验证本地 llm 是否正在运行并响应：`python 文件路径/test_api.py`

### 配置本地大模型API服务

1. 获取本地vllm服务地址：`http://localhost:xxx`, 其中，OLLAMA一般为 `11434`，VLLM一般为 `8000`。
2. 获取本地部署的模型名称，可以通过在浏览器输入`http://localhost:xxx/v1/models`查看，模型名稍后会用到
3. 新建 `api_config/local_vllm_conf.json` 文件并添加以下内容：
```
{
    "api_base": "http://localhost:11434/v1/chat/completions", （你的本地llm服务地址，与你使用VLLM或者Ollama有关）
    "api_key": "your-key" （你的本地llm服务密钥，一般可以随意填写）
}
```

## 代码仓库内容

1. api_config/: 包含本地大模型API服务的配置文件。
2. botzone/: 包含游戏环境的代码(一般不用管)。
3. local_bots/: 包含本地开发的AI智能体代码，每个游戏文件夹下，sample.py为随机动作智能体，llm_bot.py为基于大模型的智能体。
4. demo.py: 用于检测botzone-ALE docker环境是否正常运行。
5. evaluate_single_round.py: 针对麻将游戏用于评估基于大模型的智能体与传统智能体的性能。
5. evaluate_single_game.py: 用于批量比较基于大模型的智能体与传统智能体的性能。如果使用远程API服务，需要注意使用的API可用性，设置过高的parallel_ct可能导致API调用失败，进而无法完成评测。国内大模型API可以设置8-16， 国外大模型API建议设置为4-8。
6. evaluate_tournament.py: 用于评估基于大模型的智能体之间的性能。
7. bot_info.py: 包含游戏环境的智能体配置, 其中Lvx_CONFIG_LIST为不同等级的传统智能体配置， LLM_CONFIG_LIST为基于大模型的智能体配置。
8. demo_test/: 包含一些测试用例，用于测试api, 游戏bot等。
9. 获取传统智能体baseline: https://github.com/AMysteriousBeing/BotzoneBench/releases/tag/BaselineBots，将文件解压缩放到`botzone/online/bot`目录下。

## 路径映射 （**重要**）

进行游戏时，Botzone-ALE会将本地指定的文件目录拷贝到docker环境中的/data目录下，当前指定的目录为：`api_config`。因此，`api_config`目录下的文件会在docker环境中被访问到，而在docker环境中的地址为/data/xxx。
例如，开发环境中`api_config/conf.py`在docker环境中的地址为`/data/conf.py`，因此llm_bot.py中引用conf.py的语句为：`from data.conf import ...`。

在bot_info.py的LLM_CONFIG_LIST的**游戏名**下的`userfile_path`参数中指定的目录，目前设置为`api_config`。

## 运行评测（以evaluate_single_round为示例）

1. 将你所选用的模型取一个昵称，例如`my_Qwen3-8B`，填入evaluate_xxx.py中的online_llms和llm2config字典中。其中，online_llms字典中键为模型昵称，值为模型名，llm2config字典中键为模型昵称，值为模型配置（"silicon_flow"->api_config/silicon_flow_conf.json, "local_vllm"->api_config/local_vllm_conf.json）。
当然，如果不需要频繁更换API，可以将api_base和api_key直接写死在智能体文件中（local_bots/mahjong/llm_bot.py）。
2. 修改bot_lvl以选择对手："lv0"-"lv4"，对手信息可以参考bot_info.py。
3. 运行评测：`python evaluate_single_round.py`。
4. （可选）通过修改代码中的`env.render()`来开启或关闭游戏渲染；通过修改game_log_output_dir，来指定游戏日志输出目录（或者设为None关闭这个功能）；通过修改show_action，来开启或关闭智能体的动作显示。