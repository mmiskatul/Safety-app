import cv2
import base64
from ultralytics import YOLO
from collections import Counter
import numpy as np
from .detect import draw_boxes, class_names

model = YOLO("../model/best.pt")
# model = YOLO("../model/yolo11n (1).pt")

def process_frame(frame_b64):
    img_bytes = base64.b64decode(frame_b64)
    np_img = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
    results = model(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    annotated_frame, cls_ids = draw_boxes(frame.copy(), results[0])
    _, buffer = cv2.imencode(".jpg", annotated_frame)
    encoded_frame = base64.b64encode(buffer).decode("utf-8")
    counts = Counter([class_names[i] for i in cls_ids])
    return encoded_frame, dict(counts)
