import cv2
import numpy as np

CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def decode_image(data: bytes) -> np.ndarray:
    array = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Invalid image file.")
    return image

def largest_face(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = CASCADE.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
    )
    if len(faces) == 0:
        raise ValueError(
            "No clear face detected. Use a front-facing, well-lit photograph."
        )
    x, y, width, height = max(faces, key=lambda face: face[2] * face[3])
    margin = int(0.12 * max(width, height))
    x1, y1 = max(0, x - margin), max(0, y - margin)
    x2 = min(gray.shape[1], x + width + margin)
    y2 = min(gray.shape[0], y + height + margin)
    return gray[y1:y2, x1:x2]

def embedding_from_image(image: np.ndarray) -> np.ndarray:
    face = largest_face(image)
    face = cv2.resize(face, (64, 64), interpolation=cv2.INTER_AREA)
    face = cv2.equalizeHist(face).astype(np.float32)
    vector = face.flatten()
    vector -= vector.mean()
    norm = np.linalg.norm(vector)
    if norm == 0:
        raise ValueError("The face image contains insufficient detail.")
    return vector / norm

def encode_embedding(vector: np.ndarray) -> bytes:
    return vector.astype(np.float32).tobytes()

def decode_embedding(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)

def similarity(first: np.ndarray, second: np.ndarray) -> float:
    denominator = np.linalg.norm(first) * np.linalg.norm(second) + 1e-8
    return float(np.dot(first, second) / denominator)
