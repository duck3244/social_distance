import math


class DistanceMonitor:
    def __init__(self, safe_distance):
        """
        사람들 간의 거리를 모니터링하는 클래스
        
        Args:
            safe_distance (float): 안전 거리 (픽셀 단위)
        """
        self.safe_distance = safe_distance


    def check_distances(self, boxes, box_centers):
        """
        감지된 모든 사람 간의 거리를 확인하고 안전 거리 위반을 표시
        
        Args:
            boxes: 감지된 경계 상자 목록
            box_centers: 감지된 경계 상자의 중심점 목록
            
        Returns:
            unsafe: 안전 거리를 위반한 사람들의 좌표
            count: 안전 거리를 위반한 사람 수
        """
        unsafe = []
        count = 0
        
        # 각 감지된 객체에 대해
        for i in range(len(boxes)):
            centeriX, centeriY = box_centers[i]
            
            # 다른 모든 감지된 사람과의 거리 확인
            for j in range(len(boxes)):
                if i != j:
                    centerjX, centerjY = box_centers[j]
                    
                    # 유클리드 거리 계산
                    distance = math.sqrt(math.pow(centerjX - centeriX, 2) + math.pow(centerjY - centeriY, 2))
                    
                    # 안전 거리 위반 체크
                    if distance <= self.safe_distance:
                        unsafe.append([centerjX, centerjY])
                        unsafe.append([centeriX, centeriY])
        
        # 안전하지 않은 사람 수 계산 (중복 제거)
        unique_unsafe = set(tuple(coord) for coord in unsafe)
        count = len(unique_unsafe)
        
        return unsafe, count

