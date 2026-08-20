import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

MODELS = [
    ("Qwen2.5-VL-3B-Instruct", "/path/to/Qwen2.5-VL-3B-Instruct", 0,
     "/path/to/test_swipebench_qwen2.5_vl_3b_instruct.py", "--base_model_path"),
    ("Qwen3-VL-2B-Instruct", "/path/to/Qwen3-VL-2B-Instruct", 1,
     "/path/to/test_swipebench_qwen3_vl_2b_instruct.py", "--base_model_path"),
    ("GUI-Owl-1.5-2B-Instruct", "/path/to/GUI-Owl-1.5-2B-Instruct", 2,
     "/path/to/test_swipebench_gui_owl_1.5_2b.py", "--base_model_path"),
    ("UGround-V1-2B", "/path/to/UGround-V1-2B", 3,
     "/path/to/test_swipebench_ugound_v1_2b.py", "--base_model_path"),
    ("UI-TARS-2B-SFT", "/path/to/UI-TARS-2B-SFT", 4,
     "/path/to/test_swipebench_ui_tars_2b_sft.py", "--base_model_path"),
    ("MAI-UI-2B", "/path/to/MAI-UI-2B", 5,
     "/path/to/test_swipebench_mai_ui_2b.py", "--base_model_path"),
    ("GUISwiper-v0", "/path/to/GUISwiper", 6,
     "/path/to/test_swipebench_guiswiper.py", "--model_path"),
    ("Qwen2.5-VL-3B-UI-R1", "/path/to/Qwen2.5-VL-3B-UI-R1", 7,
     "/path/to/test_swipebench_qwen2.5_vl_3b_ui_r1.py", "--base_model_path"),
]


def main():
    parser = argparse.ArgumentParser(description="Evaluate models on SwipeBench")
    parser.add_argument("--test_json", type=str, default="/path/to/swipe_test.json")
    parser.add_argument("--image_root", type=str, default="/path/to/SwipeBench")
    parser.add_argument("--output_dir", type=str, default="/path/to/swipebench_results")
    parser.add_argument("--models", type=str, default="all")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if args.models != "all":
        selected_names = set(args.models.split(","))
        models_to_run = [(n, p, g, s, a) for n, p, g, s, a in MODELS if n in selected_names]
    else:
        models_to_run = MODELS

    print(f"Will evaluate {len(models_to_run)} models: {[m[0] for m in models_to_run]}")

    processes = []
    for model_name, model_path, gpu_id, script_path, model_arg in models_to_run:
        safe_name = model_name.replace('-', '_').replace('.', '_')
        output_file = os.path.join(args.output_dir, f"results_{safe_name}.json")

        cmd = [
            sys.executable,
            script_path,
            model_arg, model_path,
            "--test_json", args.test_json,
            "--image_root", args.image_root,
            "--output_file", output_file,
            "--device_id", str(gpu_id),
        ]

        print(f"Launching {model_name} on GPU {gpu_id}")
        log_file = open(os.path.join(args.output_dir, f"log_{safe_name}.txt"), "w")
        p = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
        processes.append((model_name, p, log_file, output_file))

    for model_name, p, log_file, output_file in processes:
        p.wait()
        log_file.close()
        print(f"{model_name} completed")

    print("\n" + "="*60)
    print("SUMMARY - All Models")
    print("="*60)
    print(f"{'Model':<30} {'Swipe':<12} {'Overall':<12}")
    print("-"*60)

    all_results = []
    for model_name, model_path, gpu_id, script_path, model_arg in models_to_run:
        safe_name = model_name.replace('-', '_').replace('.', '_')
        output_file = os.path.join(args.output_dir, f"results_{safe_name}.json")
        metrics_file = output_file.replace(".json", "_metrics.json")
        try:
            with open(metrics_file) as f:
                metrics = json.load(f)
                all_results.append({"model": model_name, "metrics": metrics})
                swipe_acc = metrics.get("swipe_accuracy", metrics.get("swipe", {}).get("acc", 0))
                overall_acc = metrics.get("overall_accuracy", metrics.get("overall", {}).get("acc", 0))
                print(f"{model_name:<30} {swipe_acc}   {overall_acc}")
        except Exception as e:
            print(f"{model_name:<30} ERROR: {e}")

    print("="*60)


    summary_file = os.path.join(args.output_dir, "summary_all_models.json")
    with open(summary_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSummary saved to: {summary_file}")


if __name__ == "__main__":
    main()
