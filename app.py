import sys
from PyQt5.QtWidgets import QApplication
from frontend.video_display import YOLOApp  # Import the GUI application

def main():
    app = QApplication(sys.argv)
    window = YOLOApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
