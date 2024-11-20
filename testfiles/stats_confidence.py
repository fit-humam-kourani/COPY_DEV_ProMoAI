import os
import json
import numpy as np

TARGET_MODEL = "gpt-4o-mini"
X_CATEGORY = "n_iterations"

TARGET_MODEL = TARGET_MODEL.strip().replace("/", "").replace(":", "").strip()

rrr = {}

for file in os.listdir("results"):
    if file.startswith("gpt-4o-mini"):
        contents = json.load(open(os.path.join("results", file), "r"))

        grading = contents["self_grading"]
        x_value = contents[X_CATEGORY]

        if x_value not in rrr:
            rrr[x_value] = []

        rrr[x_value].append(grading)

for x_value in rrr:
    rrr[x_value] = float(np.mean(rrr[x_value]))

rrr = [(x, y) for x, y in rrr.items()]
rrr.sort(key=lambda z: (z[0], z[1]))

print(rrr)
