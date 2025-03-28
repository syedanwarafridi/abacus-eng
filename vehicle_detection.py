from ultralytics import YOLO
import cv2

# Load the YOLO model
model = YOLO('new_best.pt')

# Open the video file
video_path = "73.mp4"
cap = cv2.VideoCapture(video_path)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break  # Exit if the video ends

    # Perform detection
    results = model.track(frame)
    print("Results", results)
    
    # Get the annotated frame
    annotated_frame = results[0].plot()

    resized_frame = cv2.resize(annotated_frame, (800, 600))
    # Show the video
    cv2.imshow("YOLO Detection", resized_frame)

    # Press 'q' to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
