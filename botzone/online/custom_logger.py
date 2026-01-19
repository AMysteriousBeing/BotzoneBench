import datetime
from pathlib import Path

class CustomLogger:
    def __init__(self, location):
        self.location = location
        path = Path(self.location)
        path.parent.mkdir(parents=True, exist_ok=True)

    def info(self, msg):
        with open(self.location, "a+") as f:
            f.write(datetime.datetime.now().strftime("%m_%d_%H_%M_%S"))
            f.write("\t")
            f.write(msg)
            f.write("\n")

    def separator(self):
        with open(self.location, "a+") as f:
            f.write("\n\n--------------------------------------------------------------------------------\n")
