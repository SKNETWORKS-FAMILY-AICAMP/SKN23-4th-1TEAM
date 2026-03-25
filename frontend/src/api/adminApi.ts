import { axiosClient } from "./axiosClient";

export interface AdminUser {
  id: number;
  email: string;
  name: string;
  password?: string;
  provider?: string;
  role: string;
  status?: string;
  tier?: string;
}

export const adminApi = {
  getUsers: async (): Promise<AdminUser[]> => {
    const res = await axiosClient.get("/api/admin/query?query_type=users");
    return res.data;
  },

  updateUser: async (sql: string, args: any[]) => {
    const res = await axiosClient.post("/api/admin/sql", { sql, args });
    return res.data;
  },
};
