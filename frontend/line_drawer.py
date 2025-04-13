from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPixmap, QPainter, QPen, QImage
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

class LineDrawer(QLabel):
    line_drawn = pyqtSignal(QPoint, QPoint)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lines = []
        self.current_line = []
        self.original_size = QPoint(1, 1)
        self.display_size = QPoint(1, 1)
        self.offset = QPoint(0, 0)

    def load_frame(self, q_img):
        """Store original dimensions and calculate display parameters"""
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

    def calculate_display_size(self, q_img):
        """Determine display size while preserving aspect ratio"""
        max_width = self.width()
        max_height = self.height()
        aspect_ratio = q_img.width() / q_img.height()
        
        # Calculate dimensions that fit within the label while maintaining aspect ratio
        if max_width / max_height > aspect_ratio:
            height = max_height
            width = int(height * aspect_ratio)
        else:
            width = max_width
            height = int(width / aspect_ratio)
            
        return QPoint(width, height)

    def calculate_letterbox_offset(self, q_img):
        """Calculate black bar offsets for centered display"""
        dx = (self.width() - self.display_size.x()) // 2
        dy = (self.height() - self.display_size.y()) // 2
        return QPoint(dx, dy)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Adjust for letterboxing and scale to original coordinates
            adjusted_pos = self.adjust_position(event.pos())
            self.current_line = [adjusted_pos]

    def mouseMoveEvent(self, event):
        if self.current_line:
            adjusted_pos = self.adjust_position(event.pos())
            self.current_line.append(adjusted_pos)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.current_line:
            adjusted_pos = self.adjust_position(event.pos())
            self.current_line.append(adjusted_pos)
            self.lines.append(self.current_line)
            self.line_drawn.emit(self.current_line[0], self.current_line[-1])
            self.current_line = []
            self.update()

    # def adjust_position(self, pos):
    #     """Convert GUI coordinates to original video coordinates"""
    #     # Subtract letterbox offsets
    #     x = pos.x() - self.offset.x()
    #     y = pos.y() - self.offset.y()
        
    #     # Calculate scaling factors
    #     scale_x = self.original_size.x() / self.display_size.x()
    #     scale_y = self.original_size.y() / self.display_size.y()
        
    #     # Scale to original coordinates
    #     return QPoint(
    #         int(x * scale_x),
    #         int(y * scale_y)
    #     )
    def adjust_position(self, pos):
        """Convert GUI coordinates to original video coordinates"""
        # Subtract letterbox offsets
        x = pos.x() - self.offset.x()
        y = pos.y() - self.offset.y()
        
        # Prevent negative coordinates
        x = max(0, x)
        y = max(0, y)
        
        # Calculate scaling factors
        scale_x = self.original_size.x() / self.display_size.x()
        scale_y = self.original_size.y() / self.display_size.y()
        
        # Scale to original coordinates (clamped to video dimensions)
        return QPoint(
            min(int(x * scale_x), self.original_size.x() - 1),
            min(int(y * scale_y), self.original_size.y() - 1)
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
        
        # Draw all stored lines
        for line in self.lines:
            if len(line) >= 2:
                # Convert back to display coordinates for drawing
                start = self.scale_to_display(line[0])
                end = self.scale_to_display(line[-1])
                painter.drawLine(start, end)

    def scale_to_display(self, point):
        """Convert original coordinates back to display coordinates"""
        scale_x = self.display_size.x() / self.original_size.x()
        scale_y = self.display_size.y() / self.original_size.y()
        
        return QPoint(
            int(point.x() * scale_x) + self.offset.x(),
            int(point.y() * scale_y) + self.offset.y()
        )
        
    def clear_lines(self):
        """Clear all stored lines"""
        self.lines = []
        self.current_line = []
        self.update() 
