import { axiosClient } from "./axiosClient";

export interface EphemeralTokenResponse {
  client_secret: {
    value: string;
  };
}

export interface AttitudeFramePayload {
  t_ms: number;
  image_b64: string;
}

export interface AttitudeResponse {
  metrics: {
    head_center_ratio: number;
    downward_ratio: number;
    expression_variability: number;
    eye_open_variability: number;
  };
  events: Array<{
    t_start_ms: number;
    t_end_ms: number;
    type: string;
    severity: string;
    detail?: string | null;
  }>;
  summary_text: string;
  debug?: Record<string, unknown>;
}

export const inferApi = {
  getRealtimeToken: async () => {
    const response = await axiosClient.get<EphemeralTokenResponse>(
      "/api/infer/realtime-token",
    );
    return response.data;
  },

  // 면접 준비용 RAG 데이터 저장
  ingestResume: async (
    file: File,
    userId: string,
  ): Promise<{ message: string; resume_text: string }> => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await axiosClient.post(
      `/api/infer/ingest?session_id=${userId}`,
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      },
    );
    return response.data;
  },

  storeDirectTextRAG: async (text: string, userId: string) => {
    const response = await axiosClient.post("/api/interview/store-resume", {
      resume_text: text,
      user_id: userId,
    });
    return response.data;
  },

  // 예상 질문 추출
  analyzeResume: async (resumeText: string, jobRole: string) => {
    const response = await axiosClient.post("/api/interview/analyze-resume", {
      resume_text: resumeText,
      job_role: jobRole,
    });
    return response.data;
  },

  // 면접 평가 및 질문 풀
  evaluateTurn: async (payload: any) => {
    const response = await axiosClient.post(
      "/api/infer/evaluate-turn",
      payload,
    );
    return response.data;
  },

  analyzeAttitude: async (frames: AttitudeFramePayload[]) => {
    const response = await axiosClient.post<AttitudeResponse>(
      "/api/infer/attitude",
      { frames },
    );
    return response.data;
  },

  getTTS: async (text: string) => {
    const response = await axiosClient.post("/api/infer/tts", text ? { text } : {}, {
      responseType: "blob",
    });
    return response.data as Blob;
  },

  getEvaluationReport: async (payload: {
    messages: any[];
    job_role: string;
    difficulty: string;
    resume_text: string | null;
  }) => {
    const response = await axiosClient.post("/api/interview/evaluate", payload);
    return response.data;
  },

  getQuestionPool: async (
    jobRole: string,
    difficulty: string,
    limit: number,
  ) => {
    const response = await axiosClient.get(`/api/infer/questions`, {
      params: {
        job_role: jobRole,
        difficulty: difficulty,
        limit: limit,
      },
    });
    return response.data;
  },
};
