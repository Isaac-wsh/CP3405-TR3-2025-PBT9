# backend.py
# FastAPI backend for Seat Detection MVP
# Features:
#  - /api/check_seat : simple person detection
#  - /api/check_map  : map persons to seats; supports ?map=<name> and ?save=1
#  - Static /static/ for annotated images
#  - Dynamic seat map CRUD under /api/seatmap*
#       * GET  /api/seatmaps                 -> list available maps
#       * GET  /api/seatmap/{name}           -> get a map json
#       * PUT  /api/seatmap/{name}           -> create/replace a map (body = {"seats":[...]})
#       * PATCH/DELETE /api/seatmap/{name}/{id} -> update/delete a single seat
#       * DELETE /api/seatmap/{name}         -> delete a map
#  Seat maps are stored as ./seatmaps/<name>.json
from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, Query, HTTPException, Body
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
SEATMAP_DIR = "seatmaps"
DEFAULT_MAP = "default"

os.makedirs(ANNOT_DIR, exist_ok=True)
os.makedirs(SEATMAP_DIR, exist_ok=True)

app = FastAPI(title="Seat Detection MVP", version="0.4.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static annotated images
app.mount("/static", StaticFiles(directory=ANNOT_DIR), name="static")

@app.get("/health")
def health():
    return {"status": "ok"}

def _boolish(x: str | None) -> bool:
    if x is None:
        return False
    return x.lower() in ("1", "true", "yes", "y", "t")

# ---------- Detection APIs ----------
@app.post("/api/check_seat")
async def check_seat(
    file: UploadFile = File(...),
    save: str | None = Query(default=None),
):
    data = await file.read()
    want_save = _boolish(save)
    res = detect_from_bytes(data, save_annotated=want_save, save_dir=ANNOT_DIR)
    out = {"occupied": res["occupied"], "persons": res["persons"]}
    if want_save and "annotated_path" in res:
        fname = os.path.basename(res["annotated_path"])
        out["annotated_url"] = f"/static/{fname}"
    return out

# Seat map helpers
def _seatmap_path(name: str) -> str:
    safe = "".join(c for c in name if c.isalnum() or c in ("-", "_"))
    if not safe:
        raise HTTPException(status_code=400, detail="Invalid map name")
    return os.path.join(SEATMAP_DIR, safe + ".json")

def load_seat_map(name: str = DEFAULT_MAP) -> Dict[str, Any]:
    path = _seatmap_path(name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Seat map '{name}' not found")
    with open(path, "r", encoding="utf-8") as f:
        m = json.load(f)
    if "seats" not in m or not isinstance(m["seats"], list):
        raise HTTPException(status_code=400, detail="seat map json must contain 'seats' array")
    return m

def decode_shape(image_bytes: bytes) -> Tuple[int, int]:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Cannot decode image")
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
    map: str | None = Query(default=DEFAULT_MAP, description="Seat map name (file seatmaps/<name>.json)"),
    save: str | None = Query(default=None),
):
    data = await file.read()
    want_save = _boolish(save)

    detect_res = detect_from_bytes(data, save_annotated=want_save, save_dir=ANNOT_DIR)
    persons_xyxy: List[List[float]] = [d["xyxy"] for d in detect_res["detections"] if d["cls"] == 0]

    h, w = decode_shape(data)
    seat_map = load_seat_map(map)
    seats = seat_map["seats"]

    seat_status = [{"id": s["id"], "occupied": False, "count": 0} for s in seats]

    unmapped = 0
    for box in persons_xyxy:
        cx, cy = bbox_center_norm(box, w, h)
        mapped = False
        for i, s in enumerate(seats):
            rect = s["rect"]
            if point_in_rect_norm((cx, cy), rect):
                seat_status[i]["occupied"] = True
                seat_status[i]["count"] += 1
                mapped = True
                break
        if not mapped:
            unmapped += 1

    out = {
        "occupied": any(s["occupied"] for s in seat_status),
        "persons": len(persons_xyxy),
        "seats": seat_status,
        "unmapped_persons": unmapped,
        "seat_map": map
    }
    if want_save and "annotated_path" in detect_res:
        fname = os.path.basename(detect_res["annotated_path"])
        out["annotated_url"] = f"/static/{fname}"
    return out

# ---------- Seat map CRUD ----------
@app.get("/api/seatmaps")
def list_seatmaps():
    names = []
    for fn in os.listdir(SEATMAP_DIR):
        if fn.endswith(".json"):
            names.append(os.path.splitext(fn)[0])
    return {"maps": sorted(names)}

@app.get("/api/seatmap/{name}")
def get_seatmap(name: str):
    return load_seat_map(name)

@app.put("/api/seatmap/{name}")
def put_seatmap(
    name: str,
    body: Dict[str, Any] = Body(..., example={"seats": [{"id": "R1C1","rect":[0,0,0.1,0.1]}]})
):
    if "seats" not in body or not isinstance(body["seats"], list):
        raise HTTPException(status_code=400, detail="Body must contain 'seats' array")
    path = _seatmap_path(name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)
    return {"ok": True, "name": name}

@app.delete("/api/seatmap/{name}")
def delete_seatmap(name: str):
    path = _seatmap_path(name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Map not found")
    os.remove(path)
    return {"ok": True}

@app.patch("/api/seatmap/{name}/{seat_id}")
def patch_seat(
    name: str,
    seat_id: str,
    rect: List[float] = Body(..., embed=True, example={"rect":[0.1,0.2,0.3,0.4]}),
):
    m = load_seat_map(name)
    found = False
    for s in m["seats"]:
        if s["id"] == seat_id:
            s["rect"] = rect
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Seat id not found")
    with open(_seatmap_path(name), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    return {"ok": True}

@app.delete("/api/seatmap/{name}/{seat_id}")
def delete_seat(name: str, seat_id: str):
    m = load_seat_map(name)
    seats2 = [s for s in m["seats"] if s["id"] != seat_id]
    if len(seats2) == len(m["seats"]):
        raise HTTPException(status_code=404, detail="Seat id not found")
    m["seats"] = seats2
    with open(_seatmap_path(name), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    return {"ok": True}
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
