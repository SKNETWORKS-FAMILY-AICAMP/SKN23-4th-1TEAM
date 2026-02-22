"""
File: local_inference.py
Author: 김다빈
Created: 2026-02-22
Description: 로컬 STT(faster-whisper) 및 TTS(Qwen3-TTS) 모듈
             기존 rag_service.py를 수정하지 않고, 별도 모듈로 분리하여 충돌 방지
             모델 로드 실패 시 OpenAI API로 자동 폴백

Modification History:
- 2026-02-22 (김다빈): 초기 생성 — faster-whisper STT + Qwen3-TTS + OpenAI 폴백
"""

import os
import sys
import io
import tempfile

# 외부 패키지 경로 (macOS SIP 우회용)
_EXT_PKG_PATH = "/tmp/fw_pkg"
if os.path.isdir(_EXT_PKG_PATH) and _EXT_PKG_PATH not in sys.path:
    sys.path.insert(0, _EXT_PKG_PATH)

from openai import OpenAI

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================================
# faster-whisper STT (싱글톤)
# ============================================================
_whisper_model = None


def _get_whisper_model():
    """faster-whisper 모델을 최초 호출 시에만 로딩 (small, CPU)"""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel

            _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
            print("✅ [local_inference] faster-whisper (small) 모델 로드 완료")
        except Exception as e:
            print(f"⚠️ [local_inference] faster-whisper 로드 실패: {e}")
    return _whisper_model


# ============================================================
# Qwen3-TTS (싱글톤, GPU 권장)
# ============================================================
_qwen_tts_model = None
_qwen_tts_available = None


def _get_qwen_tts_model():
    """Qwen3-TTS 모델을 최초 호출 시에만 로딩. GPU 없으면 None"""
    global _qwen_tts_model, _qwen_tts_available
    if _qwen_tts_available is False:
        return None
    if _qwen_tts_model is not None:
        return _qwen_tts_model
    try:
        import torch
        from qwen_tts import Qwen3TTSModel

        device = "cuda" if torch.cuda.is_available() else "cpu"
        _qwen_tts_model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
            torch_dtype=torch.float32,
            device_map=device,
        )
        _qwen_tts_available = True
        print(f"✅ [local_inference] Qwen3-TTS 로드 완료 (device={device})")
    except Exception as e:
        _qwen_tts_available = False
        print(f"⚠️ [local_inference] Qwen3-TTS 로드 실패: {e}")
    return _qwen_tts_model


# ============================================================
# 공개 API
# ============================================================


def local_stt(audio_bytes: bytes, language: str = "ko") -> str:
    """
    음성(bytes) → 텍스트 (STT)
    1순위: faster-whisper (로컬, 무료)
    2순위: OpenAI Whisper API (유료 폴백)
    """
    whisper = _get_whisper_model()
    if whisper is not None:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            tmp.write(audio_bytes)
            tmp.flush()
            tmp.close()
            segments, info = whisper.transcribe(
                tmp.name,
                language=language,
                beam_size=5,
                initial_prompt="면접, 자기소개, 프로젝트, 경험, 기술스택, 데이터분석, 머신러닝, 딥러닝, 파이썬, FastAPI, Streamlit, AWS",
            )
            text = "".join([seg.text for seg in segments])
            return text.strip()
        finally:
            os.unlink(tmp.name)

    # 폴백: OpenAI Whisper API
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.wav"
    transcript = _client.audio.transcriptions.create(
        model="whisper-1", file=audio_file, language=language
    )
    return transcript.text


def local_tts(text: str, voice: str = "onyx") -> bytes:
    """
    텍스트 → 음성(bytes) (TTS)
    1순위: Qwen3-TTS (로컬, 무료, GPU 권장)
    2순위: OpenAI TTS API (유료 폴백)
    """
    qwen_tts = _get_qwen_tts_model()
    if qwen_tts is not None:
        try:
            import soundfile as sf

            wavs, sample_rate = qwen_tts.generate_custom_voice(
                text=text,
                speaker="Chelsie",
                language="Korean",
            )
            buf = io.BytesIO()
            sf.write(buf, wavs[0], sample_rate, format="WAV")
            buf.seek(0)
            return buf.read()
        except Exception as e:
            print(f"⚠️ [local_inference] Qwen3-TTS 추론 실패: {e}")

    # 폴백: OpenAI TTS
    response = _client.audio.speech.create(model="tts-1", voice=voice, input=text)
    return response.content
