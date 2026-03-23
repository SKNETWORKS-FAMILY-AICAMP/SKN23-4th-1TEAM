import axios from "axios";
import { useAuthStore } from "../store/authStore";

export const axiosClient = axios.create({
  baseURL: "",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

axiosClient.interceptors.request.use(
  (config) => {
    let token = useAuthStore.getState().accessToken;

    if (!token) {
      try {
        const authData = JSON.parse(
          localStorage.getItem("auth-storage") || "{}",
        );
        token = authData?.state?.accessToken;
      } catch (e) {
        console.error("Token parsing error:", e);
      }
    }

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    const csrfCookie = document.cookie
      .split("; ")
      .find((row) => row.toLowerCase().includes("csrf"));

    if (csrfCookie) {
      const csrfToken = csrfCookie.split("=")[1];
      config.headers["X-CSRF-Token"] = csrfToken;
    }

    return config;
  },
  (error) => Promise.reject(error),
);

// Response Interceptor
axiosClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // 401 에러가 나면 토큰 재발급(Refresh) 시도
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      originalRequest.url !== "/api/auth/refresh" &&
      originalRequest.url !== "/api/auth/login"
    ) {
      originalRequest._retry = true;
      try {
        // 이 재발급 요청에도 방금 추가한 CSRF 헤더가 자동으로 붙어서 날아갑니다! (403 해결)
        const res = await axiosClient.post("/api/auth/refresh");
        const newToken = res.data.access_token;

        useAuthStore.setState({ accessToken: newToken });
        originalRequest.headers.Authorization = `Bearer ${newToken}`;

        // 재발급받은 토큰으로 원래 하려던 요청(예: 게시글 삭제) 다시 시도
        return axiosClient(originalRequest);
      } catch (refreshError) {
        useAuthStore.getState().clearAuth();
        window.location.href = "/auth";
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  },
);
