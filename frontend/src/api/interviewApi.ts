// api/interviewApi.ts

import axios from "axios";
import { EvaluationPayload, EvaluationResponse } from "../types/interview";

// Axios 인스턴스 (필요시 baseURL 설정)
const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || "/api",
});

// 1. OpenAI WebRTC 통신용 단기(Ephemeral) 토큰 발급
export const getRealtimeToken = async () => {
  const response = await api.get("/infer/realtime-token");
  return response.data;
};

// 2. 답변 평가 (OpenAI가 텍스트로 변환해준 사용자의 음성을 백엔드로 전송)
export const evaluateVoiceTurn = async (
  payload: EvaluationPayload,
): Promise<EvaluationResponse> => {
  const response = await api.post("/infer/evaluate-turn", payload);
  return response.data;
};

// 3. AI 면접관 음성 파일(TTS) 생성
export const getTTS = async (text: string): Promise<Blob> => {
  const response = await api.post(
    "/infer/tts",
    { text },
    { responseType: "blob" },
  );
  return response.data;
};
