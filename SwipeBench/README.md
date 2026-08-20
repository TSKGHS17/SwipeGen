# SwipeBench

**SwipeBench** is the first benchmark specifically designed to evaluate the fine-grained swipe execution capabilities of GUI agents in mobile environments.

## 📊 Dataset Overview

To prevent data leakage from large-scale VLM pre-training corpora, SwipeBench is strictly constructed under an **Out-of-Distribution (OOD)** principle. 
*   **Source**: Collected from 16 newly released or significantly updated mobile applications (e.g., *Character AI, Bluesky, Perplexity, etc.*).
*   **Size**: 352 high-quality, human-like swipe interaction instances.
*   **Modality**: Multimodal (contains visual UI screenshots, 4D swipe parameters, and natural language instructions).

## 📂 Directory Structure

```text
SwipeBench/
├── screenshots/               # Contains the UI screenshots before the swipe interaction
│   ├── ai.character.app_page_0_swipe_0.png
│   └── ...
├── swipe.json                 # The main dataset file containing all annotations
└── README.md                  # This document
```

## 📝 Data Format (`swipe.json`)

All swipe interactions are unified into a four-dimensional parameter space: `start position`, `end position`, `direction`, and `duration`. 

The dataset is formatted as a JSON array. Each entry follows this schema:

```json
[
  {
    "img_filename": "ai.character.app_page_0_swipe_0.png",
    "action_data": {
      "action": "swipe",
      "bbox": [0, 112, 999, 177],
      "instruction": "swipe left to view more categories in the navigation bar",
      "start": [878.7, 144.2],
      "end": [119.4, 144.2],
      "duration": 0.3,
      "direction": "left"
    }
  }
]
```

### Field Description:
*   `img_filename`: The filename of the corresponding UI screenshot in the `screenshots/` directory.
*   `action_data`: A nested object containing the interaction details.
    *   `action`: The type of action (always `"swipe"` in this benchmark).
    *   `bbox`: The bounding box `[x1, y1, x2, y2]` of the valid scrollable region or component, normalized to `[0, 1000]`.
    *   `instruction`: The step-level natural language command describing the user's intent.
    *   `start`: Normalized starting coordinate `[x, y]` in `[0, 1000]` scale.
    *   `end`: Normalized ending coordinate `[x, y]` in `[0, 1000]` scale.
    *   `duration`: Swipe duration in seconds (e.g., `0.3`), which determines the scrolling speed and inertia.
    *   `direction`: The macro direction of the swipe (`"up"`, `"down"`, `"left"`, `"right"`).

## 🎯 Evaluation Metrics

When evaluating a GUI agent on SwipeBench, a prediction is considered a **Success** *only if* all of the following strict criteria are met simultaneously:

1.  **Start Point**: The predicted start coordinate must be within a 140-pixel Euclidean distance from the ground truth *and* must fall strictly inside the target `bbox`.
2.  **End Point**: The predicted end coordinate must be within a 140-pixel Euclidean distance from the ground truth.
3.  **Direction**: The predicted direction must exactly match the ground truth `direction`.
4.  **Duration/Speed**: The predicted duration must fall into the correct speed category (fast vs. slow) corresponding to the ground truth.

For baseline evaluation scripts, please refer to the evaluation module in our repository.

## 📜 License

The annotations in `swipe.json` are licensed under [CC BY-NC 4.0](./LICENSE.md). Application screenshots are excluded from that license; all rights in the depicted applications and third-party content remain with their respective owners. See the [SwipeBench license notice](./LICENSE.md) for details.
