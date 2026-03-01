"""
Hugging Face Space wrapper for landmark inference.
"""

import base64
import ast
import json
import os
import tempfile

from gradio_client import Client, handle_file


HF_SPACE = "Akjava/mediapipe-68-points-facial-landmark"
_CLIENT = None


def get_client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = Client(HF_SPACE)
    return _CLIENT


def _normalize_groups_payload(payload) -> dict:
    if isinstance(payload, dict):
        return payload

    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            try:
                parsed = ast.literal_eval(text)
            except Exception:
                return {}

        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, str):
            return _normalize_groups_payload(parsed)
        if isinstance(parsed, list):
            for item in parsed:
                normalized = _normalize_groups_payload(item)
                if normalized:
                    return normalized
            return {}
        return {}

    if isinstance(payload, list):
        for item in payload:
            normalized = _normalize_groups_payload(item)
            if normalized:
                return normalized
        return {}

    return {}


def infer_landmark_groups(image_b64: str) -> dict:
    """
    Space infer signature:
    process_images(image, draw_number, font_scale, text_color, dot_size, dot_color,
                   line_size, line_color, box_size, box_color, json_format, draw_mesh)
    outputs: annotated_image, jsons, download_path
    """
    image_bytes = base64.b64decode(image_b64)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    client = get_client()

    try:
        _annotated_img, jsons, _download = client.predict(
            handle_file(tmp_path),
            False,
            0.5,
            "rgba(200,200,200,1)",
            3,
            "rgba(255,0,0,1)",
            1,
            "rgba(0,0,255,1)",
            1,
            "rgba(200,200,200,1)",
            "face-detection",
            False,
            api_name="/infer",
        )
        normalized = _normalize_groups_payload(jsons)
        print("[DEBUG][hf_landmark_service] raw_jsons_type:", type(jsons).__name__)
        if isinstance(jsons, str):
            print("[DEBUG][hf_landmark_service] raw_jsons_preview:", jsons[:500])
        print("[DEBUG][hf_landmark_service] normalized_keys:", list(normalized.keys())[:20])
        if normalized:
            first_key = next(iter(normalized.keys()))
            first_value = normalized.get(first_key)
            print("[DEBUG][hf_landmark_service] first_key:", first_key)
            print("[DEBUG][hf_landmark_service] first_value_type:", type(first_value).__name__)
            if isinstance(first_value, list):
                print("[DEBUG][hf_landmark_service] first_value_len:", len(first_value))
        else:
            print("[DEBUG][hf_landmark_service] normalized payload is empty")
        return normalized
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
