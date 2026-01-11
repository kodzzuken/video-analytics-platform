"""Integration tests for full platform flow"""
import requests
import json
import time
import logging

logger = logging.getLogger(__name__)

API_URL = "http://localhost:8000/api/v1"

class TestVideoAnalyticsPlatform:
    """
    Integration tests for full platform.
    Requires:
    - docker-compose up -d
    - All services running
    """
    
    def test_health_check(self):
        """Test API health endpoint"""
        response = requests.get("http://localhost:8000/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        logger.info("✓ Health check passed")
    
    def test_create_scenario(self):
        """Test scenario creation"""
        payload = {
            "camera_url": "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"
        }
        response = requests.post(f"{API_URL}/scenario/init", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "scenario_uuid" in data
        assert data["status"] == "init_startup"
        
        logger.info(f"✓ Created scenario: {data['scenario_uuid']}")
        return data["scenario_uuid"]
    
    def test_get_scenario(self, scenario_uuid: str):
        """Test getting scenario details"""
        response = requests.get(f"{API_URL}/scenario/{scenario_uuid}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["scenario_uuid"] == str(scenario_uuid)
        
        logger.info(f"✓ Retrieved scenario: {data['status']}")
    
    def test_get_predictions(self, scenario_uuid: str):
        """Test getting predictions after processing"""
        # Wait for processing
        logger.info("Waiting for processing (30 seconds)...")
        time.sleep(30)
        
        response = requests.get(f"{API_URL}/prediction/{scenario_uuid}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["scenario_uuid"] == str(scenario_uuid)
        
        logger.info(f"✓ Retrieved predictions: {data['total_frames_processed']} frames")
        
        if data["results"]:
            first_result = data["results"][0]
            logger.info(f"  - Frame {first_result['frame_number']}: {len(first_result['detections'])} detections")
    
    def test_full_flow(self):
        """Test complete workflow"""
        logger.info("\n=== Testing Full Video Analytics Flow ===")
        
        # 1. Create scenario
        scenario_uuid = self.test_create_scenario()
        
        # 2. Get scenario details
        self.test_get_scenario(scenario_uuid)
        
        # 3. Wait and get predictions
        self.test_get_predictions(scenario_uuid)
        
        logger.info("\n✓✓✓ All tests passed!")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    tests = TestVideoAnalyticsPlatform()
    
    try:
        # Run tests
        tests.test_health_check()
        tests.test_full_flow()
    except AssertionError as e:
        logger.error(f"Test failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
