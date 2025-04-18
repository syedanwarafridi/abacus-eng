import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QFileDialog, 
    QHBoxLayout, QStyle, QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem, QFrame, QGridLayout
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QPoint
from backend.video_processor import VideoProcessor
from backend.line_manager import LineManager
from frontend.line_drawer import LineDrawer
import cv2
import json
import os
from frontend.analytics import Dashboard

class YOLOApp(QWidget):
    """Main PyQt5 GUI Application with structured 3-column layout"""
    def __init__(self):
        super().__init__()
        self.video_path = None
        self.processor = None
        self.line_manager = LineManager()
        self.class_names = {
            0: "Passenger Car", 1: "Motorbike", 2: "Van",
            3: "Truck", 4: "Large Truck", 5: "Bus", 6: "Minibus"
        }
        self.directions = {} 
        
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        main_layout = QHBoxLayout()
    
        # Column 1: Video and Controls (70% width)
        col1 = QVBoxLayout()
        self.video_label = LineDrawer(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Button Layout
        button_layout = self.create_button_layout()
        
        # Add components to column 1 with stretch factors
        col1.addWidget(self.video_label, 70)  # 70% of column height
        col1.addLayout(button_layout, 10)     # 10% height for buttons
        col1.addWidget(self.create_route_table(), 20)  # 20% height for route table
        
        # Column 2: Placeholder
        col2 = Dashboard()
        
        # Column 3: Vehicle Counts
        col3 = QVBoxLayout()
        count_layout = self.create_count_layout()
        col3.addLayout(count_layout)
        col3.addStretch()
        
        # Configure main layout proportions
        main_layout.addLayout(col1, 60)  # 60% width
        main_layout.addWidget(col2, 20)  # 20% width
        main_layout.addLayout(col3, 20)  # 20% width
        
        self.setLayout(main_layout)
        self.setWindowTitle("YOLO Vehicle Detection")
        self.setGeometry(200, 200, 1200, 800)
        self.setStyleSheet("background-color: white;")

    def create_button_layout(self):
        layout = QHBoxLayout()
        self.load_button = QPushButton()
        self.play_button = QPushButton()
        self.pause_button = QPushButton()
        self.stop_button = QPushButton()
        self.record_button = QPushButton()
        self.draw_line_button = QPushButton("Draw Line")
        
        # Set icons
        icons = self.style().standardIcon
        self.load_button.setIcon(icons(QStyle.SP_DirOpenIcon))
        self.play_button.setIcon(icons(QStyle.SP_MediaPlay))
        self.pause_button.setIcon(icons(QStyle.SP_MediaPause))
        self.stop_button.setIcon(icons(QStyle.SP_MediaStop))
        self.record_button.setIcon(icons(QStyle.SP_DialogApplyButton))
        
        # Add buttons to layout
        buttons = [
            self.play_button, self.pause_button, self.stop_button,
            self.record_button, self.draw_line_button, self.load_button
        ]
        for btn in buttons:
            btn.setFixedSize(40, 40) if btn != self.draw_line_button else None
            layout.addWidget(btn)
        
        return layout

    def create_count_layout(self):
        """Create direction-based count display"""
        layout = QVBoxLayout()
        self.count_labels = {}
        
        # Will be populated when routes are loaded
        layout.addWidget(QLabel("<b>Direction Counts</b>"))
        self.count_container = QVBoxLayout()
        layout.addLayout(self.count_container)
        
        return layout

    def connect_signals(self):
        self.load_button.clicked.connect(self.load_video)
        self.play_button.clicked.connect(self.start_detection)
        self.pause_button.clicked.connect(self.pause_video)
        self.stop_button.clicked.connect(self.stop_video)
        self.record_button.clicked.connect(self.toggle_recording)
        self.draw_line_button.clicked.connect(self.start_drawing)
        self.video_label.line_drawn.connect(self.store_line)
    ################################################################
        
    def update_counts(self, route_counts):
        # Clear the entire layout of count cards
        while self.count_container.count():
            item = self.count_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Recursively clear child layouts if any
                def clear_layout(layout):
                    while layout.count():
                        child = layout.takeAt(0)
                        if child.widget():
                            child.widget().deleteLater()
                        elif child.layout():
                            clear_layout(child.layout())
                clear_layout(item.layout())

        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        max_cards = 12
        num_directions = min(len(route_counts), max_cards)

        card_colors = [
            "#dff0d8",  # Light green for top-left
            "#fde4e5",  # Soft pink
            "#ece4f5",  # Lavender/purple
            "#fbeedb",  # Light peach/orange
            "#dff0d8",  # Green again for second row, first col
            "#fde4e5",  # Pink
            "#ece4f5",  # Purple
            "#fbeedb",  # Orange
            "#dff0d8",  # Green
            "#fde4e5",  # Pink
            "#ece4f5",  # Purple
            "#fbeedb",  # Orange
        ]

        route_items = list(route_counts.items())  # [(key, {"direction":..., "counts":...}), ...]

        for i in range(num_directions):
            route_key, data = route_items[i]
            direction_name = data["direction"]
            counts = data["counts"]

            card_frame = QFrame()
            card_frame.setStyleSheet("""
                QFrame {
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }
            """)
            card_layout = QVBoxLayout(card_frame)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(0)

            header_color = card_colors[i % len(card_colors)]
            header_frame = QFrame()
            header_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {header_color};
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    min-height: 30px;
                }}
            """)
            header_layout = QHBoxLayout(header_frame)
            header_layout.setContentsMargins(8, 2, 8, 2)

            direction_label = QLabel(direction_name)
            direction_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 14px;
                    color: #333;
                }
            """)
            header_layout.addWidget(direction_label, alignment=Qt.AlignCenter)

            card_layout.addWidget(header_frame)

            body_frame = QFrame()
            body_layout = QVBoxLayout(body_frame)
            body_layout.setContentsMargins(10, 8, 10, 8)
            body_layout.setSpacing(6)

            for cls_id in range(7):
                row_hbox = QHBoxLayout()
                row_hbox.setSpacing(10)

                # Icon
                icon_filename = f"{self.class_names[cls_id].replace(' ', '_')}.png"
                icon_path = os.path.join("icons", icon_filename)

                icon_label = QLabel()
                if os.path.exists(icon_path):
                    pixmap = QPixmap(icon_path).scaled(
                        30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    icon_label.setPixmap(pixmap)
                else:
                    icon_label.setText("[X]")  # fallback if icon doesn't exist
                row_hbox.addWidget(icon_label, alignment=Qt.AlignLeft)

                # Count label
                count_value = counts.get(cls_id, 0)
                count_label = QLabel(str(count_value))
                count_label.setStyleSheet("""
                    QLabel {
                        font-size: 13px;
                        color: #333;
                    }
                """)
                row_hbox.addWidget(count_label, alignment=Qt.AlignLeft)

                body_layout.addLayout(row_hbox)

            card_layout.addWidget(body_frame)

            # Round the bottom corners of the card
            body_frame.setStyleSheet("""
                QFrame {
                    border-bottom-left-radius: 4px;
                    border-bottom-right-radius: 4px;
                }
            """)

            row = i // 4
            col = i % 4
            grid_layout.addWidget(card_frame, row, col)

        # Add the new grid layout to the count container
        self.count_container.addLayout(grid_layout)
            
    def start_drawing(self):
        """Enables line drawing mode."""
        self.video_label.setCursor(Qt.CrossCursor)

    def store_line(self, start, end):
        """Directly use the already-scaled coordinates from LineDrawer"""
        self.line_manager.add_line(start, end)
        print(f"Line added at original coordinates: {start.x()},{start.y()} to {end.x()},{end.y()}")

    def load_video(self):
        """Loads the first frame from the video."""
        self.stop_video()  # Clear previous state
        
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video Files (*.mp4 *.avi *.mov)")
        if file_path:
            # Full reset for new video
            self.line_manager.reset()
            self.video_label.clear()
            self.video_label.clear_lines()
            self.route_table.setRowCount(0)
            self.update_counts({})  # Clear direction counts
            
            self.video_path = file_path
            cap = cv2.VideoCapture(self.video_path)
            ret, frame = cap.read()
            cap.release()

            if ret:
                # Convert and display first frame
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame_rgb.shape
                q_img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
                
                # Force frame update
                self.video_label.load_frame(q_img)
                self.video_label.repaint()
                
                # Load existing routes if available
                video_name = os.path.basename(file_path)
                if os.path.exists("routes.json"):
                    with open("routes.json", "r") as f:
                        data = json.load(f)
                        if video_name in data:
                            self.load_routes_to_table(data[video_name])

    def start_detection(self):
        """Starts or resumes the video processing."""
        if self.video_path:
            if self.processor is None:
                self.processor = VideoProcessor(self.video_path, self.line_manager)
                self.processor.frame_signal.connect(self.update_frame)
                self.processor.count_update.connect(self.update_counts)
                self.processor.start()
            elif self.processor.isRunning() and self.processor.paused:
                self.processor.resume()

    def pause_video(self):
        """Pauses the video processing."""
        if self.processor and self.processor.isRunning():
            self.processor.pause()

    def stop_video(self):
        """Enhanced to clear routes"""
        if self.processor:
            self.processor.stop()
            self.processor = None
            
        self.video_label.clear()
        self.video_label.setText("Video Stopped - Load New Video")
        self.video_path = None
        self.route_table.setRowCount(0)  # Clear route table
        self.line_manager.reset()
        self.update_counts({}) 

    def toggle_recording(self):
        """Toggles video recording on/off."""
        if self.processor and self.processor.isRunning():
            if not self.processor.recording:
                self.processor.start_recording()
                self.record_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
            else:
                self.processor.stop_recording()
                self.record_button.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))

    def update_frame(self, q_img):
        """Scale frame to fit container while maintaining aspect ratio"""
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(
            self.video_label.width(),
            self.video_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

    def closeEvent(self, event):
        """Ensures the video processing stops when the app closes."""
        if self.processor and self.processor.isRunning():
            self.processor.stop()
        event.accept()

    def create_route_table(self):
        """Create the route input table and controls"""
        route_group = QWidget()
        layout = QVBoxLayout()
        
        # Table
        self.route_table = QTableWidget()
        self.route_table.setColumnCount(4)
        self.route_table.setHorizontalHeaderLabels(["Origin Line", "Destination Line", "Direction", "Start Time (HH:MM:SS AM/PM)"])
        self.route_table.horizontalHeader().setStretchLastSection(True)
        
        # Controls
        control_layout = QHBoxLayout()
        add_btn = QPushButton("Add Route")
        del_btn = QPushButton("Delete Route")
        save_btn = QPushButton("Save Routes")
        
        add_btn.clicked.connect(lambda: self.route_table.insertRow(self.route_table.rowCount()))
        del_btn.clicked.connect(lambda: self.route_table.removeRow(self.route_table.currentRow()))
        save_btn.clicked.connect(self.save_routes)
        
        control_layout.addWidget(add_btn)
        control_layout.addWidget(del_btn)
        control_layout.addWidget(save_btn)
        
        layout.addWidget(QLabel("<b>Route Configuration</b>"))
        layout.addWidget(self.route_table)
        layout.addLayout(control_layout)
        
        route_group.setLayout(layout)
        return route_group
    
    def save_routes(self):
        """Save routes with direction-based counting"""
        try:
            routes = []
            valid = True
            
            for row in range(self.route_table.rowCount()):
                origin = self.route_table.item(row, 0).text() if self.route_table.item(row, 0) else ""
                dest = self.route_table.item(row, 1).text() if self.route_table.item(row, 1) else ""
                direction = self.route_table.item(row, 2).text() if self.route_table.item(row, 2) else ""
                start_time = self.route_table.item(row, 3).text() if self.route_table.item(row, 3) else ""

                if not all([origin, dest, direction, start_time]):
                    valid = False
                    break
                    
                try:
                    routes.append({
                        "origin": int(origin.replace("Line ", "").strip()),
                        "destination": int(dest.replace("Line ", "").strip()),
                        "direction": direction,
                        "start_time": start_time
                    })
                except ValueError:
                    valid = False
                    break

            if valid and routes:
                # Update line manager with verification
                self.line_manager.load_routes(routes)
                
                # Save to JSON
                video_name = os.path.basename(self.video_path)
                data = {}
                if os.path.exists("routes.json"):
                    with open("routes.json", "r") as f:
                        data = json.load(f)
                
                data[video_name] = routes
                with open("routes.json", "w") as f:
                    json.dump(data, f, indent=4)
                    
                # Refresh UI counts
                self.update_counts(self.line_manager.route_counts)
                
        except Exception as e:
            print(f"Route Error: {str(e)}")

    def load_routes_to_table(self, routes):
        """Load routes from JSON into table"""
        try:
            self.route_table.setRowCount(0)
            for route in routes:
                row = self.route_table.rowCount()
                self.route_table.insertRow(row)
                
                self.route_table.setItem(row, 0, QTableWidgetItem(f"Line {route['origin']}"))
                self.route_table.setItem(row, 1, QTableWidgetItem(f"Line {route['destination']}"))
                self.route_table.setItem(row, 2, QTableWidgetItem(route['direction']))
                
        except Exception as e:
            print(f"Error loading routes: {str(e)}")
            
    def load_frame(self, q_img):
        """Store original dimensions and calculate display parameters"""
        # Clear previous content
        self.clear()
        
        # Original video dimensions
        self.original_size = QPoint(q_img.width(), q_img.height())
        
        # Calculate display size with aspect ratio preservation
        self.display_size = self.calculate_display_size(q_img)
        self.offset = self.calculate_letterbox_offset(q_img)
        
        # Create and display pixmap
        pixmap = QPixmap.fromImage(q_img).scaled(
            self.display_size.x(), 
            self.display_size.y(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.setPixmap(pixmap)
        self.setAlignment(Qt.AlignCenter)
