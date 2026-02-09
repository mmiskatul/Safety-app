import os
import cv2
from ultralytics import YOLO
from collections import Counter
import numpy as np

# model = YOLO("../model/yolo11n(1).pt")
model = YOLO("../model/best.pt")

if not model.names:
    model.names = {0: "Mask", 1: "Helmet", 2: "Vest", 3: "Boots", 4: "Person"}
    #  model.names = {0: "Hardhat", 1: "Mask", 2: "NO-Hardhat", 3: "NO-Mask", 4: "NO-Safety Vest", 5: "Person",7:"Safety Vest"}

class_names = model.names

def draw_boxes(frame, results):
    cls_ids = results.boxes.cls.cpu().numpy().astype(int)
    confs = results.boxes.conf.cpu().numpy()
    boxes = results.boxes.xyxy.cpu().numpy()
    for cls_id, conf, box in zip(cls_ids, confs, boxes):
        x1, y1, x2, y2 = map(int, box)
        color = (0, 255, 0) if conf > 0.5 else (0, 0, 255)  # green/red
        label = f"{class_names.get(cls_id,'Unknown')} ({conf:.2f})"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return frame, cls_ids

def detect_image(image_path, original_filename="detected_image"):
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = model(image_rgb)
    annotated_image, cls_ids = draw_boxes(image_rgb.copy(), results[0])

    os.makedirs("app/output", exist_ok=True)
    output_path = os.path.join("app/output", f"{original_filename}_detected.jpg")
    cv2.imwrite(output_path, cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))

    detections = []
    for b, cls_id, conf in zip(results[0].boxes.xyxy.cpu().numpy(),
                               results[0].boxes.cls.cpu().numpy().astype(int),
                               results[0].boxes.conf.cpu().numpy()):
        detections.append({
            "x1": float(b[0]), "y1": float(b[1]),
            "x2": float(b[2]), "y2": float(b[3]),
            "confidence": float(conf),
            "class_id": int(cls_id),
            "class_name": class_names.get(int(cls_id), "Unknown")
        })

    counts = Counter([d["class_name"] for d in detections])
    return annotated_image, detections, dict(counts), output_path

def detect_video(video_path):
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    os.makedirs("app/output", exist_ok=True)
    base_name = os.path.basename(video_path).split('.')[0]
    output_path = os.path.join("app/output", f"{base_name}_detected.mp4")
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    total_counts = Counter()
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = model(frame_rgb)
        annotated_frame, cls_ids = draw_boxes(frame_rgb.copy(), results[0])
        out.write(cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR))
        total_counts.update([class_names[i] for i in cls_ids])

    cap.release()
    out.release()
    return output_path, dict(total_counts)
