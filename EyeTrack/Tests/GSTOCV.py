import cv2

pipeline = (
    "aravissrc ! "
    "video/x-raw,format=GRAY8,width=640,height=480,framerate=120/1 ! "
    "videoconvert ! appsink"
)

cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    cv2.imshow("cam", frame)
    if cv2.waitKey(1) == 27:
        break
