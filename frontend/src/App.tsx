import { useState, useEffect, type FC } from "react";
import { BrowserRouter } from "react-router-dom";
import { AppRouter } from "./router/AppRouter";
import { SplashView } from "./components/layout/SplashView";
import { GlobalAlertHost } from "./components/common/GlobalAlertHost";
import { useAutoLogout } from "./hooks/useAutoLogout";
import { useAuthStore } from "./store/authStore";
import { authApi } from "./api/authApi";

const AppContent: FC = () => {
  useAutoLogout(30);
  const setAuth = useAuthStore((state) => state.setAuth);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const accessToken = params.get("access_token");
    const social = params.get("social");

    if (!accessToken || !social) {
      return;
    }

    let cancelled = false;

    const completeSocialLogin = async () => {
      try {
        const user = await authApi.verify(accessToken);
        if (cancelled) {
          return;
        }

        setAuth(
          {
            id: String(user.id),
            email: user.email,
            name: user.name ?? undefined,
            profile_image_url: user.profile_image_url ?? undefined,
            role: user.role,
            tier: user.tier,
          },
          accessToken,
        );
      } catch (error) {
        console.error("Social login completion failed:", error);
      } finally {
        const cleanUrl = window.location.pathname + window.location.hash;
        window.history.replaceState({}, "", cleanUrl);
      }
    };

    void completeSocialLogin();

    return () => {
      cancelled = true;
    };
  }, [setAuth]);

  return (
    <main className="app-main-content">
      <AppRouter />
    </main>
  );
};

const App: FC = () => {
  const [isAppLoading, setIsAppLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsAppLoading(false);
    }, 2000);

    return () => clearTimeout(timer);
  }, []);

  if (isAppLoading) {
    return <SplashView />;
  }

  return (
    <BrowserRouter>
      <GlobalAlertHost />
      <AppContent />
    </BrowserRouter>
  );
};

export default App;
