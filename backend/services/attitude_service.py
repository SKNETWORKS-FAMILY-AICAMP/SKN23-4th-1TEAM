"""
File: attitude_service.py
Author: 양창일
Created: 2026-02-28
Description: 프레임 여러 장을 HF에 보내고 요약

Modification History:
- 2026-02-28 (양창일): 초기 생성
"""

from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from backend.services.hf_landmark_service import infer_landmark_groups
from backend.services.attitude_metrics_service import compute_frame_features, compute_turn_metrics, detect_events

def analyze_attitude(frames: List[dict], fps: float = 2.0) -> Dict[str, Any]:
    # 1) 프레임 과다 방지: 최대 40장(20초 @2fps)
    frames = frames[:40]
    if len(frames) > 10:
        step = max(1, len(frames) // 10)
        frames = frames[::step][:10]

    t_ms_list = []
    feats = []

    def _analyze_frame(item: tuple[int, dict]):
        idx, fr = item
        t_ms = int(fr["t_ms"])
        groups = infer_landmark_groups(fr["image_b64"])
        ff = compute_frame_features(groups)
        return idx, t_ms, groups, ff

    indexed_frames = list(enumerate(frames, start=1))
    results = []
    for batch_start in range(0, len(indexed_frames), 5):
        batch = indexed_frames[batch_start:batch_start + 5]
        with ThreadPoolExecutor(max_workers=5) as executor:
            results.extend(executor.map(_analyze_frame, batch))

    results = sorted(results, key=lambda item: item[0])
    for idx, t_ms, groups, ff in results:
        t_ms_list.append(t_ms)
        print(
            "[DEBUG][attitude_service] frame",
            idx,
            "group_keys=",
            list((groups or {}).keys())[:12],
            "feature_ok=",
            ff is not None,
        )
        if ff is not None:
            feats.append(ff)

    for fr in []:
        t_ms_list.append(int(fr["t_ms"]))
        groups = infer_landmark_groups(fr["image_b64"])
        ff = compute_frame_features(groups)
        print(
            "[DEBUG][attitude_service] frame",
            len(t_ms_list),
            "group_keys=",
            list((groups or {}).keys())[:12],
            "feature_ok=",
            ff is not None,
        )
        if ff is not None:
            feats.append(ff)
        else:
            # landmark 실패 프레임은 스킵(또는 별도 카운트)
            pass

    metrics = compute_turn_metrics(feats)
    events = detect_events(t_ms_list[:len(feats)], feats, fps=fps) if feats else []
    print(
        "[DEBUG][attitude_service] sampled_frames=",
        len(frames),
        "valid_features=",
        len(feats),
        "metrics=",
        metrics,
    )

    # 2) 요약 텍스트(면접 내용과 같이 보낼 한두 줄)
    tips = []
    if not feats:
        return {
            "metrics": metrics,
            "events": events,
            "summary_text": "태도 분석에 필요한 얼굴 포인트를 충분히 인식하지 못했습니다. 카메라 각도와 조명을 확인해 주세요.",
            "debug": {
                "sampled_frames": len(frames),
                "valid_features": len(feats),
            },
        }
    if metrics["head_center_ratio"] < 0.45:
        tips.append("정면 유지가 자주 무너졌습니다(고개의 좌우를 돌리지 않고 정면을 유지해보세요).")
    if metrics["downward_ratio"] > 0.20:
        tips.append("아래를 보는 구간이 길었습니다(질문-답변 전환 시 고개를 먼저 들어 시선을 정리해보세요).")
    if metrics["expression_variability"] < 0.0040:
        tips.append("표정 변화가 낮아 경직되어 보일 수 있습니다(핵심 문장에만 미소/끄덕임 1회만 추가해보세요).")

    summary_text = " ".join(tips[:2]) if tips else "태도 지표가 안정적입니다."

    return {
        "metrics": metrics,
        "events": events,
        "summary_text": summary_text,
        "debug": {
            "sampled_frames": len(frames),
            "valid_features": len(feats),
        },
    }
