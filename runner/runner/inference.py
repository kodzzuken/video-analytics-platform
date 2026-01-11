import random
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MockInferenceModel:
    """
    Mock inference model for testing.
    In production, this would integrate with a real model like YOLOv5, TensorFlow, etc.
    """
    
    def __init__(self):
        self.class_names = [
            "person", "car", "truck", "bicycle",
            "dog", "cat", "bird", "background"
        ]
        logger.info("Mock inference model initialized")
    
    def predict(self, frame: Any) -> List[Dict[str, Any]]:
        """
        Perform inference on frame.
        Returns list of detections with class, confidence, and bbox.
        """
        try:
            # Get frame dimensions
            height, width = frame.shape[:2]
            
            # Generate random detections (mock)
            num_detections = random.randint(0, 3)
            detections = []
            
            for _ in range(num_detections):
                class_id = random.randint(0, len(self.class_names) - 1)
                confidence = random.uniform(0.7, 0.99)
                
                # Generate random bbox [x_min, y_min, x_max, y_max]
                x_min = random.randint(0, width - 50)
                y_min = random.randint(0, height - 50)
                x_max = min(x_min + random.randint(50, 200), width)
                y_max = min(y_min + random.randint(50, 200), height)
                
                detection = {
                    "class": self.class_names[class_id],
                    "confidence": round(confidence, 2),
                    "bbox": [x_min, y_min, x_max, y_max]
                }
                detections.append(detection)
            
            return detections
        
        except Exception as e:
            logger.error(f"Inference failed: {str(e)}")
            return []

def get_model() -> MockInferenceModel:
    return MockInferenceModel()
