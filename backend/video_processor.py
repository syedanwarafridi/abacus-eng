import cv2
import torch
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
from PyQt5.QtGui import QImage
from ultralytics import YOLO
import os
import pandas as pd
import gc
from datetime import datetime, timedelta

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
        
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.line_manager.set_video_info(fps, total_frames)
        
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
                print("Detected IDs:", [d["id"] for d in detections])
                
                self.line_manager.check_line_crossing(detections, annotated_frame.shape)
                print("Updated counts:", self.line_manager.route_counts, "###########")
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
            cv2.waitKey(100)

        # Cleanup resources
        if self.cap:
            self.cap.release()
        if out:
            out.release()
        
        # Save results to Excel before finishing
        self.save_results()

    def save_results(self):
        """Save results with timestamps"""
        rows = []
        for (origin, destination), data in self.line_manager.route_counts.items():
            # Find the route info to get the start time
            route_info = next(
                (r for r in self.line_manager.routes 
                if r["origin"] == origin and r["destination"] == destination),
                None
            )
            
            start_time_str = route_info["start_time"] if route_info else "00:00:00 AM"
            
            # Convert string time to datetime
            try:
                start_time = datetime.strptime(start_time_str, "%I:%M:%S %p")
            except ValueError:
                start_time = datetime.strptime("00:00:00 AM", "%I:%M:%S %p")
            
            for cls_id, count in data["counts"].items():
                if count > 0:
                    class_name = self.line_manager.class_names.get(cls_id, f"Class_{cls_id}")
                    # Calculate actual times for each detection
                    for i, sec in enumerate(data.get("times", [])[:count]):
                        detection_time = start_time + timedelta(seconds=sec)
                        time_str = detection_time.strftime("%I:%M:%S %p").lstrip("0")
                        
                        rows.append({
                            "Origin Line": origin,
                            "Destination Line": destination,
                            "Direction": data["direction"],
                            "Vehicle Type": class_name,
                            "Detection Time": time_str,
                            "Frame Number": int(sec * self.line_manager.fps)
                        })
        
        if rows:
            df = pd.DataFrame(rows)
        else:
            df = pd.DataFrame(columns=[
                "Origin Line", "Destination Line", "Direction", 
                "Vehicle Type", "Detection Time", "Frame Number"
            ])
        
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        file_path = os.path.join(downloads_path, "vehicle_results.xlsx")
        df.to_excel(file_path, index=False)
        print(f"Results saved to {file_path}")

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
        # self.cleanup()
        self.resume()
        if self.cap and self.cap.isOpened():
            self.cap.release()
        torch.cuda.empty_cache()
        gc.collect() 
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
