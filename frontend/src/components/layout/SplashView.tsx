// src/components/layout/SplashView.tsx
import "./SplashView.scss";

export const SplashView = () => {
  return (
    <div className="splash-container">
      <div className="splash-logo">
        <img src="/favicon.png" alt="AIWORK Logo" />
        <h1>
          <span className="logo-ai">AI</span>
          <span className="logo-work">WORK</span>
        </h1>
      </div>
    </div>
  );
};
