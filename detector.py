import numpy as np

from ultralytics import YOLO


class YoloDetector:
    def __init__(self, model_path):
        """
        YOLOv8 모델을 로드하고 객체 감지를 수행하는 클래스
        
        Args:
            model_path (str): YOLO 모델 파일 경로
        """
        print(f'Loading YOLO model from {model_path}...')
        self.model = YOLO(model_path)


    def detect(self, frame, conf_threshold=0.5):
        """
        프레임에서 사람을 감지
        
        Args:
            frame: 입력 이미지 프레임
            conf_threshold (float): 신뢰도 임계값
            
        Returns:
            boxes, confidences, box_centers: 감지된 객체의 경계 상자, 신뢰도, 중심점
        """
        # YOLOv8로 사람 감지 실행 (사람만 감지하도록 classes=0 설정)
        results = self.model(frame, conf=conf_threshold, classes=0)  # 0은 사람 클래스
        
        boxes = []
        confidences = []
        box_centers = []
        
        # 결과가 있는지 확인
        if len(results) > 0:
            # 첫 번째 결과 가져오기 (한 프레임에 대한 결과)
            result = results[0]
            
            # 각 탐지된 객체에 대해
            for box in result.boxes:
                # 신뢰도
                confidence = float(box.conf)
                
                # 클래스 (YOLOv8에서는 이미 필터링되었지만 확인용)
                class_id = int(box.cls)
                
                # 바운딩 박스
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                width = x2 - x1
                height = y2 - y1
                
                # 중심점 계산
                centerX = x1 + width // 2
                centerY = y1 + height // 2
                
                # 결과 저장
                boxes.append([x1, y1, width, height])
                confidences.append(confidence)
                box_centers.append([centerX, centerY])
            
            # 디버깅
            print(f"Detected {len(boxes)} people in this frame")
        else:
            print("No detections in this frame")
        
        return boxes, confidences, box_centers

