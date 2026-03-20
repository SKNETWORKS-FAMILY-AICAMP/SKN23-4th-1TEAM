import { create } from "zustand";
import { persist } from "zustand/middleware";

export type UserTier = "guest" | "normal" | "premium";

interface User {
  id: string;
  email: string;
  name?: string;
  profile_image_url?: string;
  role?: string;
  job_role?: string;
  tier: UserTier;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  accessToken: string | null;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
  updateTier: (tier: UserTier) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      accessToken: null,
      setAuth: (user, token) =>
        set({ user, accessToken: token, isAuthenticated: true }),
      clearAuth: () =>
        set({ user: null, accessToken: null, isAuthenticated: false }),
      updateTier: (tier) =>
        set((state) => ({
          ...state,
          user: state.user ? { ...state.user, tier } : null,
        })),
    }),
    {
      name: "auth-storage",
    },
  ),
);
