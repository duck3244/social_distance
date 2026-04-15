import logging

import torch
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class YoloDetector:
    def __init__(self, model_path, device=None):
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info("Loading YOLO model from %s (device=%s)", model_path, device)
        self.model = YOLO(model_path)
        self.device = device

    def detect(self, frame, conf_threshold=0.5):
        results = self.model(frame, conf=conf_threshold, classes=0,
                             device=self.device, verbose=False)

        boxes = []
        confidences = []
        box_centers = []

        if not results:
            return boxes, confidences, box_centers

        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            w = x2 - x1
            h = y2 - y1
            boxes.append([x1, y1, w, h])
            confidences.append(float(box.conf))
            box_centers.append([x1 + w // 2, y1 + h // 2])

        logger.debug("Detected %d people", len(boxes))
        return boxes, confidences, box_centers
