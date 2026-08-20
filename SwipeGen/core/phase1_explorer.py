import time
import os
import logging
from pathlib import Path
from core.device_controller import UIAutomatorController
from core.page_graph import PageMemory

class Phase1Explorer:
    def __init__(self, package_name: str, max_depth=3):
        self.package = package_name
        self.max_depth = max_depth
        self.controller = UIAutomatorController()
        self.memory = PageMemory(package_name=self.package, similarity_threshold=0.85)
        
        self.temp_dir = Path("outputs") / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
    def run_exploration(self):
        """Core BFS Exploration Loop"""
        logging.info(f"=== Starting Phase 1 Automated Exploration (App: {self.package}) ===")
        
        queue = []
        
        #[Breakpoint Resume] Load existing progress
        if self.memory.load_from_disk():
            logging.info(f"  -> 📦 Found existing progress, restored {len(self.memory.pages)} page graphs!")
            for p in self.memory.pages:
                if len(p.trajectory) < self.max_depth and not getattr(p, 'is_fully_explored', False):
                    queue.append(p.page_id)
        else:
            self.controller.reset_app(self.package)
            time.sleep(8) # Wait for dynamic UI rendering
            
            temp_home = str(self.temp_dir / "temp_home.png")
            self.controller.take_screenshot(temp_home)
            # Home page has no parent node
            home_page_id = self.memory.add_page(temp_home, trajectory=[], parent_page_id=None)
            logging.info(f"Recorded Home Page: {home_page_id}")
            queue.append(home_page_id)

        while queue:
            current_page_id = queue.pop(0)
            current_page = self.memory.get_page(current_page_id)
            
            if len(current_page.trajectory) >= self.max_depth:
                continue

            logging.info(f"\n--- Exploring Page: {current_page_id} (Depth: {len(current_page.trajectory)}) ---")
            
            # Replay handling (actively return to home if restoring from page_0)
            if len(current_page.trajectory) == 0:
                logging.info(f"  -> [Reset] Returning to home page...")
                self.controller.reset_app(self.package)
                time.sleep(1) 
            else:
                if not self.controller.replay_trajectory(self.package, current_page.trajectory):
                    logging.error(f"  -> ❌ Failed to stably replay trajectory to {current_page_id}, abandoning exploration of this page.")
                    continue
            time.sleep(8) 
            
            elements = self.controller.get_clickable_elements_xml()
            logging.info(f"Detected {len(elements)} clickable elements.")

            for elem in elements:
                time.sleep(8) 
                success = self._explore_single_element(elem, current_page, queue)
                if not success:
                    # Break loop if a fatal error occurs (e.g., ADB disconnect, app crash)
                    break
            else:
                # Mark page fully explored only if loop completes without breaking
                current_page.is_fully_explored = True
                self.memory.save_to_disk()

        self.memory.save_to_disk()
        logging.info(f"\n=== Phase 1 Exploration Complete. Discovered {len(self.memory.pages)} Independent Structural Pages ===")

    def _explore_single_element(self, elem: dict, current_page, queue: list) -> bool:
        """
        Handles single element exploration (Click, Debounce, Screenshot, Verify, Replay).
        Returns False if a fatal error occurs.
        """
        cx, cy = elem['center']
        
        # Deduplication check
        if any(abs(cx - vx) < 20 and abs(cy - vy) < 20 for vx, vy in current_page.visited_elements):
            return True
        
        # Mark and save progress
        current_page.visited_elements.add((cx, cy))
        self.memory.save_to_disk() 
        
        btn_name = elem.get('text') or elem.get('desc') or 'Unknown Component'
        logging.info(f"[{current_page.page_id}] Clicked: ({cx}, {cy}) [{btn_name}]")
        
        # Save bbox for Phase 2 Intent Generation
        action = {
            'x': cx, 
            'y': cy, 
            'bbox': elem['bounds'], 
            'desc': btn_name, 
            'expected_image_path': ''
        }
        new_trajectory = current_page.trajectory + [action]

        self.controller.click(cx, cy, delay=2.5)

        # Smart debounce: wait for loading to finish
        self.controller.wait_for_loading_to_finish()

        # Escape prevention check
        current_pkg = self.controller.get_current_package()
        if current_pkg != self.package:
            logging.warning(f"  -> ⚠️ Unexpectedly exited target app (Current: {current_pkg}). Aborting branch.")
            if not self.controller.replay_trajectory(self.package, current_page.trajectory):
                logging.error("  -> ❌ Fatal Error: Failed to restore to base page.")
                return False 
            return True 
        
        # Capture and compare new state
        temp_img = str(self.temp_dir / f"temp_{int(time.time())}.png")
        self.controller.take_screenshot(temp_img)
        is_new, matched_id = self.memory.is_new_page(temp_img)

        if is_new:
            # Pass current page ID as parent_page_id
            new_page_id = self.memory.add_page(temp_img, new_trajectory, parent_page_id=current_page.page_id)
            logging.info(f"  -> ⭐ New page skeleton detected! Recorded as {new_page_id}")

            new_page_node = self.memory.get_page(new_page_id)
            new_page_node.scrollable_components = self.controller.get_scrollable_elements_xml()
            logging.info(f"     Extracted and saved {len(new_page_node.scrollable_components)} XML scrollable components.")
            
            action['expected_image_path'] = new_page_node.image_path
            queue.append(new_page_id)
        else:
            logging.info(f"  -> No structural UI changes detected (skeleton matched {matched_id})")
            matched_page_node = self.memory.get_page(matched_id)
            action['expected_image_path'] = matched_page_node.image_path
            
            if os.path.exists(temp_img):
                os.remove(temp_img)
            temp_xml = temp_img.replace('.png', '.xml')
            if os.path.exists(temp_xml):
                os.remove(temp_xml)

        self.memory.save_to_disk()

        # Restore initial state of the current page for the next element
        if not self.controller.replay_trajectory(self.package, current_page.trajectory):
            logging.error("  -> ❌ Fatal Error: Failed to restore to base page.")
            return False

        return True