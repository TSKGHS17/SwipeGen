import base64
import io
import torch
from PIL import Image
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModelForImageTextToText, AutoProcessor
import json
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "inference_log.jsonl"

MODEL_PATH = "" # Fill in your model path here, e.g., "/home/user/models/Qwen3-VL-8B-Instruct"
MAX_NEW_TOKENS = 2048 

print("Loading model...")
model = AutoModelForImageTextToText.from_pretrained(
    MODEL_PATH,
    dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)
processor = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True)
model.eval()
print("Model loaded.")

app = FastAPI(title="Remote VLM Inference Server")

class InferRequest(BaseModel):
    target_image_base64: str
    target_user_prompt: str
    # One-Shot example parameters (optional)
    example_image_base64: str = None
    example_user_prompt: str = ""
    example_assistant_reply: str = ""

@app.post("/infer")
def infer(req: InferRequest):
    print("Received inference request.")
    try:
        # 1. Parse the target image
        tg_bytes = base64.b64decode(req.target_image_base64)
        tg_image = Image.open(io.BytesIO(tg_bytes)).convert("RGB")
        
        messages =[]
        
        # 2. If a One-Shot example is provided, construct a two-turn dialogue first
        if req.example_image_base64:
            ex_bytes = base64.b64decode(req.example_image_base64)
            ex_image = Image.open(io.BytesIO(ex_bytes)).convert("RGB")
            
            # Turn 1: Example prompt
            messages.append({
                "role": "user",
                "content":[
                    {"type": "image", "image": ex_image},
                    {"type": "text", "text": req.example_user_prompt}
                ]
            })
            # Turn 2: Example response
            messages.append({
                "role": "assistant",
                "content": req.example_assistant_reply
            })
            
        # 3. Construct the actual target prompt
        target_text = req.target_user_prompt
        if req.example_image_base64:
            target_text = f"Now please analyze the current screenshot based on the standards above.\n\n{req.target_user_prompt}"

        messages.append({
            "role": "user",
            "content":[
                {"type": "image", "image": tg_image},
                {"type": "text", "text": target_text}
            ]
        })

        # 4. Model inference
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        # Extract all provided images
        images = [img["image"] for msg in messages for img in msg["content"] if img["type"] == "image"]

        inputs = processor(text=[text], images=images, return_tensors="pt", padding=True).to(model.device)

        with torch.no_grad():
            output_ids = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)

        gen_ids = output_ids[:, inputs.input_ids.shape[1]:]
        result_text = processor.batch_decode(gen_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

        return {"text": result_text}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# You can also start the server with a command like: uvicorn remote_server:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    print("Starting Uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)