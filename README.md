<div align="center">
  <h1>SwipeGen: Bridging the Execution Gap in GUI Agents via Human-like Swipe Synthesis</h1>
</div>

<div align="center">
  <a href="https://arxiv.org/abs/2601.18305"><img src="https://img.shields.io/badge/arXiv-2601.18305-b31b1b.svg" alt="arXiv"></a>
  <a href="https://dl.acm.org/doi/10.1145/3767308.3835803"><img src="https://img.shields.io/badge/ACM%20DL-10.1145%2F3767308.3835803-0085CA" alt="ACM Digital Library"></a>
</div>

<div align="center">
  <a href="https://github.com/TSKGHS17">Xuan Wang*</a>,
  <a href="https://github.com/drunksu">Siyuan Su*</a>,
  <a href="https://github.com/QuanQiuTong">Quantong Fu*</a>,
  <a href="https://github.com/Gootter12">Yongxiang Hu</a>, and
  <a href="https://cs.fudan.edu.cn/3f/a9/c25909a278441/page.htm">Yangfan Zhou</a>
</div>

<div align="center">
  <sup>*</sup> Equal contribution.
</div>

<br>

This repository contains the code, data, and model pointers for our comprehensive framework aimed at solving the "Execution Gap" in GUI agents, specifically focusing on the fine-grained control of *Swipe* interactions.

## 📖 Overview

While modern Vision-Language Models (VLMs) have significantly improved GUI understanding and component-level clicking, they still struggle with complex continuous actions like *swipe*.
Swipes require precise control over spatial coordinates, direction, and temporal dynamics (duration/speed).

To bridge this gap, we introduce a unified pipeline encompassing automated data synthesis, robust benchmarking, and reinforcement learning-based model alignment:

1. **[SwipeGen](./SwipeGen/)**: An automated, human-like swipe data synthesis pipeline that employs continuous state exploration and visual execute-and-verify mechanisms without relying on manual annotations.
2. **[SwipeBench](./SwipeBench/)**: The first dedicated benchmark for evaluating GUI agents' swipe execution capabilities, featuring high-quality, out-of-domain (OOD) multimodal data.
3. **[GUISwiper](./GUISwiper/)**: A 3B-parameter VLM fine-tuned via Reinforcement Learning with Verifiable Rewards (RLVR/GRPO), achieving a **247% relative improvement** in swipe execution accuracy over baseline models.

## 📁 Repository Structure

```text
.
├── GUISwiper/       # Links and instructions for downloading the fine-tuned GUISwiper model weights
├── SwipeBench/      # The SwipeBench dataset (swipe.json) and corresponding before/after screenshots
├── SwipeGen/        # Source code for the automated data synthesis and exploration pipeline
└── README.md        # This document
```

## 📜 License

The source code in this repository is licensed under the [Apache License 2.0](./LICENSE). The annotations in SwipeBench are available under [CC BY-NC 4.0](./SwipeBench/LICENSE.md). Application screenshots are excluded from that data license; their rights remain with the respective owners.

## 🚀 Quick Navigation

*   **To generate your own UI interaction data:** Check out the [SwipeGen Documentation](./SwipeGen/README.md).
*   **To evaluate your GUI Agent's swipe capability:** Explore [SwipeBench](./SwipeBench/README.md).
*   **To deploy or test our RL-aligned model:** See the [GUISwiper Model Page](./GUISwiper/).

## 🧑 Team introduction

SwipeGen is developed by [Prof. Yangfan Zhou's team](https://www.y-droid.com/yz/) at Fudan University. Our team has long been dedicated to GUI agents, intelligent GUI testing, and automated mobile-app interaction.
If you are interested, please also check out our other work in the GUI domain: **[TestWeaver](https://ieeexplore.ieee.org/document/11334344)** and **[AUITestAgent](https://arxiv.org/abs/2407.09018)**.

## 📝 Citation

If you find this work useful, please cite our paper:

```bibtex
@inproceedings{wang2026swipegen,
  title     = {SwipeGen: Bridging the Execution Gap in GUI Agents via Human-like Swipe Synthesis},
  author    = {Xuan Wang and Siyuan Su and Quantong Fu and Yongxiang Hu and Yangfan Zhou},
  year      = {2026},
  month     = nov,
  booktitle = {Proceedings of the 34th ACM International Conference on Multimedia (MM'26)},
  publisher = {ACM},
  doi       = {10.1145/3767308.3835803},
  url       = {https://doi.org/10.1145/3767308.3835803}
}
```
