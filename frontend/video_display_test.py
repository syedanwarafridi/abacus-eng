# frontend/main.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QFileDialog,
    QHBoxLayout, QStyle, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QDialogButtonBox, QFormLayout
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, pyqtSignal
from backend.video_processor_test import VideoProcessor
import random

class LineConfigDialog(QDialog):
    def __init__(self, line_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configure Line {line_id}")
        self.line_id = line_id
        
        layout = QFormLayout()
        self.origin_edit = QLineEdit()
        self.destination_edit = QLineEdit()
        self.direction_edit = QLineEdit()
        
        layout.addRow("Origin Line ID:", self.origin_edit)
        layout.addRow("Destination Line ID:", self.destination_edit)
        layout.addRow("Direction:", self.direction_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addRow(buttons)
        self.setLayout(layout)

class YOLOApp(QWidget):
    def __init__(self):
        super().__init__()
        self.video_path = None
        self.processor = None
        self.lines = []
        self.current_line = None
        self.drawing = False
        self.next_line_id = 1
        self.direction_rules = []
        
        self.init_ui()
        
    def init_ui(self):
        self.video_label = QLabel("No Video Loaded")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.mousePressEvent = self.mouse_press
        self.video_label.mouseMoveEvent = self.mouse_move
        self.video_label.mouseReleaseEvent = self.mouse_release

        # Buttons
        self.load_btn = QPushButton("Load Video")
        self.draw_btn = QPushButton("Draw Lines")
        self.play_btn = QPushButton()
        self.pause_btn = QPushButton()
        self.stop_btn = QPushButton()
        self.config_btn = QPushButton("Configure Directions")
        
        # Table
        self.direction_table = QTableWidget(0, 3)
        self.direction_table.setHorizontalHeaderLabels(["Origin", "Destination", "Direction"])
        self.direction_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Button icons
        self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.pause_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))

        # Layout
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.stop_btn)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.video_label)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.load_btn)
        main_layout.addWidget(self.draw_btn)
        main_layout.addWidget(self.config_btn)
        main_layout.addWidget(self.direction_table)
        
        self.setLayout(main_layout)
        self.setWindowTitle("Vehicle Direction Counter")
        self.setGeometry(100, 100, 800, 600)

        # Connections
        self.load_btn.clicked.connect(self.load_video)
        self.draw_btn.clicked.connect(self.toggle_drawing)
        self.play_btn.clicked.connect(self.start_processing)
        self.pause_btn.clicked.connect(self.pause_processing)
        self.stop_btn.clicked.connect(self.stop_processing)
        self.config_btn.clicked.connect(self.configure_directions)
#----------------------------------------------------------------------------------#        
    def load_video(self):
        """Handle video file loading"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Video", "", "Video Files (*.mp4 *.avi *.mov)"
        )
        if file_path:
            self.video_path = file_path
            self.video_label.setText(f"Loaded: {file_path.split('/')[-1]}")
            
            # Enable controls
            self.draw_btn.setEnabled(True)
            self.play_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)

    def pause_processing(self):
        """Pause video processing"""
        if self.processor and self.processor.isRunning():
            self.processor.pause()
            self.pause_btn.setEnabled(False)
            self.play_btn.setEnabled(True)

    def stop_processing(self):
        """Stop processing and reset UI"""
        if self.processor:
            self.processor.stop()
            self.processor.wait()
            self.processor = None
        
        # Reset UI elements
        self.video_label.clear()
        self.video_label.setText("Video Stopped - Load New Video")
        self.direction_table.setRowCount(0)
        self.lines.clear()
        self.next_line_id = 1
        
        # Update button states
        self.play_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.draw_btn.setEnabled(False)
        self.config_btn.setEnabled(False)
        self.draw_btn.setStyleSheet("")

    def update_counts(self, counts):
        """Update direction counts display"""
        for direction, count in counts.items():
            found = False
            # Update existing row if found
            for row in range(self.direction_table.rowCount()):
                if self.direction_table.item(row, 2).text() == direction:
                    self.direction_table.item(row, 3).setText(
                        str(int(self.direction_table.item(row, 3).text()) + count)
                    )
                    found = True
                    break
            
            # Add new row if not found
            if not found:
                row = self.direction_table.rowCount()
                self.direction_table.insertRow(row)
                self.direction_table.setItem(row, 0, QTableWidgetItem(""))
                self.direction_table.setItem(row, 1, QTableWidgetItem(""))
                self.direction_table.setItem(row, 2, QTableWidgetItem(direction))
                self.direction_table.setItem(row, 3, QTableWidgetItem(str(count)))
                
    def toggle_drawing(self):
        self.drawing = not self.drawing
        self.draw_btn.setStyleSheet("background: #4CAF50" if self.drawing else "")

    def mouse_press(self, event):
        if self.drawing and event.button() == Qt.LeftButton:
            self.current_line = {
                'id': self.next_line_id,
                'points': [self.scale_point(event.pos())],
                'color': QColor(*random_color())
            }

    def mouse_move(self, event):
        if self.drawing and self.current_line:
            self.update()

    def mouse_release(self, event):
        if self.drawing and self.current_line:
            self.current_line['points'].append(self.scale_point(event.pos()))
            self.lines.append(self.current_line)
            self.next_line_id += 1
            self.current_line = None
            self.update()

    def scale_point(self, point):
        # Convert widget coordinates to video coordinates
        if self.video_label.pixmap():
            pmap = self.video_label.pixmap()
            scale_w = pmap.width() / self.video_label.width()
            scale_h = pmap.height() / self.video_label.height()
            return (int(point.x() * scale_w), int(point.y() * scale_h))
        return (point.x(), point.y())

    def configure_directions(self):
        dialog = LineConfigDialog(len(self.direction_rules)+1)
        if dialog.exec_():
            origin = dialog.origin_edit.text()
            destination = dialog.destination_edit.text()
            direction = dialog.direction_edit.text()
            self.direction_table.insertRow(self.direction_table.rowCount())
            self.direction_table.setItem(self.direction_table.rowCount()-1, 0, QTableWidgetItem(origin))
            self.direction_table.setItem(self.direction_table.rowCount()-1, 1, QTableWidgetItem(destination))
            self.direction_table.setItem(self.direction_table.rowCount()-1, 2, QTableWidgetItem(direction))
            self.direction_rules.append((int(origin), int(destination), direction))

    def start_processn(self):
        """Starts or resumes the video processing."""
        if self.video_path:
            if self.processor is None:
                self.processor = VideoProcessor(self.video_path)
                self.processor.frame_signal.connect(self.update_frame)
                self.processor.start()
            elif self.processor.isRunning() and self.processor.paused:
                self.processor.resume()

    def update_frame(self, q_img):
        pixmap = QPixmap.fromImage(q_img)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw current line
        if self.current_line:
            pen = QPen(self.current_line['color'], 2)
            painter.setPen(pen)
            painter.drawLine(*self.current_line['points'][0], *self.points[1])
        
        # Draw all stored lines
        for line in self.lines:
            pen = QPen(line['color'], 2)
            painter.setPen(pen)
            painter.drawLine(*line['points'][0], *line['points'][1])
            painter.drawText(line['points'][0][0], line['points'][0][1], str(line['id']))
        
        painter.end()
        self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio))

    def update_counts(self, counts):
        # Update your UI with new counts here
        pass

    # Remaining methods (load_video, pause_processing, stop_processing) same as before

def random_color():
    return (random.randint(0,255), (random.randint(0,255)), (random.randint(0,255)))

# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = YOLOApp()
#     window.show()
#     sys.exit(app.exec_())