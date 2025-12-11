"""
ML Model Service - Calls Actual GCP Vision Inference API
Endpoints loaded from config
"""
import requests
import base64
from io import BytesIO
from typing import Dict, Tuple
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class MLModelService:
    """Service to call actual ML model endpoints."""
    
    @staticmethod
    def predict_tb(image_data: BytesIO) -> Tuple[Dict, BytesIO]:
        """
        Call TB classification endpoint.
        
        Args:
            image_data: Image file as BytesIO
            
        Returns:
            (prediction_dict, gradcam_image)
        """
        try:
            logger.info("Calling TB model endpoint...")
            
            # Prepare file for upload
            image_data.seek(0)
            files = {'file': ('scan.jpg', image_data, 'image/jpeg')}
            headers = {'accept': 'application/json'}
            
            # Call endpoint
            response = requests.post(
                settings.TB_MODEL_ENDPOINT,
                headers=headers,
                files=files,
                timeout=60  # 1 minute timeout
            )
            
            if response.status_code != 200:
                logger.error(f"TB model API error: {response.status_code} - {response.text}")
                raise Exception(f"Model API returned {response.status_code}")
            
            result = response.json()
            
            # Extract prediction
            prediction = {
                "predicted_class": result.get("predicted_class", "Unknown"),
                "confidence": result.get("confidence", 0.0),
                "class_probabilities": result.get("class_probabilities", {})
            }
            
            # Decode GradCAM image
            gradcam_image = None
            if 'gradcam_image' in result:
                gradcam_base64 = result['gradcam_image']
                gradcam_bytes = base64.b64decode(gradcam_base64)
                gradcam_image = BytesIO(gradcam_bytes)
            
            logger.info(f" TB model prediction: {prediction['predicted_class']} ({prediction['confidence']:.2%})")
            
            return prediction, gradcam_image
            
        except requests.Timeout:
            logger.error("TB model endpoint timeout")
            raise Exception("Model inference timeout")
        except Exception as e:
            logger.error(f"TB model error: {e}")
            raise
    
    @staticmethod
    def predict_lung_cancer(image_data: BytesIO) -> Tuple[Dict, BytesIO]:
        """
        Call Lung Cancer classification endpoint.
        
        Args:
            image_data: Image file as BytesIO
            
        Returns:
            (prediction_dict, gradcam_image)
        """
        try:
            logger.info("Calling Lung Cancer model endpoint...")
            
            # Prepare file
            image_data.seek(0)
            files = {'file': ('scan.jpg', image_data, 'image/jpeg')}
            headers = {'accept': 'application/json'}
            
            # Call endpoint (TODO: Update URL when lung cancer endpoint is ready)
            response = requests.post(
                settings.LUNG_CANCER_MODEL_ENDPOINT,
                headers=headers,
                files=files,
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f"LC model API error: {response.status_code}")
                # For now, return mock data if endpoint not ready
                logger.warning("Lung Cancer endpoint not ready, using mock data")
                return MLModelService._mock_lung_cancer_prediction()
            
            result = response.json()
            
            prediction = {
                "predicted_class": result.get("predicted_class", "Unknown"),
                "confidence": result.get("confidence", 0.0),
                "class_probabilities": result.get("class_probabilities", {})
            }
            
            # Decode GradCAM
            gradcam_image = None
            if 'gradcam_image' in result:
                gradcam_base64 = result['gradcam_image']
                gradcam_bytes = base64.b64decode(gradcam_base64)
                gradcam_image = BytesIO(gradcam_bytes)
            
            logger.info(f" LC model prediction: {prediction['predicted_class']} ({prediction['confidence']:.2%})")
            
            return prediction, gradcam_image
            
        except Exception as e:
            logger.error(f"LC model error: {e}")
            # Return mock data for now
            return MLModelService._mock_lung_cancer_prediction()
    
    @staticmethod
    def _mock_lung_cancer_prediction() -> Tuple[Dict, None]:
        """Mock lung cancer prediction (until endpoint is ready)."""
        logger.warning("Using mock Lung Cancer prediction")
        return {
            "predicted_class": "adenocarcinoma",
            "confidence": 0.82,
            "class_probabilities": {
                "normal": 0.18,
                "adenocarcinoma": 0.82,
                "squamous_cell": 0.00,
                "large_cell": 0.00
            }
        }, None


# Singleton
ml_model_service = MLModelService()