# SwipeBench GUI Model Evaluation

Evaluation toolkit for multimodal large language models on mobile GUI interaction tasks (SwipeBench benchmark).

## Supported Models

- Qwen2.5-VL-3B-Instruct
- Qwen3-VL-2B-Instruct
- GUI-Owl-1.5-2B-Instruct
- UGround-V1-2B
- UI-TARS-2B-SFT
- MAI-UI-2B
- GUISwiper-v0
- Qwen2.5-VL-3B-UI-R1

## Metrics

- **Overall Accuracy**: Overall prediction accuracy
- **Swipe Accuracy**: Swipe action accuracy
- **Tap Accuracy**: Tap/click action accuracy

## Installation

```bash
pip install -r requirements.txt
```

## Data Preparation

1. Download pretrained model weights
2. Prepare SwipeBench dataset (JSON + screenshots)

## Run Evaluation

### Single Model

```bash
python test_swipebench_<model>.py \
    --base_model_path /path/to/model \
    --test_json /path/to/swipe_test.json \
    --image_root /path/to/SwipeBench \
    --output_file results.json
```

### Batch Evaluation

Evaluate all models at once using `eval_swipe_models.py`:

```bash
python eval_swipe_models.py \
    --test_json /path/to/swipe_test.json \
    --image_root /path/to/SwipeBench \
    --output_dir /path/to/results
```

Or select specific models:

```bash
python eval_swipe_models.py \
    --models Qwen2.5-VL-3B-Instruct,GUI-Owl-1.5-2B-Instruct \
    --test_json /path/to/swipe_test.json \
    --image_root /path/to/SwipeBench \
    --output_dir /path/to/results
```

## Output Files

- `*_results_<timestamp>.json`: Prediction results for each sample
- `*_metrics_<timestamp>.json`: Aggregated evaluation metrics
- `summary_all_models.json`: Combined results for all models
