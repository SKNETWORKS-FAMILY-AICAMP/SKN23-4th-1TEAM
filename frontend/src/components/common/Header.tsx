import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createPortal } from "react-dom";
import { useAuthStore } from "../../store/authStore";
import { ROUTES } from "../../constants/routes";
import { authApi } from "../../api/authApi";
import "./Header.scss";

export const Header = () => {
  const { isAuthenticated, user, clearAuth } = useAuthStore();
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  const handleNavClick = (path: string) => {
    if (!isAuthenticated) {
      alert("로그인이 필요한 서비스입니다.");
      navigate(ROUTES.AUTH);
      return;
    }
    navigate(path);
  };

  const handleLogoutClick = () => {
    setShowLogoutModal(true);
  };

  const executeLogout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error(error);
    } finally {
      setShowLogoutModal(false);
      clearAuth();
      navigate(ROUTES.AUTH);
    }
  };

  return (
    <>
      <header className="main-header">
        <div className="logo-container" onClick={() => navigate(ROUTES.HOME)}>
          <img src="/favicon.png" alt="AIWORK Logo" className="logo-img" />
          <span className="logo-text">WORK</span>
        </div>

        <nav className="nav-links">
          <button
            className="nav-btn"
            onClick={() => handleNavClick(ROUTES.INTERVIEW)}
          >
            AI 면접
          </button>
          <button className="nav-btn" onClick={() => handleNavClick("/resume")}>
            이력서
          </button>
          <button className="nav-btn" onClick={() => handleNavClick("/mypage")}>
            내 기록
          </button>
          <button
            className="nav-btn"
            onClick={() => handleNavClick(ROUTES.BOARD)}
          >
            게시판
          </button>
          <button
            className="nav-btn"
            onClick={() => handleNavClick("/my_info")}
          >
            마이페이지
          </button>
        </nav>

        <div className="auth-actions">
          {isAuthenticated ? (
            <>
              <span className="user-greeting">{user?.name}님</span>
              <button className="logout-btn" onClick={handleLogoutClick}>
                로그아웃
              </button>
            </>
          ) : (
            <button className="login-btn" onClick={() => navigate(ROUTES.AUTH)}>
              로그인 / 회원가입
            </button>
          )}
        </div>
      </header>

      {showLogoutModal &&
        createPortal(
          <div
            style={{
              position: "fixed",
              inset: 0,
              backgroundColor: "rgba(15,23,42,0.6)",
              backdropFilter: "blur(4px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 9999,
            }}
          >
            <div
              style={{
                background: "#ffffff",
                padding: "32px",
                borderRadius: "20px",
                width: "90%",
                maxWidth: "360px",
                textAlign: "center",
                boxShadow: "0 25px 50px -12px rgba(0,0,0,0.25)",
              }}
            >
              <h3
                style={{
                  margin: "0 0 12px 0",
                  fontSize: "20px",
                  fontWeight: "800",
                  color: "#1e293b",
                }}
              >
                로그아웃 하시겠습니까?
              </h3>
              <p
                style={{
                  margin: "0 0 24px 0",
                  fontSize: "14px",
                  color: "#64748b",
                }}
              >
                로그인 화면으로 이동합니다.
              </p>
              <div style={{ display: "flex", gap: "12px" }}>
                <button
                  onClick={() => setShowLogoutModal(false)}
                  style={{
                    flex: 1,
                    padding: "12px",
                    borderRadius: "12px",
                    border: "1px solid #e2e8f0",
                    background: "#ffffff",
                    color: "#475569",
                    fontWeight: "700",
                    cursor: "pointer",
                  }}
                >
                  취소
                </button>
                <button
                  onClick={executeLogout}
                  style={{
                    flex: 1,
                    padding: "12px",
                    borderRadius: "12px",
                    border: "none",
                    background: "#0176f7",
                    color: "#ffffff",
                    fontWeight: "700",
                    cursor: "pointer",
                    boxShadow: "0 4px 12px rgba(1, 118, 247, 0.3)",
                  }}
                >
                  확인
                </button>
              </div>
            </div>
          </div>,
          document.body,
        )}
    </>
  );
};
