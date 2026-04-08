import json
import shutil
import os
import logging
from pathlib import Path
from utils.image_utils import ImageUtils

class PageNode:
    def __init__(self, page_id: str, image_path: str, skeleton_path: str, trajectory: list, parent_page_id: str = None):
        self.page_id = page_id
        self.image_path = image_path
        self.skeleton_path = skeleton_path
        self.trajectory = trajectory
        self.visited_elements = set()
        self.scrollable_components =[]
        self.parent_page_id = parent_page_id
        self.is_fully_explored = False

class PageMemory:
    def __init__(self, package_name: str, similarity_threshold=0.85):
        self.pages =[]
        self.similarity_threshold = similarity_threshold
        
        self.output_dir = Path("outputs") / package_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.json_file = self.output_dir / "memory_graph.json"

    def load_from_disk(self) -> bool:
        """Recover previous exploration progress from JSON"""
        if not self.json_file.exists():
            return False
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.pages =[]
            for item in data:
                node = PageNode(
                    page_id=item['page_id'],
                    image_path=item['image_path'],
                    skeleton_path=item['skeleton_path'],
                    trajectory=item['trajectory'],
                    parent_page_id=item.get('parent_page_id')
                )
                node.scrollable_components = item.get('scrollable_components',[])
                node.visited_elements = set(tuple(x) for x in item.get('visited_elements',[]))
                node.is_fully_explored = item.get('is_fully_explored', False)
                self.pages.append(node)
            return True
        except Exception as e:
            logging.error(f"Failed to load map cache: {e}")
            return False

    def is_new_page(self, new_image_path: str):
        if not self.pages:
            return True, None

        for page in self.pages:
            sim = ImageUtils.calculate_skeleton_similarity(page.image_path, new_image_path)
            if sim >= self.similarity_threshold:
                return False, page.page_id
        
        return True, None

    def add_page(self, temp_image_path: str, trajectory: list, parent_page_id: str = None) -> str:
        """Formally record the temporary screenshot as a new Page"""

        page_index = len(self.pages)
        page_id = f"page_{page_index}"
        
        final_img_path = self.output_dir / f"{page_id}.png"
        final_skel_path = self.output_dir / f"{page_id}_skeleton.png"
        final_xml_path = self.output_dir / f"{page_id}.xml"
        
        shutil.move(temp_image_path, final_img_path)
        
        temp_xml_path = temp_image_path.replace('.png', '.xml')
        if os.path.exists(temp_xml_path):
            shutil.move(temp_xml_path, final_xml_path)
            
        ImageUtils.save_skeleton(str(final_img_path), str(final_skel_path))
        
        new_page = PageNode(
            page_id=page_id,
            image_path=str(final_img_path),
            skeleton_path=str(final_skel_path),
            trajectory=trajectory,
            parent_page_id=parent_page_id
        )
        self.pages.append(new_page)
        return page_id

    def get_page(self, page_id: str) -> PageNode:
        for p in self.pages:
            if p.page_id == page_id:
                return p
        return None

    def save_to_disk(self):
        data =[]
        for p in self.pages:
            data.append({
                "page_id": p.page_id,
                "parent_page_id": getattr(p, 'parent_page_id', None),
                "image_path": p.image_path,
                "skeleton_path": p.skeleton_path,
                "trajectory": p.trajectory,
                "scrollable_components": getattr(p, 'scrollable_components',[]),
                "visited_elements": list(p.visited_elements),
                "is_fully_explored": getattr(p, 'is_fully_explored', False)
            })
        
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"Page graph saved to: {self.json_file}")