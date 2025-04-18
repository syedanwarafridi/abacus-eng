import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QProgressBar, QFrame
)
from PyQt5.QtGui import QFont, QPainter
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg
import random


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Intersection G23")
        self.setGeometry(100, 100, 400, 700)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Intersection G23")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # CPU and Memory Gauges (simulated with QProgressBar)
        gauge_layout = QHBoxLayout()
        self.cpu_bar = self.create_gauge("CPU", 77)
        self.mem_bar = self.create_gauge("Memory", 38)
        gauge_layout.addLayout(self.cpu_bar)
        gauge_layout.addLayout(self.mem_bar)
        layout.addLayout(gauge_layout)

        # Usage History Graph
        graph_label = QLabel("Usage History")
        graph_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(graph_label)

        self.plot = pg.PlotWidget()
        self.plot.setYRange(0, 100)
        self.data = [random.randint(10, 40) for _ in range(50)]
        self.curve = self.plot.plot(self.data, pen='c')
        layout.addWidget(self.plot)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(500)

        # System Usage Details
        details_label = QLabel("Details")
        details_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(details_label)

        layout.addWidget(self.usage_label("System", 16, "red"))
        layout.addWidget(self.usage_label("User", 23, "blue"))
        layout.addWidget(self.usage_label("Idle", 61, "gray"))

        # Top Processes
        top_label = QLabel("Top processes")
        top_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(top_label)

        layout.addWidget(self.usage_label("SuperCrash", 42.5))
        layout.addWidget(self.usage_label("decoder_hyperisk", 18.5))
        layout.addWidget(self.usage_label("Coolpad", 4.6))
        layout.addWidget(self.usage_label("ZamuroVid", 2.4))
        layout.addWidget(self.usage_label("Safari", 2.4))

        # Spacer
        layout.addStretch()

        # Footer
        footer = QVBoxLayout()
        footer.addWidget(QLabel("FPS Video:        20"))
        footer.addWidget(QLabel("Processing time:  1:05:12"))
        footer.addWidget(QLabel("Est. Remaing time: 0:23:00"))

        layout.addLayout(footer)

        self.setLayout(layout)

    def create_gauge(self, label_text, value):
        layout = QVBoxLayout()
        label = QLabel(f"{label_text}: {value}%")
        label.setAlignment(Qt.AlignCenter)
        bar = QProgressBar()
        bar.setMaximum(100)
        bar.setValue(value)
        layout.addWidget(label)
        layout.addWidget(bar)
        return layout

    def usage_label(self, name, value, color=None):
        label = QLabel(f"{name}: {value}%")
        if color:
            label.setStyleSheet(f"color: {color}")
        return label

    def update_plot(self):
        self.data = self.data[1:] + [random.randint(10, 80)]
        self.curve.setData(self.data)

