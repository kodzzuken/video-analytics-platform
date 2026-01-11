import cv2
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class VideoProcessor:
    """
    Handles video stream reading and frame extraction.
    """
    
    def __init__(self, video_url: str, fps_target: int = 2):
        self.video_url = video_url
        self.fps_target = fps_target
        self.cap = None
        self.frame_count = 0
        self.frame_skip = None
        
    def open(self) -> bool:
        """
        Open video stream.
        Supports RTSP, HTTP, and local file paths.
        """
        try:
            self.cap = cv2.VideoCapture(self.video_url)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open video: {self.video_url}")
                return False
            
            # Get video FPS
            original_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            if original_fps <= 0:
                original_fps = 25  # Default FPS
            
            # Calculate frame skip to achieve target FPS
            self.frame_skip = max(1, original_fps // self.fps_target)
            
            logger.info(
                f"Opened video: {self.video_url} "
                f"(original FPS: {original_fps}, target FPS: {self.fps_target}, "
                f"skip: {self.frame_skip})"
            )
            return True
        
        except Exception as e:
            logger.error(f"Error opening video: {str(e)}")
            return False
    
    def read_frame(self) -> Optional[Any]:
        """
        Read next frame from stream.
        Returns numpy array or None if stream ends/error.
        """
        if not self.cap or not self.cap.isOpened():
            return None
        
        try:
            ret, frame = self.cap.read()
            
            if not ret:
                logger.warning(f"Failed to read frame or stream ended")
                return None
            
            self.frame_count += 1
            return frame
        
        except Exception as e:
            logger.error(f"Error reading frame: {str(e)}")
            return None
    
    def get_frame_number(self) -> int:
        """Get current frame number"""
        return self.frame_count
    
    def close(self):
        """Close video stream"""
        if self.cap:
            self.cap.release()
            logger.info(f"Video stream closed. Total frames: {self.frame_count}")

def extract_frames(video_url: str, fps_target: int = 2, max_frames: Optional[int] = None):
    """
    Generator for extracting frames from video.
    """
    processor = VideoProcessor(video_url, fps_target)
    
    if not processor.open():
        return
    
    frame_index = 0
    skip_counter = 0
    
    try:
        while True:
            frame = processor.read_frame()
            
            if frame is None:
                break
            
            skip_counter += 1
            
            # Skip frames to achieve target FPS
            if skip_counter >= processor.frame_skip:
                skip_counter = 0
                frame_index += 1
                
                yield frame, frame_index, datetime.utcnow().isoformat() + 'Z'
                
                if max_frames and frame_index >= max_frames:
                    logger.info(f"Reached max frames: {max_frames}")
                    break
    
    finally:
        processor.close()
