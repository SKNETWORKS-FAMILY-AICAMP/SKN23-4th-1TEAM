import { useState, useEffect, type FC } from "react";
import { BrowserRouter } from "react-router-dom";
import { AppRouter } from "./router/AppRouter";
import { SplashView } from "./components/layout/SplashView";
import { GlobalAlertHost } from "./components/common/GlobalAlertHost";
import { useAutoLogout } from "./hooks/useAutoLogout";

const AppContent: FC = () => {
  // 30분 미활동 감지 로그아웃 타이머 실행
  useAutoLogout(30);

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
