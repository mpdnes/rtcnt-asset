import cv2

def check_cameras():
    index = 0
    arr = []
    while True:
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            break
        ret, frame = cap.read()
        if ret:
            arr.append(index)
        cap.release()
        index += 1
    return arr

cameras = check_cameras()
print(f"Available cameras: {cameras}")

if cameras:
    cap = cv2.VideoCapture(cameras[0])  # Use the first available camera
    if cap.isOpened():
        print(f"Using camera index: {cameras[0]}")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow("Press 'q' to quit", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()
else:
    print("No cameras found.")
