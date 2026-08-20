import cv2
import numpy as np

class ImageUtils:
    @staticmethod
    def get_skeleton_image(image_path: str) -> np.ndarray:
        """Extract the UI skeleton graph of an image"""
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Failed to load Image: {image_path}")
        
        # 1. Downscale to smooth out minute details
        scale_percent = 300 / img.shape[1]
        width = int(img.shape[1] * scale_percent)
        height = int(img.shape[0] * scale_percent)
        resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
        
        # 2. Gaussian blur to remove content textures
        blurred = cv2.GaussianBlur(resized, (5, 5), 0)
        
        # 3. Edge detection to extract UI component boundaries
        edges = cv2.Canny(blurred, 50, 150)
        
        # 4. Dilation to make component borders thicker and continuous
        kernel = np.ones((3, 3), np.uint8)
        skeleton = cv2.dilate(edges, kernel, iterations=1)
        
        return skeleton

    @staticmethod
    def save_skeleton(image_path: str, output_path: str):
        """Generate and save the skeleton image for visual debugging"""
        skeleton = ImageUtils.get_skeleton_image(image_path)
        cv2.imwrite(output_path, skeleton)

    @staticmethod
    def calculate_skeleton_similarity(img_path1: str, img_path2: str) -> float:
        """Calculate the structural skeleton similarity between two screenshots"""
        skel1 = ImageUtils.get_skeleton_image(img_path1)
        skel2 = ImageUtils.get_skeleton_image(img_path2)
        
        if skel1.shape != skel2.shape:
            skel2 = cv2.resize(skel2, (skel1.shape[1], skel1.shape[0]))
            
        intersection = np.logical_and(skel1 > 0, skel2 > 0)
        union = np.logical_or(skel1 > 0, skel2 > 0)
        
        union_sum = np.sum(union)
        if union_sum == 0:
            return 1.0
            
        return np.sum(intersection) / union_sum
    
def calculate_image_diff(img_path1: str, img_path2: str, threshold=0.01) -> bool:
    """
    Compute pixel-level difference between two screenshots.
    Used to determine if a swipe action triggered substantial UI changes.
    """
    import cv2
    import numpy as np
    
    img1 = cv2.imread(img_path1, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(img_path2, cv2.IMREAD_GRAYSCALE)
    
    if img1 is None or img2 is None:
        return False
        
    if img1.shape != img2.shape:
        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        
    # Calculate absolute differences
    diff = cv2.absdiff(img1, img2)
    # Binarize to filter out minor rendering noise (pixel delta > 10 is considered change)
    _, diff_thresh = cv2.threshold(diff, 10, 255, cv2.THRESH_BINARY)
    
    # Calculate the ratio of changed pixels to total pixels
    change_ratio = np.count_nonzero(diff_thresh) / diff_thresh.size
    print(f"[Verify] UI change ratio: {change_ratio:.4f} (Threshold: {threshold})")
    
    return change_ratio > threshold
    

def mask(img, box, reason):
    """Draw aesthetically pleasing anonymization masks for better interpretability"""
    x1, y1, x2, y2 = box
    box_w, box_h = x2 - x1, y2 - y1
    
    # A. Draw solid black background rectangle (thickness -1 means fill)
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)
    
    # B. Draw gray outer border (thickness 2)
    cv2.rectangle(img, (x1, y1), (x2, y2), (128, 128, 128), 2)
    
    # C. Draw anonymization reason text (white)
    if box_w > 20 and box_h > 12: # Filter out extremely small boxes
        text_str = f"[{reason}]"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        
        # Get text size dynamically
        (text_w, text_h), _ = cv2.getTextSize(text_str, font, font_scale, thickness)
        
        # Core logic: Dynamically auto-scale font size to prevent text overflow
        if text_w > box_w - 4:
            font_scale = font_scale * ((box_w - 4) / text_w)
            (text_w, text_h), _ = cv2.getTextSize(text_str, font, font_scale, thickness)
        
        # Render text only if it's large enough to be legible
        if font_scale > 0.15:
            text_x = int(x1 + (box_w - text_w) / 2)
            text_y = int(y1 + (box_h + text_h) / 2)
            cv2.putText(img, text_str, (text_x, text_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    return img