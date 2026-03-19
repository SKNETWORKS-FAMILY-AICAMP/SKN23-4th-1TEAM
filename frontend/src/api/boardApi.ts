import { axiosClient } from './axiosClient';

export const boardApi = {
  getQuestions: async () => {
    const res = await axiosClient.get('/api/board/questions');
    return res.data;
  },

  getQuestionDetail: async (questionId: number, limit = 10, offset = 0) => {
    const res = await axiosClient.get(`/api/board/questions/${questionId}`, {
      params: { limit, offset }
    });
    return res.data;
  },

  submitAnswer: async (questionId: number, content: string, userId: number, authorName: string) => {
    const res = await axiosClient.post(`/api/board/questions/${questionId}/answers`, { 
      content, user_id: userId, author_name: authorName
    });
    return res.data;
  },

  toggleLike: async (answerId: number) => {
    const res = await axiosClient.post(`/api/board/answers/${answerId}/like`);
    return res.data;
  },

  // 답변 삭제 API
  deleteAnswer: async (answerId: number) => {
    const res = await axiosClient.delete(`/api/board/answers/${answerId}`);
    return res.data;
  },

  // 새 질문 등록 API (백엔드에서 AI 처리 진행)
  createQuestion: async (rawContent: string) => {
    const res = await axiosClient.post('/api/board/questions', { raw_content: rawContent });
    return res.data;
  },

  // 관리자용 질문 삭제 API
  deleteQuestion: async (questionId: number) => {
    const res = await axiosClient.delete(`/api/board/questions/${questionId}`);
    return res.data;
  }
};