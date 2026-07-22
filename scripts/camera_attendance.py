import json
import time
import urllib.request

import cv2

API_URL = "http://127.0.0.1:8000/api/recognize"

def send_frame(frame):
    success, encoded = cv2.imencode(".jpg", frame)
    if not success:
        return None

    boundary = "----AttendanceBoundary"
    header = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="photo"; filename="camera.jpg"\r\n'
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode()
    footer = f"\r\n--{boundary}--\r\n".encode()
    body = header + encoded.tobytes() + footer

    request = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as error:
        return {"matched": False, "message": f"Server error: {error}"}

camera = cv2.VideoCapture(0)
if not camera.isOpened():
    raise SystemExit("Could not open webcam. Check Windows camera permission.")

last_scan = 0.0
message = "Show your face. Scanning every 3 seconds."

while True:
    ok, frame = camera.read()
    if not ok:
        break

    current_time = time.time()
    if current_time - last_scan >= 3:
        result = send_frame(frame)
        last_scan = current_time
        if result:
            if result.get("matched"):
                student = result["student"]
                message = (
                    f'{student["name"]} ({student["roll_no"]}) - '
                    f'{result["message"]}'
                )
            else:
                message = result.get("message", "Face not recognized.")

    display = frame.copy()
    cv2.rectangle(
        display, (10, 10), (display.shape[1] - 10, 58), (0, 0, 0), -1
    )
    cv2.putText(
        display,
        message[:85],
        (20, 43),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (255, 255, 255),
        2,
    )
    cv2.putText(
        display,
        "Press Q to close",
        (20, display.shape[0] - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
    )
    cv2.imshow("AI Smart Attendance Scanner", display)

    if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
        break

camera.release()
cv2.destroyAllWindows()
