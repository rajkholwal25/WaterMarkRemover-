import cv2
import numpy as np
from pathlib import Path


class VideoProcessor:
    """Handles video processing for watermark/text removal"""
    
    def __init__(self):
        self.video_path = None
        self.cap = None
        self.total_frames = 0
        self.fps = 0
        self.width = 0
        self.height = 0
        self.mask = None
        self.current_frame = None
        
    def load_video(self, video_path):
        """Load a video file"""
        try:
            self.video_path = video_path
            self.cap = cv2.VideoCapture(video_path)
            
            if not self.cap.isOpened():
                return False, "Failed to open video file"
            
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Initialize mask
            self.mask = np.zeros((self.height, self.width), dtype=np.uint8)
            
            return True, f"Video loaded: {self.total_frames} frames @ {self.fps} FPS"
        except Exception as e:
            return False, f"Error loading video: {str(e)}"
    
    def get_frame(self, frame_num):
        """Get a specific frame from the video"""
        if self.cap is None:
            return None
        
        if frame_num < 0 or frame_num >= self.total_frames:
            return None
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()
        
        if ret:
            self.current_frame = frame
            return frame
        return None
    
    def get_first_frame(self):
        """Get the first frame of the video"""
        return self.get_frame(0)
    
    def add_mask_region(self, x1, y1, x2, y2):
        """Add a rectangular region to the removal mask"""
        if self.mask is None:
            return False
        
        # Normalize coordinates
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        # Clamp to video dimensions
        x1 = max(0, min(x1, self.width - 1))
        x2 = max(0, min(x2, self.width - 1))
        y1 = max(0, min(y1, self.height - 1))
        y2 = max(0, min(y2, self.height - 1))
        
        # Add to mask (white = remove)
        self.mask[y1:y2, x1:x2] = 255
        return True
    
    def clear_mask(self):
        """Clear the removal mask"""
        self.mask = np.zeros((self.height, self.width), dtype=np.uint8)
    
    def remove_watermark_frame(self, frame, method='inpaint'):
        """Remove watermark from a single frame using the mask"""
        if self.mask is None or cv2.countNonZero(self.mask) == 0:
            return frame.copy()
        
        frame_out = frame.copy()
        
        # Dilate the mask to remove edges better
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_dilated = cv2.dilate(self.mask, kernel, iterations=2)
        
        if method == 'inpaint':
            # Use Telea's inpainting algorithm
            frame_out = cv2.inpaint(frame_out, mask_dilated, 3, cv2.INPAINT_TELEA)
        elif method == 'morphological':
            # Use morphological operations for removal
            frame_out = cv2.morphologyEx(frame_out, cv2.MORPH_OPEN, kernel)
        
        return frame_out
    
    def process_video(self, output_path, progress_callback=None, method='inpaint'):
        """Process the entire video and remove watermarks"""
        if self.cap is None or cv2.countNonZero(self.mask) == 0:
            return False, "No video loaded or no regions selected"
        
        try:
            # Reset to start
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, self.fps, (self.width, self.height))
            
            if not out.isOpened():
                return False, "Failed to create output video file"
            
            # Process each frame
            for frame_num in range(self.total_frames):
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                # Remove watermark
                processed_frame = self.remove_watermark_frame(frame, method)
                
                # Write frame
                out.write(processed_frame)
                
                # Call progress callback
                if progress_callback:
                    progress_callback(frame_num, self.total_frames)
            
            out.release()
            return True, f"Video processed successfully: {output_path}"
        
        except Exception as e:
            return False, f"Error processing video: {str(e)}"
    
    def recolor_region(self, frame, x1, y1, x2, y2, hue_shift):
        """Recolor a region in a frame (changes clothes color, etc.)"""
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
        
        # Normalize coordinates
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        # Clamp to frame dimensions
        x1 = max(0, min(x1, self.width - 1))
        x2 = max(0, min(x2, self.width - 1))
        y1 = max(0, min(y1, self.height - 1))
        y2 = max(0, min(y2, self.height - 1))
        
        if x1 >= x2 or y1 >= y2:
            return frame.copy()
        
        # Apply hue shift to selected region
        region = frame_hsv[y1:y2, x1:x2]
        region[:, :, 0] = (region[:, :, 0] + hue_shift) % 180  # Hue is 0-180 in OpenCV
        
        frame_hsv[y1:y2, x1:x2] = region
        frame_hsv = np.clip(frame_hsv, 0, 255).astype(np.uint8)
        
        result = cv2.cvtColor(frame_hsv, cv2.COLOR_HSV2BGR)
        return result
    
    def replace_text_in_frame(self, frame, old_text, new_text, reader=None):
        """Detect and replace text in a frame using OCR"""
        if reader is None:
            try:
                import easyocr
                reader = easyocr.Reader(['en'])
            except ImportError:
                return frame.copy(), "EasyOCR not installed"
        
        try:
            # Detect text
            results = reader.readtext(frame)
            frame_out = frame.copy()
            
            replacements = 0
            for (bbox, text, confidence) in results:
                if old_text.lower() in text.lower():
                    # Get bounding box coordinates
                    pts = np.array(bbox, dtype=np.int32)
                    x_min = int(min(pt[0] for pt in bbox))
                    y_min = int(min(pt[1] for pt in bbox))
                    x_max = int(max(pt[0] for pt in bbox))
                    y_max = int(max(pt[1] for pt in bbox))
                    
                    # Create white mask over detected text
                    cv2.rectangle(frame_out, (x_min, y_min), (x_max, y_max), (255, 255, 255), -1)
                    
                    # Add new text
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = max(0.4, (x_max - x_min) / 100)
                    thickness = max(1, int(font_scale))
                    text_size = cv2.getTextSize(new_text, font, font_scale, thickness)[0]
                    text_x = x_min + ((x_max - x_min) - text_size[0]) // 2
                    text_y = y_min + ((y_max - y_min) + text_size[1]) // 2
                    
                    cv2.putText(frame_out, new_text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness)
                    replacements += 1
            
            return frame_out, replacements
        except Exception as e:
            return frame.copy(), f"Error: {str(e)}"
    
    def process_video_with_all_effects(self, output_path, effects_config, progress_callback=None):
        """Process video with watermark removal, text replacement, and color changes"""
        if self.cap is None:
            return False, "No video loaded"
        
        try:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, self.fps, (self.width, self.height))
            
            if not out.isOpened():
                return False, "Failed to create output video file"
            
            # Initialize OCR reader if text replacement is enabled
            reader = None
            if effects_config.get('text_replacements'):
                try:
                    import easyocr
                    reader = easyocr.Reader(['en'])
                except ImportError:
                    pass
            
            for frame_num in range(self.total_frames):
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                processed_frame = frame.copy()
                
                # Step 1: Remove watermarks
                if cv2.countNonZero(self.mask) > 0:
                    processed_frame = self.remove_watermark_frame(processed_frame, effects_config.get('removal_method', 'inpaint'))
                
                # Step 2: Replace text
                if effects_config.get('text_replacements'):
                    for old_text, new_text in effects_config['text_replacements']:
                        processed_frame, _ = self.replace_text_in_frame(processed_frame, old_text, new_text, reader)
                
                # Step 3: Recolor regions (clothes)
                if effects_config.get('recolor_regions'):
                    for x1, y1, x2, y2, hue_shift in effects_config['recolor_regions']:
                        processed_frame = self.recolor_region(processed_frame, x1, y1, x2, y2, hue_shift)
                
                out.write(processed_frame)
                
                if progress_callback:
                    progress_callback(frame_num, self.total_frames)
            
            out.release()
            return True, f"Video processed successfully: {output_path}"
        
        except Exception as e:
            return False, f"Error processing video: {str(e)}"
    
    def close(self):
        """Release video resources"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
