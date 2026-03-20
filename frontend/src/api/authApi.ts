import { axiosClient } from "./axiosClient";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  id: number;
  email: string;
  name: string;
  role: string;
  tier: "normal" | "premium";
  profile_image_url: string | null;
  refresh_token: string;
}

export const authApi = {
  login: async (credentials: Record<string, string>) => {
    const response = await axiosClient.post<LoginResponse>("/api/auth/login", {
      email: credentials.email,
      password: credentials.password,
    });
    return response.data;
  },

  register: async (data: Record<string, any>) => {
    const response = await axiosClient.post("/api/auth/signup", data);
    return response.data;
  },

  logout: async () => {
    const response = await axiosClient.post("/api/auth/logout");
    return response.data;
  },

  updateProfileImage: async (formData: FormData) => {
    const response = await axiosClient.post(
      "/api/auth/profile-image",
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      },
    );
    return response.data;
  },

  sendResetEmail: async (data: { email: string; auth_code: string }) => {
    const response = await axiosClient.post("/api/auth/send-reset-email", data);
    return response.data;
  },

  resetPassword: async (data: { email: string; new_password: string }) => {
    const response = await axiosClient.post("/api/auth/reset-password", data);
    return response.data;
  },

  checkEmail: async (email: string) => {
    const response = await axiosClient.get(
      `/api/auth/check-email?email=${email}`,
    );
    return response.data;
  },

  sendSignupEmail: async (data: { email: string; auth_code: string }) => {
    const response = await axiosClient.post(
      "/api/auth/send-signup-email",
      data,
    );
    return response.data;
  },

  upgradeTier: async () => {
    const response = await axiosClient.post("/api/auth/upgrade");
    return response.data;
  },
};
