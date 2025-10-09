# seat_detector.py (enhanced)
# 用 YOLOv8 做“是否有人”检测，增强：
#  - 调高默认分辨率 imgsz=1280，降低 conf=0.20，改善密集人群小目标召回
#  - 暴露 conf/imgsz/iou 参数
#  - 支持保存标注结果图片（可视化检查漏检）
# 依赖：ultralytics, opencv-python, numpy
# 安装：pip install ultralytics opencv-python numpy

from typing import Dict, Any, List, Tuple, Optional
import os
import time
import json
import numpy as np
import cv2
from ultralytics import YOLO

# 模型选择：n/s/m 逐渐更大更准（也更慢）
# 可改为 "yolov8s.pt" 或 "yolov8m.pt" 以提升精度
_MODEL_NAME = "yolov8m.pt"
_CLASS_PERSON = 0

_model: Optional[YOLO] = None

def _get_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO(_MODEL_NAME)
    return _model

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _draw_boxes(img: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
    """在图像上绘制检测框与置信度（仅 person 类别）。"""
    out = img.copy()
    for d in detections:
        if d["cls"] != _CLASS_PERSON:
            continue
        x1, y1, x2, y2 = map(int, d["xyxy"])
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 0, 255), 2)
        label = f"person {d['conf']:.2f}"
        (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(out, (x1, y1 - th - 6), (x1 + tw + 6, y1), (0, 0, 255), -1)
        cv2.putText(out, label, (x1 + 3, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
    return out

def detect_from_bytes(
    image_bytes: bytes,
    conf: float = 0.10,
    imgsz: int = 1280,
    iou: float = 0.45,
    save_annotated: bool = False,
    save_dir: str = "runs/annotated",
) -> Dict[str, Any]:
    """
    传入图片字节，返回占用结果与检测框列表。
    参数：
      - conf: 置信度阈值（越低越不易漏检，但可能多检）
      - imgsz: 推理输入分辨率（越大越清晰，但更耗时）
      - iou: NMS 阈值
      - save_annotated: 是否保存带框可视化图片
      - save_dir: 保存目录
    返回：
      {
        "occupied": true,
        "persons": 12,
        "detections": [ {cls, conf, xyxy}, ... ],
        "annotated_path": "runs/annotated/xxxx.jpg"  # 若保存
      }
    """
    # 解码图片
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("无法解析图像数据，请确认上传的是有效图片文件。")

    model = _get_model()
    results = model.predict(img, conf=conf, iou=iou, imgsz=imgsz, verbose=False)

    detections: List[Dict[str, Any]] = []
    person_count = 0

    h, w = img.shape[:2]

    for r in results:
        # r.boxes.xyxy, r.boxes.conf, r.boxes.cls
        if r.boxes is None:
            continue
        for b in r.boxes:
            cls = int(b.cls.item()) if hasattr(b.cls, "item") else int(b.cls)
            conf_v = float(b.conf.item()) if hasattr(b.conf, "item") else float(b.conf)
            if hasattr(b.xyxy, "tolist"):
                xyxy = b.xyxy[0].tolist()
            else:
                xyxy = list(b.xyxy[0])
            # 限制到图像范围并保留两位小数
            x1, y1, x2, y2 = xyxy
            x1 = max(0.0, min(float(x1), float(w - 1)))
            y1 = max(0.0, min(float(y1), float(h - 1)))
            x2 = max(0.0, min(float(x2), float(w - 1)))
            y2 = max(0.0, min(float(y2), float(h - 1)))
            xyxy = [round(x1,2), round(y1,2), round(x2,2), round(y2,2)]

            detections.append({"cls": cls, "conf": round(conf_v,3), "xyxy": xyxy})
            if cls == _CLASS_PERSON:
                person_count += 1

    annotated_path = None
    if save_annotated:
        _ensure_dir(save_dir)
        ts = time.strftime("%Y%m%d-%H%M%S")
        annotated_path = os.path.join(save_dir, f"det-{ts}.jpg")
        vis = _draw_boxes(img, detections)
        cv2.imwrite(annotated_path, vis)

    result = {
        "occupied": person_count > 0,
        "persons": person_count,
        "detections": detections
    }
    if annotated_path:
        result["annotated_path"] = annotated_path
    return result

def detect_file(path: str, **kwargs) -> Dict[str, Any]:
    """从本地图片路径读取并检测，kwargs 透传给 detect_from_bytes。"""
    with open(path, "rb") as f:
        return detect_from_bytes(f.read(), **kwargs)

if __name__ == "__main__":
    # 用法: python seat_detector.py <image_path> [--save]
    import sys
    save = False
    if len(sys.argv) < 2:
        print("用法: python seat_detector.py <image_path> [--save]")
        sys.exit(1)
    if len(sys.argv) >= 3 and sys.argv[2] == "--save":
        save = True
    res = detect_file(sys.argv[1], save_annotated=save)
    print(json.dumps(res, ensure_ascii=False, indent=2))
