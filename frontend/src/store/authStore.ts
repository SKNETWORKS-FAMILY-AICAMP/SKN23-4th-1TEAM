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
  github_url?: string;
  is_cancel_scheduled?: number | boolean;
  pro_expire_date?: string | null;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  accessToken: string | null;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
  updateTier: (tier: UserTier) => void;
  setUser: (user: User) => void;
  isLoginModalOpen: boolean;
  openLoginModal: () => void;
  closeLoginModal: () => void;
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
        
      setUser: (user) => set({ user }),
      isLoginModalOpen: false,
      openLoginModal: () => set({ isLoginModalOpen: true }),
      closeLoginModal: () => set({ isLoginModalOpen: false }),
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        accessToken: state.accessToken,
      }),
    },
  ),
);