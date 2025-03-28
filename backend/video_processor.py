import cv2
import torch
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
from PyQt5.QtGui import QImage
from ultralytics import YOLO

class VideoProcessor(QThread):
    frame_signal = pyqtSignal(QImage)
    recording_signal = pyqtSignal(bool)
    count_update = pyqtSignal(dict)


    def __init__(self, video_path, line_manager):
        super().__init__()
        self.line_manager = line_manager
        self.video_path = video_path
        self.running = True
        self.paused = False
        self.recording = False
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.mutex = QMutex()
        self.pause_condition = QWaitCondition()
        self.cap = None  # Add video capture as instance variable

    def run(self):
        print(f"Using device: {self.device.upper()}")
        model = YOLO("yolov12/new_best.pt").to(self.device)
        self.cap = cv2.VideoCapture(self.video_path)
        
        # Initialize VideoWriter for recording
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = None
        first_frame = True

        while self.cap.isOpened() and self.running:
            self.mutex.lock()
            if self.paused:
                self.pause_condition.wait(self.mutex)
            self.mutex.unlock()

            ret, frame = self.cap.read()
            if not ret:
                break

            # Perform object detection
            results = model.track(frame, persist=True, device=self.device)
            annotated_frame = results[0].plot() if hasattr(results[0], "plot") else frame

            # Process lines and counting
            if self.line_manager and results[0].boxes.id is not None:
                # Set reference size on first frame
                if first_frame:
                    h, w = annotated_frame.shape[:2]
                    self.line_manager.set_reference_size(w, h)
                    first_frame = False

                # Draw all stored lines
                for line_id, line_data in self.line_manager.lines.items():
                    start = line_data['start']
                    end = line_data['end']
                    # Convert coordinates to video resolution
                    start_x = int(start.x() * (w / self.line_manager.reference_width))
                    start_y = int(start.y() * (h / self.line_manager.reference_height))
                    end_x = int(end.x() * (w / self.line_manager.reference_width))
                    end_y = int(end.y() * (h / self.line_manager.reference_height))
                    
                    cv2.line(annotated_frame, 
                            (start_x, start_y),
                            (end_x, end_y),
                            (0, 255, 0), 2)
                    mid_x = (start_x + end_x) // 2
                    mid_y = (start_y + end_y) // 2
                    cv2.putText(annotated_frame, f"Line {line_id}", 
                            (mid_x - 20, mid_y - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                # Check for line crossings
                detections = []
                for box, cls, track_id in zip(results[0].boxes.xyxy, 
                                            results[0].boxes.cls,
                                            results[0].boxes.id):
                    detections.append({
                        'id': track_id.item() if track_id is not None else None,
                        'cls': cls.item(),
                        'box': box.tolist()
                    })
                
                self.line_manager.check_line_crossing(detections, annotated_frame.shape)
                self.count_update.emit(self.line_manager.route_counts.copy())

            # Recording logic
            if self.recording:
                if out is None:
                    h, w, _ = annotated_frame.shape
                    out = cv2.VideoWriter('output.avi', fourcc, 20.0, (w, h))
                out.write(annotated_frame)

            # Convert to QImage
            rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            q_img = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888)
            self.frame_signal.emit(q_img)

        # Cleanup resources
        if self.cap:
            self.cap.release()
        if out:
            out.release()

    def pause(self):
        self.mutex.lock()
        self.paused = True
        self.mutex.unlock()

    def resume(self):
        self.mutex.lock()
        self.paused = False
        self.pause_condition.wakeAll()
        self.mutex.unlock()

    def stop(self):
        self.running = False
        self.resume()  # Wake thread if paused
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.wait()

    def start_recording(self):
        self.mutex.lock()
        self.recording = True
        self.recording_signal.emit(True)
        self.mutex.unlock()

    def stop_recording(self):
        self.mutex.lock()
        self.recording = False
        self.recording_signal.emit(False)
        self.mutex.unlock()
        
