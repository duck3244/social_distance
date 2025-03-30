import cv2
import time

from config import SAFE_DISTANCE
from detector import YoloDetector
from visualizer import Visualizer
from distance_monitor import DistanceMonitor


def main():
    # Initialize components
    detector = YoloDetector("yolov8n.pt")
    distance_monitor = DistanceMonitor(SAFE_DISTANCE)
    visualizer = Visualizer()
    
    # 비디오 캡처 객체 생성
    vs = cv2.VideoCapture("small.mp4")
    
    # 비디오가 성공적으로 열렸는지 확인
    if not vs.isOpened():
        print("Error: Could not open video file.")
        exit()
    
    # 총 프레임 수 계산
    try:
        prop = cv2.CAP_PROP_FRAME_COUNT
        total = int(vs.get(prop))
        print('Total frames detected are: ', total)
    except Exception as e:
        print(e)
        total = -1
    
    while True:
        # 프레임 읽기
        (grabbed, frame) = vs.read()
        
        if not grabbed:
            print("End of video file reached")
            break
        
        # 프레임 크기 조정
        frame = cv2.resize(frame, (640, 480))
        
        # YOLO 모델로 사람 감지
        start_time = time.time()
        boxes, confidences, box_centers = detector.detect(frame)
        end_time = time.time()
        
        # 안전 거리 체크
        unsafe_coords, count = distance_monitor.check_distances(boxes, box_centers)
        
        # 결과 시각화
        frame = visualizer.draw_results(frame, boxes, confidences, box_centers, unsafe_coords, count)
        
        # 프레임 표시
        cv2.imshow('Demo', frame)
        
        # waitKey 호출
        key = cv2.waitKey(1) & 0xFF
        
        # 'q' 키를 누르면 종료
        if key == ord('q'):
            break
    
    # 정리
    print('Cleaning up...')
    vs.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

