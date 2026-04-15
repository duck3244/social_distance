import logging

import cv2

from config import (
    YOLOV8_MODEL_PATH,
    VIDEO_PATH,
    SAFE_DISTANCE,
    CONFIDENCE_THRESHOLD,
)
from detector import YoloDetector
from visualizer import Visualizer
from distance_monitor import DistanceMonitor

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    detector = YoloDetector(YOLOV8_MODEL_PATH)
    distance_monitor = DistanceMonitor(SAFE_DISTANCE)
    visualizer = Visualizer()

    vs = cv2.VideoCapture(VIDEO_PATH)
    if not vs.isOpened():
        logger.error("Could not open video file: %s", VIDEO_PATH)
        return

    total = int(vs.get(cv2.CAP_PROP_FRAME_COUNT))
    logger.info("Total frames: %d", total)

    try:
        while True:
            grabbed, frame = vs.read()
            if not grabbed:
                logger.info("End of video file reached")
                break

            frame = cv2.resize(frame, (640, 480))

            boxes, confidences, box_centers = detector.detect(frame, CONFIDENCE_THRESHOLD)
            unsafe_pairs, count = distance_monitor.check_distances(boxes, box_centers)
            frame = visualizer.draw_results(frame, boxes, confidences, box_centers, unsafe_pairs, count)

            cv2.imshow('Demo', frame)
            if (cv2.waitKey(1) & 0xFF) == ord('q'):
                break
    finally:
        logger.info("Cleaning up...")
        vs.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
