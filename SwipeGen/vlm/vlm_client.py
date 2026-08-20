import requests
import base64
import json
import os
from pathlib import Path
from vlm.prompts import (
    REGION_TASK_PROMPT, REGION_EXAMPLE_ASSISTANT,
    COMPONENT_TASK_PROMPT, COMPONENT_EXAMPLE_PROMPT, COMPONENT_EXAMPLE_ASSISTANT
)

class VLMClient:
    def __init__(self, server_url="http://localhost:8000", screen_size=(1080, 2400)):
        self.server_url = server_url.rstrip("/")
        self.screen_size = screen_size
        
        # Preload One-Shot example images (fallback to zero-shot without errors if missing)
        self.ex_region_b64 = None
        self.ex_comp_b64 = None
        
        ex_region_path = "examples/example_region.png"
        ex_comp_path = "examples/example_component.png"
        
        if os.path.exists(ex_region_path):
            self.ex_region_b64 = self._encode_image(ex_region_path)
        if os.path.exists(ex_comp_path):
            self.ex_comp_b64 = self._encode_image(ex_comp_path)

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def analyze_slidable_regions(self, image_path: str) -> list:
        """Send screenshot to remote VLM to retrieve slidable large regions"""
        payload = {
            "target_image_base64": self._encode_image(image_path),
            "target_user_prompt": REGION_TASK_PROMPT
        }
        
        if self.ex_region_b64:
            payload["example_image_base64"] = self.ex_region_b64
            payload["example_user_prompt"] = REGION_TASK_PROMPT
            payload["example_assistant_reply"] = REGION_EXAMPLE_ASSISTANT

        try:
            print(f"  [VLM Client] Analyzing visual regions (One-Shot): {Path(image_path).name} ...")
            resp = requests.post(f"{self.server_url}/infer", json=payload, timeout=120)
            resp.raise_for_status()
            response_text = resp.json()["text"]
            
            # You can print(response_text) here to observe the <think> process
            return self._parse_json_response(response_text)
        except Exception as e:
            print(f"  [VLM Client] Region inference request failed: {e}")
            return[]

    def generate_intent_for_xml_component(self, image_path: str, bbox: list, direction: str, context_text: str) -> str:
        """Generate intent for scrollable components extracted from XML"""
        w, h = self.screen_size
        norm_bbox =[
            int(bbox[0]/w*1000), int(bbox[1]/h*1000), 
            int(bbox[2]/w*1000), int(bbox[3]/h*1000)
        ]
        
        target_prompt = COMPONENT_TASK_PROMPT.format(norm_bbox, direction, context_text)
        
        payload = {
            "target_image_base64": self._encode_image(image_path),
            "target_user_prompt": target_prompt
        }
        
        if self.ex_comp_b64:
            payload["example_image_base64"] = self.ex_comp_b64
            payload["example_user_prompt"] = COMPONENT_EXAMPLE_PROMPT
            payload["example_assistant_reply"] = COMPONENT_EXAMPLE_ASSISTANT

        try:
            resp = requests.post(f"{self.server_url}/infer", json=payload, timeout=60)
            resp.raise_for_status()
            
            response_text = resp.json()["text"].strip()
            
            # Strip the <think> tags, retaining only the final pure instruction
            if "</think>" in response_text:
                return response_text.split("</think>")[-1].strip()
            return response_text
        except Exception as e:
            print(f"[VLM Client] Failed to generate intent: {e}")
            return f"Swipe {direction} on this component"

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
            print(f"[VLM Client] JSON parsing failed: {e}")
            return
        

    def generate_intent_for_click(self, image_path: str, bbox: list, context_text: str) -> str:
        """Request a natural language intent remotely for offline-saved click operations"""
        w, h = self.screen_size
        norm_bbox =[
            int(bbox[0] / w * 1000), int(bbox[1] / h * 1000),
            int(bbox[2] / w * 1000), int(bbox[3] / h * 1000)
        ]
        
        from vlm.prompts import CLICK_TASK_PROMPT, CLICK_EXAMPLE_PROMPT, CLICK_EXAMPLE_ASSISTANT
        target_prompt = CLICK_TASK_PROMPT.format(norm_bbox, context_text)
        
        payload = {
            "target_image_base64": self._encode_image(image_path),
            "target_user_prompt": target_prompt
        }
        
        # Reuse the component's example image as the one-shot example for clicks
        if self.ex_comp_b64:
            payload["example_image_base64"] = self.ex_comp_b64
            payload["example_user_prompt"] = CLICK_EXAMPLE_PROMPT
            payload["example_assistant_reply"] = CLICK_EXAMPLE_ASSISTANT

        try:
            resp = requests.post(f"{self.server_url}/infer", json=payload, timeout=60)
            resp.raise_for_status()
            response_text = resp.json()["text"].strip()
            
            if "</think>" in response_text:
                return response_text.split("</think>")[-1].strip()
            return response_text
        except Exception as e:
            print(f"[VLM Client] Failed to generate intent: {e}")
            return f"Tap on the component '{context_text}'"