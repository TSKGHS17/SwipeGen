#!/bin/bash
pip install -q transformers huggingface_hub

python - << 'EOF'
from transformers import AutoTokenizer, AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained(
    "anonymous-uiagent-weights/GUISwiper"
)
tok = AutoTokenizer.from_pretrained("anonymous-uiagent-weights/GUISwiper")
print("Model & tokenizer loaded.")
EOF
