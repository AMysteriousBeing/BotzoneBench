import requests
import json

headers = {"Authorization": f"Bearer [KEY]"}
API_URL = (
    "https://huggingface.co/api/datasets/AMysteriousBeing/BotzoneBenchDataset/croissant"
)


def query():
    response = requests.get(API_URL, headers=headers)
    return response.json()


data = query()
with open("croissant.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
