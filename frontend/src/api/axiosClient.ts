import axios from 'axios';
import { useAuthStore } from '../store/authStore';

export const axiosClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor
axiosClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor
axiosClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    // 401 에러이고 재시도한 적이 없으며 리프레시 요청 자체가 아닌 경우에만 실행
    if (
      error.response?.status === 401 && 
      !originalRequest._retry && 
      originalRequest.url !== '/api/auth/refresh'
    ) {
      originalRequest._retry = true;
      try {
        const res = await axiosClient.post('/api/auth/refresh');
        const newToken = res.data.access_token;
        
        // 전역 스토어 토큰 갱신
        useAuthStore.setState({ accessToken: newToken });

        // 원래 실패했던 요청 헤더 교체 후 재시도
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return axiosClient(originalRequest);
      } catch (refreshError) {
        // 리프레시 실패 시 스토어 초기화 및 로그인 페이지 강제 이동
        useAuthStore.getState().clearAuth();
        window.location.href = '/auth';
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);