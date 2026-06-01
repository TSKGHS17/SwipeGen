# SwipeGen: Android UI Automation & Dataset Synthesis

SwipeGen is an automated exploration and interaction synthesis tool designed for Android UI testing. It focuses on collecting high-quality dynamic sliding (swipe) and clicking interactions without human intervention.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

1. **Device Connection:**  
   Connect your Android device (physical smartphone or emulator) and ensure it is authorized via ADB (`adb devices`).

2. **Configuration:**  
   Specify the target Application package names in `PACKAGE_INSTALLED` in `utils/packages.py`.

   Set the `MODEL_PATH` in `vlm/vlm_server.py`.  
   We recommend using `Qwen3-VL-8B-Instruct` because this is what we used for data collection.

3. **Run Exploration & Synthesis:**

   First run a server on port 8000 (using remote VLM by default):

   ```bash
   python vlm/vlm_server.py
   ```

   Then execute the main pipeline:

   ```bash
   python explore.py
   ```
   *Note: This script executes a fully automated pipeline. Phase 1 explores the UI, Phase 2 synthesizes interactions, and Phase 3 automatically performs incremental aggregation.*

   If you want to use a local VLM instead of the remote server, please modify `Phase2SwipGen()` in `explore.py`, setting `remote_vlm=False` and providing the correct `model_path` for the local VLM. 

4. **(Optional) Manual Data Aggregation:**  
   To manually aggregate and clean the verified interaction data into a unified dataset structure (`./summary`), run:
   ```bash
   python summary.py
   ```


## Pipeline Overview

- **Phase 1 (Automated Exploration):** Rapidly explores application pages using DFS/BFS algorithms based on XML accessibility trees, building a structured state-graph of the application UI.
- **Phase 2 (Interaction Synthesis):** Leverages a Vision-Language Model (VLM) offline to identify slidable regions and generate natural language intents. It then physically replays trajectories to verify and collect valid `<Before_Image, Intent, Action, After_Image>` pairs.
