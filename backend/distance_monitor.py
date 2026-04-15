class DistanceMonitor:
    def __init__(self, safe_distance):
        self.safe_distance = safe_distance
        self._safe_distance_sq = safe_distance * safe_distance

    def check_distances(self, boxes, box_centers):
        """
        감지된 사람 쌍 중 안전 거리를 위반한 쌍의 인덱스와 위반 인원 수를 반환.

        Returns:
            unsafe_pairs: list[tuple[int, int]] — 위반한 (i, j) 인덱스 쌍 (i < j)
            count: int — 위반에 연루된 고유 인원 수
        """
        unsafe_pairs = []
        unsafe_indices = set()

        n = len(box_centers)
        for i in range(n):
            xi, yi = box_centers[i]
            for j in range(i + 1, n):
                xj, yj = box_centers[j]
                dx = xj - xi
                dy = yj - yi
                if dx * dx + dy * dy <= self._safe_distance_sq:
                    unsafe_pairs.append((i, j))
                    unsafe_indices.add(i)
                    unsafe_indices.add(j)

        return unsafe_pairs, len(unsafe_indices)
