import json
import time
import shutil
import os
import logging
from pathlib import Path
from core.device_controller import UIAutomatorController
from utils.image_utils import calculate_image_diff

class Phase2Swiper:
    def __init__(self, package_name: str, remote_vlm=True, url="http://localhost:8000"):
        self.package = package_name
        self.controller = UIAutomatorController()
        self.screen_size = self.controller.window_size

        if remote_vlm:
            from vlm.vlm_client import VLMClient
            self.vlm = VLMClient(server_url=url, screen_size=self.screen_size)
        else:
            from vlm.local_vlm import LocalVLMClient
            self.vlm = LocalVLMClient(model_path=url, screen_size=self.screen_size)

        # Output directory for successfully verified Phase 2 dataset (App-level archiving)
        self.output_dir = Path("outputs") / f"{self.package}_dataset"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.temp_dir = Path("outputs") / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # === Breakpoint Resume Core Variables ===
        self.dataset_file = self.output_dir / "swipe_dataset.json"
        self.click_dataset_file = self.output_dir / "click_dataset.json"
        self.progress_file = self.output_dir / "phase2_progress.json"

        self.successful_swipes = []
        self.successful_clicks =[]
        self.processed_pages = set()

        self._load_resume_data()

    def _load_resume_data(self):
        """Load breakpoint resume data"""
        if self.dataset_file.exists():
            try:
                with open(self.dataset_file, 'r', encoding='utf-8') as f:
                    self.successful_swipes = json.load(f)
                logging.info(f"  -> 📦 Found existing dataset, restored {len(self.successful_swipes)} swipe records.")
            except Exception as e:
                logging.error(f"  -> ⚠️ Failed to read existing dataset: {e}")

        if self.click_dataset_file.exists():
            try:
                with open(self.click_dataset_file, 'r', encoding='utf-8') as f:
                    self.successful_clicks = json.load(f)
                logging.info(f"  -> 📦 Found existing click dataset, restored {len(self.successful_clicks)} click records.")
            except Exception as e:
                logging.error(f"  -> ⚠️ Failed to read existing click dataset: {e}")

        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    self.processed_pages = set(json.load(f))
                logging.info(f"  -> 📦 Found existing progress, automatically skipped {len(self.processed_pages)} processed pages.")
            except Exception as e:
                logging.error(f"  -> ⚠️ Failed to read progress file: {e}")

    def save_progress(self, page_id):
        """Save fully processed pages to progress file"""
        self.processed_pages.add(page_id)
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.processed_pages), f, ensure_ascii=False, indent=2)

    def load_memory(self):
        """Load Phase 1 map data"""
        memory_file = Path("outputs") / self.package / "memory_graph.json"
        if not memory_file.exists():
            raise FileNotFoundError(f"Cannot find Phase 1 map data: {memory_file}")
        with open(memory_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _synthesize_click_for_page(self, page, pages):
        """Extract VLM intent offline for the Click action navigating to this page"""
        if not page.get('trajectory'):
            return 
            
        page_id = page['page_id']
        parent_page_id = page.get('parent_page_id')
        if not parent_page_id:
            return

        # Deduplication: Skip if click data for this page exists
        if any(c.get('target_page') == page_id for c in self.successful_clicks):
            return

        parent_page = next((p for p in pages if p['page_id'] == parent_page_id), None)
        if not parent_page:
            return
            
        action = page['trajectory'][-1]
        cx, cy = action['x'], action['y']
        desc = action.get('desc', 'Unknown Component')
        physical_bbox = action.get('bbox')
        
        src_before_img = Path(parent_page['image_path'])
        src_after_img = Path(page['image_path'])
        
        if not src_before_img.exists() or not src_after_img.exists():
            return

        logging.info(f"  -> Requesting VLM intent for Click action from {parent_page_id} to {page_id}...")
        
        # Legacy data compatibility
        if not physical_bbox:
            physical_bbox =[max(0, cx-20), max(0, cy-20), cx+20, cy+20]

        instruction = self.vlm.generate_intent_for_click(str(src_before_img), physical_bbox, desc)
        logging.info(f"     [Click] Generated intent: {instruction}")
        
        # Copy original files to dataset directory for self-containment
        dest_before_name = f"{page_id}_click_before.png"
        dest_after_name = f"{page_id}_click_after.png"
        
        shutil.copy(src_before_img, self.output_dir / dest_before_name)
        shutil.copy(src_after_img, self.output_dir / dest_after_name)

        src_before_xml = src_before_img.with_suffix('.xml')
        if src_before_xml.exists():
            shutil.copy(src_before_xml, self.output_dir / f"{page_id}_click_before.xml")
        src_after_xml = src_after_img.with_suffix('.xml')
        if src_after_xml.exists():
            shutil.copy(src_after_xml, self.output_dir / f"{page_id}_click_after.xml")
        
        w, h = self.screen_size
        norm_bbox =[
            int(physical_bbox[0]/w*1000), int(physical_bbox[1]/h*1000),
            int(physical_bbox[2]/w*1000), int(physical_bbox[3]/h*1000)
        ]
        norm_x, norm_y = int(cx/w*1000), int(cy/h*1000)
        
        data_entry = {
            "img_filename": dest_before_name, 
            "target_page": page_id,
            "after_image": dest_after_name,   
            "action_data": {
                "action": "click",
                "bbox": norm_bbox,
                "start": [norm_x, norm_y], 
                "end":[norm_x, norm_y],
                "instruction": instruction,
                "description": desc
            }
        }
        
        self.successful_clicks.append(data_entry)
        self.save_dataset()

    def get_swipe_candidates(self, page_id):
        """Get swipe candidates via XML components and VLM visual regions"""
        live_img_path = str(self.temp_dir / f"live_{page_id}.png")
        self.controller.take_screenshot(live_img_path)

        all_swipe_candidates =[]

        # --- Source 1: XML Components ---
        logging.info(f"  -> Extracting live XML components from current page...")
        xml_components = self.controller.get_scrollable_elements_xml()

        if xml_components:
            logging.info(f"  -> Discovered {len(xml_components)} scrollable XML components, requesting intent commands...")
            for comp in xml_components:
                intent_cmd = self.vlm.generate_intent_for_xml_component(
                    live_img_path, comp['bounds'], comp['direction'], comp['text']
                )

                w, h = self.screen_size
                norm_bbox = [
                    int(comp['bounds'][0]/w*1000), int(comp['bounds'][1]/h*1000),
                    int(comp['bounds'][2]/w*1000), int(comp['bounds'][3]/h*1000)
                ]

                all_swipe_candidates.append({
                    "category": "component",
                    "type": "XML Component",
                    "direction": comp['direction'],
                    "bbox": norm_bbox,
                    "command": intent_cmd
                })
                logging.info(f"[Component] Generated intent: {intent_cmd}")

        # --- Source 2: VLM Visual Regions ---
        logging.info(f"  -> Calling VLM to analyze purely visual slidable regions (Regions)...")
        vlm_regions = self.vlm.analyze_slidable_regions(live_img_path)
        if vlm_regions:
            all_swipe_candidates.extend(vlm_regions)

        logging.info(f"  => Summary complete, generated {len(all_swipe_candidates)} test targets for current page.")
        return all_swipe_candidates

    def run_synthesis(self):
        logging.info(f"=== Starting Phase 2 Swipe Data Synthesis Pipeline (App: {self.package}) ===")
        pages = self.load_memory()
        logging.info(f"Loaded {len(pages)} unique pages for evaluation.")

        for page in pages:
            page_id = page['page_id']

            if page_id in self.processed_pages:
                logging.info(f"--- ⏭️ Node {page_id} already processed, skipping ---")
                continue

            trajectory = page['trajectory']

            logging.info(f"\n==================================================")
            logging.info(f"--- Processing node: {page_id} / {len(pages)} ---")

            self._synthesize_click_for_page(page, pages)

            logging.info(f"  -> Replaying trajectory to target page...")
            if not self.controller.replay_trajectory_unverified(self.package, trajectory):
                logging.error(f"  -> ❌ Exited target App during replay. Skipping this page.")
                continue

            # Ensure dynamic content loads
            self.controller.wait_for_loading_to_finish()
            time.sleep(8) 

            swipe_candidates = self.get_swipe_candidates(page_id)

            for idx, candidate in enumerate(swipe_candidates): 
                if idx > 0:
                    logging.info(f"\n    -> Resetting state, re-navigating to target page...")
                    if not self.controller.replay_trajectory_unverified(self.package, trajectory):
                        logging.error(f"  -> ❌ Exited target App during replay. Skipping this page.")
                        continue
                self.validate_swipe(idx, candidate, page_id)

            self.save_progress(page_id)
            logging.info(f"  => All swipe evaluations for node {page_id} completed, progress saved.")

        for _ in range(6):
            self.controller.d.press("back")
        logging.info(f"\n=== Phase 2 Complete! Synthesized {len(self.successful_swipes)} swipe records and {len(self.successful_clicks)} click records. ===")
        
    def validate_swipe(self, idx, candidate, page_id):
        logging.info(f"\n[Executing {idx+1}] {candidate.get('category')} | Intent: {candidate.get('command')}")

        time.sleep(8)
        self.controller.wait_for_loading_to_finish()

        # Step B: Capture before image
        before_img = str(self.output_dir / "temp_before.png")
        before_xml = str(self.output_dir / "temp_before.xml")
        self.controller.take_screenshot(before_img)

        # Step C: Execute swipe
        swipe_params = self.controller.swipe_by_normalized_bbox(
            bbox=candidate['bbox'],
            direction=candidate['direction']
        )

        # Step D: Capture after image
        self.controller.wait_for_loading_to_finish(timeout=4)
        after_img = str(self.output_dir / "temp_after.png")
        after_xml = str(self.output_dir / "temp_after.xml")
        self.controller.take_screenshot(after_img)

        # Step E: Compare and Verify
        is_success = calculate_image_diff(before_img, after_img, threshold=0.01)

        if is_success:
            logging.info(f"    -> ✅ Verification passed! Saving data (Images and XML).")
            dataset_id = f"{page_id}_swipe_{idx}"
            
            final_before_img = self.output_dir / f"{dataset_id}_before.png"
            final_before_xml = self.output_dir / f"{dataset_id}_before.xml"
            final_after_img = self.output_dir / f"{dataset_id}_after.png"
            final_after_xml = self.output_dir / f"{dataset_id}_after.xml"

            shutil.move(before_img, final_before_img)
            shutil.move(after_img, final_after_img)
            shutil.move(before_xml, final_before_xml)
            shutil.move(after_xml, final_after_xml)

            sx, sy = swipe_params['start']
            ex, ey = swipe_params['end']

            def convert(coords):
                x, y = coords
                W, H = self.screen_size
                return[round(x*1000/W, 1), round(y*1000/H, 1)]

            action = {
                "action": "swipe",
                "bbox": candidate['bbox'],
                "instruction": candidate.get('command', ''),
                "start": convert([sx, sy]),
                "end": convert([ex, ey]),
                "duration": swipe_params['duration'],
            }

            if sx == ex:
                action['direction'] = "up" if sy > ey else "down"
            elif sy == ey:  
                action['direction'] = "left" if sx > ex else "right"
            else:           
                pass

            self.successful_swipes.append({
                "img_filename": f"{dataset_id}_before.png", 
                "after_image": f"{dataset_id}_after.png", 
                "action_data": action
            })
            self.save_dataset()
        else:
            logging.info(f"    -> ❌ Verification failed! No UI changes after swipe. Discarding data.")
            for temp_file in [before_img, before_xml, after_img, after_xml]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    def save_dataset(self):
        unique_swipes = {s['img_filename']: s for s in self.successful_swipes}
        self.successful_swipes = list(unique_swipes.values())

        with open(self.dataset_file, 'w', encoding='utf-8') as f:
            json.dump(self.successful_swipes, f, ensure_ascii=False, indent=2)
            
        unique_clicks = {s['target_page']: s for s in self.successful_clicks}
        self.successful_clicks = list(unique_clicks.values())
        
        with open(self.click_dataset_file, 'w', encoding='utf-8') as f:
            json.dump(self.successful_clicks, f, ensure_ascii=False, indent=2)
            
        logging.info(f"Data synced and saved. Swipe: {len(self.successful_swipes)} records, Click: {len(self.successful_clicks)} records.")