import cv2


class Visualizer:
    def __init__(self):
        """
        감지 결과를 시각화하는 클래스
        """
        pass


    def draw_results(self, frame, boxes, confidences, box_centers, unsafe, count):
        """
        감지 결과를 시각화하여 프레임에 그림
        
        Args:
            frame: 입력 이미지 프레임
            boxes: 감지된 경계 상자 목록
            confidences: 신뢰도 목록
            box_centers: 경계 상자 중심점 목록
            unsafe: 안전 거리를 위반한 좌표 목록
            count: 안전 거리를 위반한 사람 수
            
        Returns:
            frame: 시각화된 결과가 그려진 프레임
        """
        # 모든 감지된 객체에 대해 경계 상자와 신뢰도 표시
        for i in range(len(boxes)):
            (x, y) = (boxes[i][0], boxes[i][1])
            (w, h) = (boxes[i][2], boxes[i][3])
            centeriX, centeriY = box_centers[i]
            
            # 다른 감지된 객체와의 연결선 그리기
            for j in range(len(boxes)):
                if i != j:
                    centerjX, centerjY = box_centers[j]
                    
                    # 두 중심점 사이에 연결선이 있는지 확인
                    for k in range(0, len(unsafe), 2):
                        if k+1 < len(unsafe):
                            if ((centeriX == unsafe[k][0] and centeriY == unsafe[k][1]) and 
                                (centerjX == unsafe[k+1][0] and centerjY == unsafe[k+1][1])) or \
                               ((centeriX == unsafe[k+1][0] and centeriY == unsafe[k+1][1]) and 
                                (centerjX == unsafe[k][0] and centerjY == unsafe[k][0])):
                                # 안전 거리를 위반한 경우 빨간 선으로 연결
                                cv2.line(frame, (centeriX, centeriY), (centerjX, centerjY), (0, 0, 255), 2)
            
            # 안전 거리 위반 여부에 따라 경계 상자 색상 결정
            is_unsafe = False
            for coord in unsafe:
                if coord[0] == centeriX and coord[1] == centeriY:
                    is_unsafe = True
                    break
            
            # 경계 상자 그리기 (위반 시 빨간색, 그렇지 않으면 녹색)
            color = (0, 0, 255) if is_unsafe else (0, 255, 0)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # 신뢰도 텍스트 표시
            text = f'Person: {confidences[i]:.4f}'
            cv2.putText(frame, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # 안전하지 않은 사람 수 표시 (왼쪽 상단)
        text = f'People unsafe: {count}'
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        
        # 배경 사각형
        cv2.rectangle(frame, (10, 10), (10 + text_size[0] + 20, 10 + text_size[1] + 10), (0, 0, 0), -1)
        
        # 텍스트
        cv2.putText(frame, text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return frame

