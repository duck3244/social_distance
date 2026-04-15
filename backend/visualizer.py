import cv2


class Visualizer:
    COLOR_SAFE = (0, 255, 0)
    COLOR_UNSAFE = (0, 0, 255)
    COLOR_TEXT = (255, 255, 255)
    FONT = cv2.FONT_HERSHEY_SIMPLEX

    def draw_results(self, frame, boxes, confidences, box_centers, unsafe_pairs, count):
        unsafe_indices = set()
        for i, j in unsafe_pairs:
            unsafe_indices.add(i)
            unsafe_indices.add(j)

        for i, j in unsafe_pairs:
            cv2.line(frame, tuple(box_centers[i]), tuple(box_centers[j]), self.COLOR_UNSAFE, 2)

        for i, (x, y, w, h) in enumerate(boxes):
            color = self.COLOR_UNSAFE if i in unsafe_indices else self.COLOR_SAFE
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            text = f'Person: {confidences[i]:.2f}'
            cv2.putText(frame, text, (x, y - 5), self.FONT, 0.5, self.COLOR_TEXT, 2)

        header = f'People unsafe: {count}'
        (tw, th), _ = cv2.getTextSize(header, self.FONT, 0.7, 2)
        cv2.rectangle(frame, (10, 10), (10 + tw + 20, 10 + th + 10), (0, 0, 0), -1)
        cv2.putText(frame, header, (20, 30), self.FONT, 0.7, self.COLOR_SAFE, 2)

        return frame
