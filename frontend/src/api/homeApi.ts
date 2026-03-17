import { axiosClient } from './axiosClient';

export interface Memo {
  id?: string;
  author: string;
  content: string;
  color: string;
  border: string;
  text_color: string;
  created_at?: string;
}

export const homeApi = {
  getMemos: async (limit: number = 30) => {
    const response = await axiosClient.get(`/api/home/memos?limit=${limit}`);
    return response.data; // { items: Memo[] }
  },
  createMemo: async (memo: Partial<Memo>) => {
    const response = await axiosClient.post('/api/home/memos', memo);
    return response.data;
  },
  getNews: async (query: string) => {
    const response = await axiosClient.post('/api/home/news', { query });
    return response.data; // { content: string }
  },
  getGuide: async (message: string, useWebSearch: boolean = true) => {
    const response = await axiosClient.post('/api/home/guide', {
      message: message,
      use_web_search: useWebSearch, // Tavily 스위치 ON
    });
    return response.data;
  },
  getMyResumes: async () => {
    const response = await axiosClient.get('/api/home/my-resumes');
    return response.data; // [{ id: '1', title: '이력서.pdf' }, ...]
  },
    // 일회성 첨삭 요청 (DB 저장 안 함)
  proofreadText: async (content: string, type: 'resume' | 'cover_letter') => {
    const response = await axiosClient.post('/api/infer/proofread', {
      content: content,
      document_type: type 
    });
    return response.data; 
  },

  proofreadFile: async (file: File, type: 'resume' | 'cover_letter') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', type);

    const response = await axiosClient.post('/api/home/proofread-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data; 
  },
};
