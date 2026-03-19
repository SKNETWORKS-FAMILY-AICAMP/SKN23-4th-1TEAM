import { axiosClient } from './axiosClient';

export interface ResumeItem {
  id: number;
  title: string;
  job_role: string;
  resume_text: string;
  created_at: string;
  analysis_result?: {
    keywords?: string[];
    match_rate?: number;
    match_feedback?: string;
    expected_questions?: string[];
  };
}

export const resumeApi = {
  listResumes: async (userId: number): Promise<{ items: ResumeItem[] }> => {
    const response = await axiosClient.get(`/api/v1/resumes?user_id=${userId}`);
    return response.data;
  },

  getLatestResume: async (userId: number): Promise<{ user_id: number; job_role: string; analysis_result: any }> => {
    const response = await axiosClient.get(`/api/v1/resumes/latest?user_id=${userId}`);
    return response.data;
  },

  createResume: async (payload: {
    user_id: number;
    title: string;
    job_role: string;
    resume_text: string;
  }) => {
    // 1. interview.py에 정의된 AI 분석 API를 먼저 호출하여 결과 획득
    const analysisResponse = await axiosClient.post('/api/interview/analyze-resume', {
      resume_text: payload.resume_text,
      job_role: payload.job_role
    });

    // 백엔드 응답 구조 { "status": "success", "data": { ... } } 에 맞춰 추출
    const aiAnalysisResult = analysisResponse.data.data;

    // 2. AI 분석 결과(analysis_result)를 페이로드에 합쳐서 최종 저장 API 호출
    const response = await axiosClient.post('/api/v1/resumes', {
      user_id: payload.user_id,
      title: payload.title,
      job_role: payload.job_role,
      resume_text: payload.resume_text,
      analysis_result: aiAnalysisResult
    });

    return response.data;
  },

  deleteResume: async (resumeId: number) => {
    const response = await axiosClient.delete(`/api/v1/resumes/${resumeId}`);
    return response.data;
  }
};