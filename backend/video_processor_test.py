# backend/video_processor.py
import cv2
import torch
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition, Qt
from PyQt5.QtGui import QImage
from ultralytics import YOLO
from collections import defaultdict

class VideoProcessor(QThread):
    frame_signal = pyqtSignal(QImage)
    count_signal = pyqtSignal(dict)

    def __init__(self, video_path, lines, direction_rules):
        super().__init__()
        self.video_path = video_path
        self.lines = lines
        self.direction_rules = direction_rules
        self.running = True
        self.paused = False
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.mutex = QMutex()
        self.pause_condition = QWaitCondition()
        self.cap = None
        self.track_history = defaultdict(lambda: {
            'path': [],
            'crossed_lines': set(),
            'counted': False
        })

    def run(self):
        print(f"Using device: {self.device.upper()}")
        model = YOLO("yolov12/new_best.pt").to(self.device)
        self.cap = cv2.VideoCapture(self.video_path)

        while self.cap.isOpened() and self.running:
            self.mutex.lock()
            if self.paused:
                self.pause_condition.wait(self.mutex)
            self.mutex.unlock()

            ret, frame = self.cap.read()
            if not ret:
                break

            results = model.track(frame, persist=True, device=self.device)
            annotated_frame = results[0].plot() if hasattr(results[0], "plot") else frame
            
            # Draw user-defined lines
            for line in self.lines:
                start = tuple(line['points'][0])
                end = tuple(line['points'][1])
                cv2.line(annotated_frame, start, end, (0,255,0), 2)
                cv2.putText(annotated_frame, str(line['id']), start, 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)

            # Process detections
            boxes = results[0].boxes.xywh.cpu()
            track_ids = results[0].boxes.id.int().cpu().tolist() if results[0].boxes.id else []

            for box, track_id in zip(boxes, track_ids):
                x, y, w, h = box
                center = (float(x), float(y))
                
                # Update track history
                self.track_history[track_id]['path'].append(center)
                if len(self.track_history[track_id]['path']) > 30:
                    self.track_history[track_id]['path'].pop(0)
                
                # Check line crossings
                current_crossings = set()
                for line in self.lines:
                    if self.check_line_crossing(self.track_history[track_id]['path'], line['points']):
                        current_crossings.add(line['id'])
                
                new_crossings = current_crossings - self.track_history[track_id]['crossed_lines']
                self.track_history[track_id]['crossed_lines'] = current_crossings
                
                # Check direction rules
                if not self.track_history[track_id]['counted'] and new_crossings:
                    for origin, destination, direction in self.direction_rules:
                        if origin in new_crossings and destination in current_crossings:
                            self.count_signal.emit({direction: 1})
                            self.track_history[track_id]['counted'] = True
                            break

            # Convert to QImage
            rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            q_img = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888)
            self.frame_signal.emit(q_img)

        if self.cap:
            self.cap.release()

    def check_line_crossing(self, path, line_points):
        if len(path) < 2:
            return False
            
        line_start = line_points[0]
        line_end = line_points[1]
        
        # Convert points to tuples
        line_start = (line_start[0], line_start[1])
        line_end = (line_end[0], line_end[1])
        
        for i in range(1, len(path)):
            a = (int(path[i-1][0]), int(path[i-1][1]))
            b = (int(path[i][0]), int(path[i][1]))
            if self.intersect(a, b, line_start, line_end):
                return True
        return False

    def ccw(self, A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

    def intersect(self, A, B, C, D):
        return self.ccw(A,C,D) != self.ccw(B,C,D) and self.ccw(A,B,C) != self.ccw(A,B,D)

    def stop(self):
        self.running = False
        self.resume()
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.wait()