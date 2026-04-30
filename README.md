# BotzoneBench: Anchored LLM Evaluation with Skill-Calibrated Game AI

BotzoneBench is built on top of Botzone-ALE, and it is a scalable evaluation framework for large language models (LLMs) based on anchored, skill-calibrated game AIs. It replaces traditional LLM-vs-LLM tournaments with a fixed hierarchy of non-LLM game bots, enabling linear-time evaluation, absolute performance ratings, and interpretable analysis of strategic decision-making.

## 🌟 Key Features
* **Anchored Evaluation:** Assess LLMs against fixed skill-level AI bots instead of volatile model pools

* **Diverse Game Suite:** 8 games covering perfect/imperfect information, deterministic/stochastic settings:

    * Perfect Information: Tic-Tac-Toe, Gomoku, Reversi, Ataxx, Chess

    * Imperfect Information: Texas Hold’em, Fight the Landlord, Mahjong (MCR)

* **Scalable Design:** O(N) evaluation cost (vs. O(N²) for tournaments)

* **Rich Data:** Public dataset with full game logs, reasoning traces, and annotated outcomes

* **Modular Architecture:** Supports both local evaluation and Botzone platform integration

## 📦 Installation

Clone the repository and install dependencies:

```
git clone https://github.com/yourusername/BotzoneBench.git
cd BotzoneBench
pip install -r requirements.txt
```

See Guides under `How-to Guide` folder for further installation instructions.

