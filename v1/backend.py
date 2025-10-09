# backend.py
# FastAPI 后端，提供：
#  - /api/check_seat ：简单是否有人
#  - /api/check_map  ：依据 seat_map.json 将人映射到座位编号（归一化矩形）
#  新增：
#  - 支持查询参数 save=1/true 保存带框图片；并通过 /static/ 暴露给前端显示
#  - 返回 annotated_url 字段（若保存）
#
# 依赖：fastapi, uvicorn, ultralytics, opencv-python, numpy
# 安装：pip install fastapi uvicorn ultralytics opencv-python numpy
from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import os
from typing import Dict, List, Any, Tuple

import numpy as np
import cv2

from seat_detector import detect_from_bytes

ANNOT_DIR = "runs/annotated"

app = FastAPI(title="Seat Detection MVP", version="0.3.0")
本
# # 允许地前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件：把保存的标注图片通过 /static/ 暴露
if not os.path.exists(ANNOT_DIR):
    os.makedirs(ANNOT_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=ANNOT_DIR), name="static")

@app.get("/health")
def health():
    return {"status": "ok"}

def _boolish(x: str | None) -> bool:
    if x is None:
        return False
    return x.lower() in ("1", "true", "yes", "y", "t")

@app.post("/api/check_seat")
async def check_seat(
    file: UploadFile = File(...),
    save: str | None = Query(default=None, description="是否保存标注图：1/true/yes"),
):
    """
    上传一张座位图片（含或不含人），返回：{occupied: bool, persons: int, annotated_url?}
    可选查询参数 ?save=1 保存带框图，并通过 /static/ 对外可见。
    """
    data = await file.read()
    want_save = _boolish(save)
    res = detect_from_bytes(data, save_annotated=want_save, save_dir=ANNOT_DIR)
    out = {"occupied": res["occupied"], "persons": res["persons"]}
    if want_save and "annotated_path" in res:
        # annotated_path 例如 runs/annotated/det-xxxx.jpg
        fname = os.path.basename(res["annotated_path"])
        out["annotated_url"] = f"/static/{fname}"
    return out

# --- 座位映射工具 ---

def load_seat_map(path: str = "seat_map.json") -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到座位映射文件：{path}")
    with open(path, "r", encoding="utf-8") as f:
        m = json.load(f)
    if "seats" not in m or not isinstance(m["seats"], list):
        raise ValueError("seat_map.json 格式错误：需要包含 seats 数组")
    return m

def decode_shape(image_bytes: bytes) -> Tuple[int, int]:
    """返回 (h, w)"""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("无法解析图像数据，请确认上传的是有效图片文件。")
    h, w = img.shape[:2]
    return h, w

def bbox_center_norm(xyxy: List[float], w: int, h: int) -> Tuple[float, float]:
    x1, y1, x2, y2 = xyxy
    cx = (x1 + x2) / 2.0 / w
    cy = (y1 + y2) / 2.0 / h
    return float(cx), float(cy)

def point_in_rect_norm(pt: Tuple[float, float], rect: List[float]) -> bool:
    x, y = pt
    x1, y1, x2, y2 = rect
    return (x1 <= x <= x2) and (y1 <= y <= y2)

@app.post("/api/check_map")
async def check_map(
    file: UploadFile = File(...),
    save: str | None = Query(default=None, description="是否保存标注图：1/true/yes"),
):
    """
    上传图片并将检测到的“人”的中心点映射到 seat_map.json 中的归一化矩形座位。
    返回每个座位的占用状态和人数计数。
    可选查询参数 ?save=1 保存带框图，并通过 /static/ 对外可见。
    """
    data = await file.read()

    want_save = _boolish(save)

    # 1) 运行人形检测
    detect_res = detect_from_bytes(data, save_annotated=want_save, save_dir=ANNOT_DIR)
    persons_xyxy: List[List[float]] = [d["xyxy"] for d in detect_res["detections"] if d["cls"] == 0]

    # 2) 读取图片尺寸
    h, w = decode_shape(data)

    # 3) 加载座位映射（归一化矩形）
    seat_map = load_seat_map("seat_map.json")
    seats = seat_map["seats"]

    # 4) 初始化计数
    seat_status = []
    for s in seats:
        seat_status.append({"id": s["id"], "occupied": False, "count": 0})

    # 5) 映射每个“人”的中心到座位
    unmapped = 0
    for box in persons_xyxy:
        cx, cy = bbox_center_norm(box, w, h)
        mapped = False
        for i, s in enumerate(seats):
            rect = s["rect"]  # [x1, y1, x2, y2] in 0..1
            if point_in_rect_norm((cx, cy), rect):
                seat_status[i]["occupied"] = True
                seat_status[i]["count"] += 1
                mapped = True
                break
        if not mapped:
            unmapped += 1

    overall_occupied = any(s["occupied"] for s in seat_status)
    persons_total = len(persons_xyxy)

    out = {
        "occupied": overall_occupied,
        "persons": persons_total,
        "seats": seat_status,
        "unmapped_persons": unmapped
    }
    if want_save and "annotated_path" in detect_res:
        fname = os.path.basename(detect_res["annotated_path"])
        out["annotated_url"] = f"/static/{fname}"
    return out

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
