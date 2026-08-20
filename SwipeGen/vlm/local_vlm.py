import torch
import json
import os
from PIL import Image
from pathlib import Path
from transformers import AutoModelForImageTextToText, AutoProcessor

from vlm.prompts import (
    REGION_TASK_PROMPT, REGION_EXAMPLE_ASSISTANT,
    COMPONENT_TASK_PROMPT, COMPONENT_EXAMPLE_PROMPT, COMPONENT_EXAMPLE_ASSISTANT,
    CLICK_TASK_PROMPT, CLICK_EXAMPLE_PROMPT, CLICK_EXAMPLE_ASSISTANT
)

class LocalVLMClient:
    def __init__(self, model_path=r"", screen_size=(1080, 2400)):
        """Initialize and load the local VL model"""
        print(f"  [LocalVLM] Loading local model: {model_path} ...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.screen_size = screen_size

        self.model = AutoModelForImageTextToText.from_pretrained(
            model_path,
            dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )
        self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
        self.model.eval()
        
        # Preload One-Shot example images (fallback to zero-shot if missing)
        self.ex_region_img = None
        self.ex_comp_img = None
        
        ex_region_path = "examples/example_region.png"
        ex_comp_path = "examples/example_component.png"
        
        if os.path.exists(ex_region_path):
            self.ex_region_img = Image.open(ex_region_path).convert("RGB")
        if os.path.exists(ex_comp_path):
            self.ex_comp_img = Image.open(ex_comp_path).convert("RGB")
            
        print(f"  [LocalVLM] Model loaded successfully!")

    def _generate_text(self, target_image: Image.Image, target_prompt: str, 
                       ex_image: Image.Image = None, ex_user_prompt: str = "", 
                       ex_assistant_reply: str = "", max_tokens: int = 2048) -> str:
        """Core Inference Engine: Assemble multi-turn dialogue and execute local inference"""
        messages =[]
        
        # 1. Construct One-Shot historical dialogue
        if ex_image is not None:
            messages.append({
                "role": "user",
                "content":[
                    {"type": "image", "image": ex_image},
                    {"type": "text", "text": ex_user_prompt}
                ]
            })
            messages.append({
                "role": "assistant",
                "content": ex_assistant_reply
            })
            
        # 2. Construct the prompt for the current target
        final_target_prompt = target_prompt
        if ex_image is not None:
            final_target_prompt = f"Now please analyze the current screenshot based on the standards above.\n\n{target_prompt}"

        messages.append({
            "role": "user",
            "content":[
                {"type": "image", "image": target_image},
                {"type": "text", "text": final_target_prompt}
            ]
        })
        
        # 3. Template rendering and tensor conversion
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        images = [img["image"] for msg in messages for img in msg["content"] if img["type"] == "image"]
        inputs = self.processor(text=[text], images=images, return_tensors="pt", padding=True).to(self.device)
        
        # 4. Execute inference
        with torch.no_grad():
            output_ids = self.model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False)
            
        gen_ids = output_ids[:, inputs.input_ids.shape[1]:]
        result_text = self.processor.batch_decode(gen_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        
        return result_text

    def analyze_slidable_regions(self, image_path: str) -> list:
        """Visual analysis: specifically identify large slidable regions"""
        try:
            print(f"  [LocalVLM] Analyzing visual regions (One-Shot): {Path(image_path).name} ...")
            target_image = Image.open(image_path).convert("RGB")
            
            response_text = self._generate_text(
                target_image=target_image,
                target_prompt=REGION_TASK_PROMPT,
                ex_image=self.ex_region_img,
                ex_user_prompt=REGION_TASK_PROMPT,
                ex_assistant_reply=REGION_EXAMPLE_ASSISTANT,
                max_tokens=2048
            )
            return self._parse_json_response(response_text)
        except Exception as e:
            print(f"  [LocalVLM] Region inference error: {e}")
            return[]

    def generate_intent_for_xml_component(self, image_path: str, bbox: list, direction: str, context_text: str) -> str:
        """Generate intent for scrollable components extracted from XML"""
        try:
            w, h = self.screen_size
            norm_bbox = [
                int(bbox[0]/w*1000), int(bbox[1]/h*1000),
                int(bbox[2]/w*1000), int(bbox[3]/h*1000)
            ]
            
            target_prompt = COMPONENT_TASK_PROMPT.format(norm_bbox, direction, context_text)
            target_image = Image.open(image_path).convert("RGB")
            
            response_text = self._generate_text(
                target_image=target_image,
                target_prompt=target_prompt,
                ex_image=self.ex_comp_img,
                ex_user_prompt=COMPONENT_EXAMPLE_PROMPT,
                ex_assistant_reply=COMPONENT_EXAMPLE_ASSISTANT,
                max_tokens=512
            )
            
            response_text = response_text.strip()
            if "</think>" in response_text:
                return response_text.split("</think>")[-1].strip()
            return response_text
        except Exception as e:
            print(f"  [LocalVLM] Failed to generate intent: {e}")
            return f"Swipe {direction} on this component"

    def generate_intent_for_click(self, image_path: str, bbox: list, context_text: str) -> str:
        """Generate intent for click operations"""
        try:
            w, h = self.screen_size
            norm_bbox = [
                int(bbox[0]/w*1000), int(bbox[1]/h*1000),
                int(bbox[2]/w*1000), int(bbox[3]/h*1000)
            ]
            
            target_prompt = CLICK_TASK_PROMPT.format(norm_bbox, context_text)
            target_image = Image.open(image_path).convert("RGB")
            
            # Reuse the component's example image for click intent (as it also demonstrates Bbox comprehension)
            response_text = self._generate_text(
                target_image=target_image,
                target_prompt=target_prompt,
                ex_image=self.ex_comp_img,
                ex_user_prompt=CLICK_EXAMPLE_PROMPT,
                ex_assistant_reply=CLICK_EXAMPLE_ASSISTANT,
                max_tokens=512
            )
            
            response_text = response_text.strip()
            if "</think>" in response_text:
                return response_text.split("</think>")[-1].strip()
            return response_text
        except Exception as e:
            print(f"  [LocalVLM] Failed to generate intent: {e}")
            return f"Tap on the component '{context_text}'"

    def _parse_json_response(self, text: str) -> list:
        start = text.find('[')
        end = text.rfind(']') + 1
        if start == -1 or end == 0:
            return[]
        
        json_str = text[start:end]
        try:
            regions = json.loads(json_str)
            valid_regions =[]
            for r in regions:
                if 'bbox' in r and len(r['bbox']) == 4:
                    valid_regions.append(r)
            return valid_regions
        except Exception as e:
            print(f"[LocalVLM] JSON parsing failed: {e}")
            return