import uiautomator2 as u2
import time
import os
import cv2
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from utils.image_utils import ImageUtils, mask

SIM_THRESHOLD = 0.60
class UIAutomatorController:
    def __init__(self, device_serial=None):
        self.d = u2.connect(device_serial)
        logging.info(f"Device connected: {self.d.info}")
        self.window_size = self.d.window_size()

    def _extract_all_text_from_node(self, node):
        """
        Recursively extract text and content-desc from the current node and all its descendants.
        Returns a set containing all valid texts (deduplicated).
        """
        texts = set()
        
        # Extract text and content-desc from the current node
        text = node.attrib.get('text', '').strip()
        desc = node.attrib.get('content-desc', '').strip()
        if text: texts.add(text)
        if desc: texts.add(desc)
        
        # Recursively traverse all descendant nodes
        for child in node:
            texts.update(self._extract_all_text_from_node(child))
            
        return texts

    def get_clickable_elements_xml(self):
        """
        Get all clickable components and smartly aggregate their internal texts.
        """
        elements =[]
        try:
            # Use native XML dump for extreme speed and Android 15 / API 36 compatibility
            xml_dump = self.d.dump_hierarchy()
            root = ET.fromstring(xml_dump)
            
            # Traverse all nodes
            for node in root.iter('node'):
                # Look for nodes where clickable is true
                if node.attrib.get('clickable') == 'true':

                    bounds_str = node.attrib.get('bounds')
                    if not bounds_str: continue
                        
                    # Parse "[x1,y1][x2,y2]"
                    bounds_str = bounds_str.replace('][', ',').replace('[', '').replace(']', '')
                    x1, y1, x2, y2 = map(int, bounds_str.split(','))
                    
                    # Filter invalid coordinates or those out of screen bounds
                    if x2 <= x1 or y2 <= y1: continue
                    if x1 < 0 or y1 < 0 or x2 > self.window_size[0] or y2 > self.window_size[1]: continue

                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    
                    # Recursively extract all text inside the container
                    aggregated_texts = self._extract_all_text_from_node(node)
                    
                    # Concatenate into a descriptive string
                    final_text = " | ".join(aggregated_texts) if aggregated_texts else ""
                    
                    elements.append({
                        'bounds': [x1, y1, x2, y2],
                        'center': (cx, cy),
                        'text': final_text,
                        'resourceId': node.attrib.get('resource-id', '')
                    })
        except Exception as e:
            logging.error(f"Failed to parse XML for clickable nodes: {e}")
            
        return elements

    def take_anonymized_screenshot(self, output_path: str):
        """
        Screenshot and anonymization: Uses native dump_hierarchy, perfectly bypassing XPath limitations.
        Simultaneously saves the XML file of the current page for debugging and dataset usage.
        Adds visual enhancement: Black background + White border + Anonymization reason text.
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        self.d.screenshot(output_path)
        
        # Add sensitive keywords here based on observed XMLs
        sensitive_keywords = [
            'avatar', 'username', 
            'account', 'password', 
        ]
        
        img = cv2.imread(output_path)
        count = 0
        
        try:
            xml_dump = self.d.dump_hierarchy()
            
            # Save the corresponding XML file
            xml_path = output_path.replace('.png', '.xml')
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(xml_dump)
            
            root = ET.fromstring(xml_dump)
            
            for node in root.iter('node'):
                text = node.attrib.get('text', '').lower()
                desc = node.attrib.get('content-desc', '').lower()
                res_id = node.attrib.get('resource-id', '').lower()
                
                # Identify the specific hit keyword to use as the "anonymization reason"
                matched_kw = None
                for kw in sensitive_keywords:
                    if kw in text or kw in desc or kw in res_id:
                        matched_kw = kw
                        break
                
                if matched_kw:
                    bounds_str = node.attrib.get('bounds')
                    if bounds_str:
                        bounds_str = bounds_str.replace('][', ',').replace('[', '').replace(']', '')
                        coords = list(map(int, bounds_str.split(',')))
                        if len(coords) == 4:
                            # Pass coordinates and reason to the mask function
                            mask(img, coords, matched_kw.upper())
                            count += 1
                            
        except Exception as e:
            logging.error(f"[Anonymize] XML parsing exception: {e}")

        # Overwrite the image only if anonymization actually occurred to save Disk I/O
        if count > 0:
            cv2.imwrite(output_path, img)
            logging.info(f"  [Anonymize] Successfully masked {count} sensitive regions.")
            
        return output_path

    def take_screenshot(self, output_path: str):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        self.d.screenshot(output_path)

        xml_path = output_path.replace('.png', '.xml')
        try:
            xml_dump = self.d.dump_hierarchy()
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(xml_dump)
        except Exception as e:
            logging.error(f"Failed to dump XML during standard screenshot: {e}")

    def get_current_package(self):
        """Get the package name of the currently running foreground App"""
        try:
            return self.d.app_current()['package']
        except Exception:
            return ""

    def click(self, x, y, delay=1.5):
        """
        Execute click and wait.
        Added delay parameter to distinguish waiting needs between 'exploration' and 'replay'.
        """
        self.d.click(x, y)
        time.sleep(delay)

    def reset_app(self, package_name, delay=2.0):
        self.d.app_stop(self.get_current_package())  # stop current app to ensure a clean start
        time.sleep(0.5)
        self.d.app_start(package_name)
        time.sleep(delay)
        for attempt in range(3):
            if self.get_current_package() == package_name:
                logging.info(f"  [Device] App {package_name} launched and ready.")
                return
            if self.get_current_package() == "com.lbe.security.miui":
                logging.warning(f"  [Device] Security popup intercepted, attempting to bypass...")
                w, h = self.window_size
                self.click(w // 2, int(h * 0.91), delay=1.0)
            elif self.get_current_package() == "com.google.android.gms":
                logging.warning(f"[Device] GMS prompt detected, allowing to proceed...")
                return
            logging.info(f"[Device ×{attempt+1}] Waiting for app to launch, currently at: {self.get_current_package()}")
            time.sleep(1)

        self.d.app_start(package_name)
        for attempt in range(3, 6):
            if self.get_current_package() == package_name:
                logging.info(f"  [Device] App {package_name} launched and ready.")
                return
            if self.get_current_package() == "com.lbe.security.miui":
                logging.warning(f"  [Device] Security popup intercepted, attempting to go back...")
                self.d.press("back")
            logging.info(f"[Device ×{attempt+1}] Waiting for app to launch, currently at: {self.get_current_package()}")
            time.sleep(1)
        raise RuntimeError(f"Failed to launch app {package_name}. Please check device status.")

    def replay_trajectory(self, package_name, trajectory):
        """
        Reset App and replay trajectory with step-by-step state verification.
        Validates dynamically whether the expected intermediate page state is reached.
        """
        self.reset_app(package_name)
        
        temp_dir = Path("outputs") / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        for step_idx, action in enumerate(trajectory):
            self.click(action['x'], action['y'], delay=1.0)
            
            expected_path = action.get('expected_image_path')
            if not expected_path or not os.path.exists(expected_path):
                # Fallback to hard wait if expected image path is missing
                time.sleep(2.0)
                continue
                
            # --- Dynamic polling to verify the page state of the current step ---
            max_retries = 3
            wait_time = 2.0
            step_success = False
            
            for attempt in range(max_retries):
                verify_img = str(temp_dir / f"verify_step_{step_idx}_{int(time.time())}.png")
                self.take_screenshot(verify_img) 
                
                sim = ImageUtils.calculate_skeleton_similarity(verify_img, expected_path)
                
                # Cleanup temp files
                if os.path.exists(verify_img):
                    os.remove(verify_img) 
                verify_xml = verify_img.replace('.png', '.xml')
                if os.path.exists(verify_xml):
                    os.remove(verify_xml)
                    
                if sim >= SIM_THRESHOLD:
                    if attempt > 0:
                        logging.info(f"      -> Step {step_idx+1}/{len(trajectory)} loaded successfully (Time: ~{attempt * wait_time}s)")
                    step_success = True
                    break
                    
                logging.info(f"      -> ⏳ Step {step_idx+1}/{len(trajectory)} verification failed (Similarity: {sim:.2f}), retrying in {wait_time}s")
                time.sleep(wait_time)
                
            if not step_success:
                logging.error(f"    -> ❌ Trajectory replay failed at step {step_idx+1}: {action.get('desc', 'Unknown action')}")
                return False
                
        return True

    def replay_trajectory_unverified(self, package_name, trajectory):
        """Fast replay without verification, used for simple navigation (e.g., return to home)"""
        self.reset_app(package_name)
        for action in trajectory:
            self.click(action['x'], action['y'], delay=1.0)
        return True

    def swipe_by_normalized_bbox(self, bbox: list, direction: str, duration=0.3):
        """
        Calculate physical coordinates and execute swipe based on VLM's normalized bbox[0-1000].
        - vertical (browse down): swipe from bottom to top (y decreases)
        - horizontal (browse right): swipe from right to left (x decreases)
        """
        w, h = self.window_size
        x1, y1 = bbox[0] * w / 1000, bbox[1] * h / 1000
        x2, y2 = bbox[2] * w / 1000, bbox[3] * h / 1000
        
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        
        box_w = x2 - x1
        box_h = y2 - y1
        
        # Reserve 12% margin to prevent swiping out of bounds
        if direction.lower() == "vertical":
            start_x = end_x = cx
            start_y = y1 + box_h * 0.88
            end_y = y1 + box_h * 0.12
        else: # horizontal
            start_y = end_y = cy
            start_x = x1 + box_w * 0.88
            end_x = x1 + box_w * 0.12

        logging.info(f"    [Action] Executing swipe: ({int(start_x)}, {int(start_y)}) -> ({int(end_x)}, {int(end_y)})")
        self.d.swipe(start_x, start_y, end_x, end_y, duration=duration)
        time.sleep(2) # Wait for swipe animation and content loading

        return {
            "start": [int(start_x), int(start_y)],
            "end":[int(end_x), int(end_y)],
            "duration": duration
        }

    def get_scrollable_elements_xml(self):
        """
        Extract explicitly scrollable components via XML.
        Based on: scrollable="true" or SeekBar classes.
        """
        elements =[]
        try:
            xml_dump = self.d.dump_hierarchy()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_dump)
            
            for node in root.iter('node'):
                is_scrollable = node.attrib.get('scrollable') == 'true'
                is_seekbar = 'SeekBar' in node.attrib.get('class', '')
                
                if is_scrollable or is_seekbar:
                    bounds_str = node.attrib.get('bounds')
                    if not bounds_str: continue
                        
                    bounds_str = bounds_str.replace('][', ',').replace('[', '').replace(']', '')
                    x1, y1, x2, y2 = map(int, bounds_str.split(','))
                    
                    if x2 <= x1 or y2 <= y1: continue
                    
                    # Determine dominant axis for swiping
                    width = x2 - x1
                    height = y2 - y1
                    direction = "vertical" if height > width else "horizontal"
                    
                    aggregated_texts = self._extract_all_text_from_node(node)
                    final_text = " | ".join(aggregated_texts) if aggregated_texts else "No text content"
                    
                    elements.append({
                        'category': 'component',
                        'bounds': [x1, y1, x2, y2],
                        'direction': direction,
                        'text': final_text,
                        'resourceId': node.attrib.get('resource-id', '')
                    })
        except Exception as e:
            logging.error(f"Failed to parse XML for scrollable nodes: {e}")
            
        return elements
    
    def wait_for_loading_to_finish(self, timeout=8.0):
        """
        Smartly determine if the current page is still displaying a loading animation (e.g., spinner, progress bar).
        Blocks execution to prevent capturing 'false positive' data.
        """
        start_time = time.time()
        
        loading_keywords = [
            'progress', 'spinner',
        ]
        
        while time.time() - start_time < timeout:
            is_loading = False
            try:
                xml_dump = self.d.dump_hierarchy()
                root = ET.fromstring(xml_dump)
                
                for node in root.iter('node'):
                    cls = node.attrib.get('class', '')
                    res_id = node.attrib.get('resource-id', '').lower()
                    
                    # 1. Match native Android progress spinners
                    if cls == 'android.widget.ProgressBar':
                        bounds_str = node.attrib.get('bounds')
                        if bounds_str:
                            bounds_str = bounds_str.replace('][', ',').replace('[', '').replace(']', '')
                            x1, y1, x2, y2 = map(int, bounds_str.split(','))
                            w, h = x2 - x1, y2 - y1
                            # Filter out thin video seekbars, targeting square spinners
                            if 0.5 < (w / (h + 0.1)) < 2.0:
                                is_loading = True
                                break
                                
                    # 2. Match developer-named IDs
                    if any(kw in res_id for kw in loading_keywords):
                        if 'seekbar' not in cls.lower(): 
                            is_loading = True
                            break
                            
            except Exception:
                pass
                
            if not is_loading:
                return True
                
            logging.info(f"      -> ⏳ Asynchronous loading detected... Blocking and waiting...")
            time.sleep(1.0)
            
        logging.warning("      -> ⚠️ Wait for loading timeout, forcing continuation.")
        return False