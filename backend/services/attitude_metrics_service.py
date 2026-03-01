"""
File: attitude_metrics_service.py
Author: 양창일
Created: 2026-02-28
Description: 랜드마크 그룹 JSON에서 지표를 계산하는 로직

Modification History:
- 2026-02-28 (양창일): 초기 생성 (랜드마크 그룹 JSON에서 지표를 계산하는 로직)
"""


from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math
import statistics

Point = Tuple[float, float]

def _flatten_points(groups: dict) -> List[Point]:
    pts: List[Point] = []
    for k, arr in (groups or {}).items():
        if isinstance(arr, list):
            for p in arr:
                if isinstance(p, (list, tuple)) and len(p) >= 2:
                    pts.append((float(p[0]), float(p[1])))
    return pts

def _avg(points: List[Point]) -> Optional[Point]:
    if not points:
        return None
    return (sum(p[0] for p in points)/len(points), sum(p[1] for p in points)/len(points))

def _get(group: dict, key: str) -> List[Point]:
    arr = group.get(key) or []
    return [(float(x), float(y)) for x, y in arr if isinstance(x, (int,float)) and isinstance(y, (int,float))]

def compute_frame_features(groups: dict) -> Optional[dict]:
    """
    returns dict with:
      yaw_proxy, pitch_proxy, is_center, is_down,
      mouth_open_norm, eye_open_norm
    """
    pts = _flatten_points(groups)
    if len(pts) < 10:
        return None

    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    w = max_x - min_x
    h = max_y - min_y
    if w <= 1e-6 or h <= 1e-6:
        return None

    mid_x = (min_x + max_x) / 2.0

    nose = _avg(_get(groups, "nose_tip")) or _avg(_get(groups, "nose_bridge"))
    l_eye = _get(groups, "left_eye")
    r_eye = _get(groups, "right_eye")
    mouth_top = _get(groups, "top_lip")
    mouth_bot = _get(groups, "bottom_lip")
    l_brow = _get(groups, "left_eyebrow")
    r_brow = _get(groups, "right_eyebrow")

    if nose is None or not l_eye or not r_eye:
        return None

    eye_y = (sum(p[1] for p in l_eye)/len(l_eye) + sum(p[1] for p in r_eye)/len(r_eye)) / 2.0
    nose_x, nose_y = nose

    # yaw: 코가 얼굴 중앙에서 얼마나 좌우로 치우쳤는지(정규화)
    yaw_proxy = (nose_x - mid_x) / w

    # pitch: 코가 눈보다 얼마나 아래에 있는지(정규화)
    pitch_proxy = (nose_y - eye_y) / h

    # mouth open: 입 위/아래 y-범위로 근사
    mouth_open = 0.0
    if mouth_top and mouth_bot:
        mouth_open = (max(p[1] for p in mouth_bot) - min(p[1] for p in mouth_top)) / h

    # eye open: 눈 y-범위/얼굴높이로 근사(좌우 평균)
    def eye_open_norm(eye_pts: List[Point]) -> float:
        if not eye_pts: return 0.0
        return (max(p[1] for p in eye_pts) - min(p[1] for p in eye_pts)) / h
    eye_open = (eye_open_norm(l_eye) + eye_open_norm(r_eye)) / 2.0

    # expression signal: 입/눈썹 변화량(프레임 단위 값)
    brow_signal = 0.0
    if l_brow and r_brow:
        brow_y = (sum(p[1] for p in l_brow)/len(l_brow) + sum(p[1] for p in r_brow)/len(r_brow)) / 2.0
        brow_signal = (eye_y - brow_y) / h  # 눈썹이 올라가면 커짐

    # thresholds (MVP용; 실측 후 조정 권장)
    is_center = (abs(yaw_proxy) < 0.12) and (abs(pitch_proxy) < 0.40)
    is_down = (pitch_proxy > 0.40)

    print(
        "[DEBUG][attitude_metrics] frame_values",
        {
            "yaw_proxy": round(yaw_proxy, 4),
            "pitch_proxy": round(pitch_proxy, 4),
            "mouth_open_norm": round(mouth_open, 4),
            "eye_open_norm": round(eye_open, 4),
            "expr_signal": round(brow_signal, 4),
            "is_center": is_center,
            "is_down": is_down,
        },
    )

    return {
        "yaw_proxy": yaw_proxy,
        "pitch_proxy": pitch_proxy,
        "is_center": is_center,
        "is_down": is_down,
        "mouth_open_norm": mouth_open,
        "eye_open_norm": eye_open,
        "expr_signal": brow_signal,
    }

def compute_turn_metrics(frame_features: List[dict]) -> dict:
    n = len(frame_features)
    if n == 0:
        return {
            "head_center_ratio": 0.0,
            "downward_ratio": 0.0,
            "expression_variability": 0.0,
            "eye_open_variability": 0.0,
        }

    head_center_ratio = sum(1 for f in frame_features if f["is_center"]) / n
    downward_ratio = sum(1 for f in frame_features if f["is_down"]) / n

    expr_vals = [f["expr_signal"] for f in frame_features]
    eye_vals = [f["eye_open_norm"] for f in frame_features]

    expression_variability = float(statistics.pstdev(expr_vals)) if len(expr_vals) >= 2 else 0.0
    eye_open_variability = float(statistics.pstdev(eye_vals)) if len(eye_vals) >= 2 else 0.0

    return {
        "head_center_ratio": float(head_center_ratio),
        "downward_ratio": float(downward_ratio),
        "expression_variability": float(expression_variability),
        "eye_open_variability": float(eye_open_variability),
    }

def detect_events(t_ms: List[int], frame_features: List[dict], fps: float = 2.0) -> List[dict]:
    """
    연속 구간 기반 이벤트.
    - head_off_center: is_center=False가 1.5초 이상 지속
    - head_down: is_down=True가 2.0초 이상 지속
    """
    events: List[dict] = []
    if not frame_features:
        return events

    def push_event(start_i, end_i, typ, severity="warn"):
        events.append({
            "t_start_ms": t_ms[start_i],
            "t_end_ms": t_ms[end_i],
            "type": typ,
            "severity": severity,
        })

    # helper: run-length
    def scan(predicate, typ, min_sec):
        run_start = None
        for i, f in enumerate(frame_features):
            ok = predicate(f)
            if ok and run_start is None:
                run_start = i
            if (not ok or i == len(frame_features)-1) and run_start is not None:
                run_end = i if ok and i == len(frame_features)-1 else i-1
                dur_sec = (run_end - run_start + 1) / fps
                if dur_sec >= min_sec:
                    push_event(run_start, run_end, typ, "warn")
                run_start = None

    scan(lambda f: not f["is_center"], "head_off_center", min_sec=1.5)
    scan(lambda f: f["is_down"], "head_down", min_sec=2.0)

    return events
