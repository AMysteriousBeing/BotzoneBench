## Guidelines for Implementing Card Games with LLM Agents

To optimize interactions with LLM agents, we should design game states to approximate the Markov property as closely as possible. This allows the system to rely primarily on the current state of the game, without needing to retain the entire conversation or action history. When this property holds, LLM agents can be prompted effectively using only the information available in the present game state.

Therefore, to support accurate and efficient decision-making by LLM agents, each game state should incorporate comprehensive and relevant information. Specifically, the following elements are essential:
* **Player’s action history**: a record of moves made so far in the game.
* **The Collection of Remaining unknown cards**: calculated as: Total cards − (agents’ cards in hand) − (already played cards)

Note: This guide is for card games only, as board games natually possess Markov property. 