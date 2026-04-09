import argparse
import json
import os
import re
import torch
from datetime import datetime
from tqdm import tqdm
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

SYSTEM_PROMPT = (
    'You are a GUI interaction assistant. Given a screenshot and instruction, output ONLY a valid JSON object with no additional text.\n'
    'Examples:\n'
    'Input: A page with a swipeable list. Instruction: "Swipe up to see more"\n'
    'Output: {"action": "swipe", "start": [500, 850], "end": [500, 200], "direction": "up", "duration": 300}\n'
    'Input: A button at top-right. Instruction: "Tap the settings button"\n'
    'Output: {"action": "tap", "start": [900, 50], "end": null, "direction": null, "duration": 0}\n'
    'Input: A scrollable feed. Instruction: "Swipe down to refresh"\n'
    'Output: {"action": "swipe", "start": [500, 200], "end": [500, 800], "direction": "down", "duration": 300}\n'
    'IMPORTANT: Output ONLY the JSON object, no markdown, no explanation. Coordinates are in pixel range [0, 1000].\n'
    'For swipe actions, direction must be one of: "up", "down", "left", "right".\n'
)


def extract_prediction(response_text):

    response_text = response_text.replace("<|im_end|>", "").replace("<|im_sep|>", "").strip()


    if response_text.startswith("```"):
        response_text = re.sub(r"^```json\s*", "", response_text, flags=re.MULTILINE)
        response_text = re.sub(r"^```\s*$", "", response_text, flags=re.MULTILINE)
        response_text = response_text.strip()

    try:
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            j = json.loads(match.group())
        else:
            return None, None, None, None

        action = j.get("action")
        if action == "click":
            action = "tap"
        if action == "terminate":
            action = None

        if action not in {"tap", "swipe", "long_press", "text", "type"}:
            action = None


        start = j.get("start") or j.get("point") or j.get("coordinate") or j.get("coord")
        end = j.get("end") or j.get("coordinate2") or j.get("coord2")
        direction = j.get("direction")


        if action == "swipe" and direction is None and start and end:
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            abs_dx = abs(dx)
            abs_dy = abs(dy)
            if abs_dy > abs_dx:
                direction = "down" if dy > 0 else "up"
            else:
                direction = "right" if dx > 0 else "left"

        return action, start, end, direction
    except Exception as e:
        print(f"Failed to parse response: {e}")
        return None, None, None, None


def point_in_bbox(x, y, bbox):

    x1, y1, x2, y2 = bbox
    return x1 <= x <= x2 and y1 <= y <= y2


def judge_direction(start, end, gt_dir):

    if not start or not end:
        return False
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    abs_dx = abs(dx)
    abs_dy = abs(dy)

    if gt_dir == "up":
        return abs_dy > abs_dx and dy < 0
    if gt_dir == "down":
        return abs_dy > abs_dx and dy > 0
    if gt_dir == "left":
        return abs_dx > abs_dy and dx < 0
    if gt_dir == "right":
        return abs_dx > abs_dy and dx > 0
    return False


def evaluate_sample(pred_action, pred_start, pred_end, gt_action, gt_bbox, gt_direction):


    if pred_start and isinstance(pred_start, list) and len(pred_start) == 2:
        pred_start = [max(0, min(1000, pred_start[0])), max(0, min(1000, pred_start[1]))]
    if pred_end and isinstance(pred_end, list) and len(pred_end) == 2:
        pred_end = [max(0, min(1000, pred_end[0])), max(0, min(1000, pred_end[1]))]

    if gt_action == "tap":
        if pred_action != "tap":
            return False

        return True

    elif gt_action == "swipe":
        if pred_action != "swipe":
            return False

        if not judge_direction(pred_start, pred_end, gt_direction):
            return False
        return True

    return False


def run_inference(model_path, test_json, image_root, output_file, device_id=0):

    print(f"Loading model from {model_path}...")
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_path, torch_dtype=torch.bfloat16, device_map="cpu"
    )
    processor = AutoProcessor.from_pretrained(model_path)
    device = torch.device(f"cuda:{device_id}" if torch.cuda.is_available() else "cpu")
    model = model.to(device).eval()

    with open(test_json, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    print(f"Running inference on {len(test_data)} samples...")
    results = []

    for item in tqdm(test_data):
        img_filename = item.get("img_filename")
        if not img_filename:
            continue

        gt_action = item.get("action_data", {}).get("action")
        gt_bbox = item.get("action_data", {}).get("bbox")
        gt_start = item.get("action_data", {}).get("start")
        gt_end = item.get("action_data", {}).get("end")
        gt_direction = item.get("action_data", {}).get("direction")
        gt_success = item.get("action_data", {}).get("success")
        instruction = item.get("action_data", {}).get("instruction", "")

        image_path = os.path.join(image_root, img_filename)
        if not os.path.exists(image_path):
            print(f"[WARN] Image not found: {image_path}")
            continue

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [{"type": "image", "image": image_path}, {"type": "text", "text": instruction}]}
        ]

        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[text], images=[image_path], return_tensors="pt").to(device)

        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=256)

        response = processor.batch_decode(output[:, inputs.input_ids.shape[1]:])[0]

        pred_action, pred_start, pred_end, pred_direction = extract_prediction(response)


        is_correct = evaluate_sample(
            pred_action, pred_start, pred_end,
            gt_action, gt_bbox, gt_direction
        )

        results.append({
            "img_filename": img_filename,
            "instruction": instruction,
            "gt_action": gt_action,
            "gt_bbox": gt_bbox,
            "gt_start": gt_start,
            "gt_end": gt_end,
            "gt_direction": gt_direction,
            "gt_success": gt_success,
            "pred_action": pred_action,
            "pred_start": pred_start,
            "pred_end": pred_end,
            "pred_direction": pred_direction,
            "response": response,
            "correct": is_correct
        })

    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return results


def compute_metrics(results):

    total = len(results)
    if total == 0:
        return {"error": "No results to evaluate"}

    correct = sum(1 for r in results if r.get("correct", False))
    overall_accuracy = correct / total

    swipe_samples = [r for r in results if r.get("gt_action") == "swipe"]
    swipe_total = len(swipe_samples)
    swipe_correct = sum(1 for r in swipe_samples if r.get("correct", False))
    swipe_accuracy = swipe_correct / swipe_total if swipe_total > 0 else 0

    tap_samples = [r for r in results if r.get("gt_action") == "tap"]
    tap_total = len(tap_samples)
    tap_correct = sum(1 for r in tap_samples if r.get("correct", False))
    tap_accuracy = tap_correct / tap_total if tap_total > 0 else 0

    metrics = {
        "overall_accuracy": round(overall_accuracy, 4),
        "overall_correct": correct,
        "overall_total": total,
        "swipe_accuracy": round(swipe_accuracy, 4),
        "swipe_correct": swipe_correct,
        "swipe_total": swipe_total,
        "tap_accuracy": round(tap_accuracy, 4),
        "tap_correct": tap_correct,
        "tap_total": tap_total,
    }

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Evaluate Qwen3-VL-2B-Instruct on SwipeBench")
    parser.add_argument("--base_model_path", type=str,
                        default="/path/to/Qwen3-VL-2B-Instruct",
                        help="Path to Qwen3-VL-2B-Instruct model")
    parser.add_argument("--test_json", type=str,
                        default="/path/to/SwipeBench/all_apps_summary_SwipeBench.json",
                        help="Path to SwipeBench test JSON")
    parser.add_argument("--image_root", type=str,
                        default="/path/to/SwipeBench",
                        help="Root directory containing SwipeBench images")
    parser.add_argument("--output_file", type=str,
                        default="/path/to/test_swipebench_results_qwen3_vl_2b_instruct.json",
                        help="Output file for evaluation results")
    parser.add_argument("--device_id", type=int, default=0, help="GPU device ID")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base, ext = os.path.splitext(args.output_file)
    args.output_file = f"{base}_{timestamp}{ext}"

    results = run_inference(
        args.base_model_path,
        args.test_json,
        args.image_root,
        args.output_file,
        args.device_id
    )

    metrics = compute_metrics(results)

    print("\n" + "="*60)
    print("SwipeBench Evaluation Results (Qwen3-VL-2B-Instruct)")
    print("="*60)
    print(f"Overall Accuracy: {metrics['overall_correct']}/{metrics['overall_total']} = {metrics['overall_accuracy']:.2%}")
    print(f"Swipe Accuracy:   {metrics['swipe_correct']}/{metrics['swipe_total']} = {metrics['swipe_accuracy']:.2%}")
    print(f"Tap Accuracy:     {metrics['tap_correct']}/{metrics['tap_total']} = {metrics['tap_accuracy']:.2%}")
    print("="*60)
    print(f"\nResults saved to: {args.output_file}")

    metrics_file = f"{base}_metrics_{timestamp}.json"
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to: {metrics_file}")


if __name__ == "__main__":
    main()