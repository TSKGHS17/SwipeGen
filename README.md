# SwipeGen: Bridging the Execution Gap in GUI Agents via Human-like Swipe Synthesis

Welcome to the official repository for our paper: **"SwipeGen: Bridging the Execution Gap in GUI Agents via Human-like Swipe Synthesis"**.

This repository contains the code, data, and model pointers for our comprehensive framework aimed at solving the "Execution Gap" in GUI agents, specifically focusing on the fine-grained control of **Swipe** interactions.

## 📖 Overview

While modern Vision-Language Models (VLMs) have significantly improved GUI understanding and component-level clicking, they still struggle with complex continuous actions like swiping. Swipes require precise control over spatial coordinates, direction, and temporal dynamics (duration/speed). 

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

## 🚀 Quick Navigation

*   **To generate your own UI interaction data:** Check out the [SwipeGen Documentation](./SwipeGen/README.md).
*   **To evaluate your GUI Agent's swipe capability:** Explore [SwipeBench](./SwipeBench/README.md).
*   **To deploy or test our RL-aligned model:** See the [GUISwiper Model Page](./GUISwiper/).

## 📝 Citation
*(To be updated after the anonymity period)*
