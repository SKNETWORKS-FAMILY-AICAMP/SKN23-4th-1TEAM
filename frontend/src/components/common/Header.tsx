import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createPortal } from "react-dom";
import { useAuthStore } from "../../store/authStore";
import { ROUTES } from "../../constants/routes";
import { authApi } from "../../api/authApi";
import { CustomAlert } from "./CustomAlert";
import "./Header.scss";

const NAV_ITEMS = [
  { label: "AI 면접", path: ROUTES.INTERVIEW },
  { label: "이력서", path: "/resume" },
  { label: "내 기록", path: "/mypage" },
  { label: "게시판", path: ROUTES.BOARD },
  { label: "마이페이지", path: "/my_info" },
];

export const Header = () => {
  const { isAuthenticated, user, clearAuth } = useAuthStore();
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [showLoginRequiredAlert, setShowLoginRequiredAlert] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (!isMobileMenuOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isMobileMenuOpen]);

  const handleNavClick = (path: string) => {
    setIsMobileMenuOpen(false);

    if (!isAuthenticated) {
      setShowLoginRequiredAlert(true);
      return;
    }

    navigate(path);
  };

  const handleLogoutClick = () => {
    setIsMobileMenuOpen(false);
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

  const renderNavItems = (className?: string) =>
    NAV_ITEMS.map((item) => (
      <button
        key={item.path}
        className={className ?? "nav-btn"}
        onClick={() => handleNavClick(item.path)}
      >
        {item.label}
      </button>
    ));

  return (
    <>
      <header className="main-header">
        <div className="logo-container" onClick={() => navigate(ROUTES.HOME)}>
          <img src="/favicon.png" alt="AIWORK Logo" className="logo-img" />
          <span className="logo-text">WORK</span>
        </div>

        <nav className="nav-links">{renderNavItems()}</nav>

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

        <button
          className={`mobile-menu-toggle${isMobileMenuOpen ? " open" : ""}`}
          type="button"
          aria-label="메뉴 열기"
          aria-expanded={isMobileMenuOpen}
          onClick={() => setIsMobileMenuOpen((prev) => !prev)}
        >
          <span />
          <span />
          <span />
        </button>
      </header>

      <div
        className={`mobile-menu-backdrop${isMobileMenuOpen ? " visible" : ""}`}
        onClick={() => setIsMobileMenuOpen(false)}
      />

      <aside className={`mobile-menu-drawer${isMobileMenuOpen ? " open" : ""}`}>
        <div className="mobile-menu-header">
          <div>
            <strong>AIWORK 메뉴</strong>
            <p>모바일에서 더 편하게 둘러보세요.</p>
          </div>
          <button
            type="button"
            className="mobile-menu-close"
            onClick={() => setIsMobileMenuOpen(false)}
            aria-label="메뉴 닫기"
          >
            ×
          </button>
        </div>

        <div className="mobile-nav-links">
          {renderNavItems("mobile-nav-btn")}
        </div>

        <div className="mobile-auth-panel">
          {isAuthenticated ? (
            <>
              <div className="mobile-user-summary">
                <span className="mobile-user-label">현재 로그인</span>
                <strong>{user?.name}님</strong>
              </div>
              <button
                className="mobile-auth-btn secondary"
                onClick={handleLogoutClick}
              >
                로그아웃
              </button>
            </>
          ) : (
            <button
              className="mobile-auth-btn primary"
              onClick={() => {
                setIsMobileMenuOpen(false);
                navigate(ROUTES.AUTH);
              }}
            >
              로그인 / 회원가입
            </button>
          )}
        </div>
      </aside>

      <CustomAlert
        open={showLoginRequiredAlert}
        title="로그인이 필요합니다"
        message="해당 메뉴는 로그인 후 이용할 수 있습니다. 로그인 페이지로 이동할까요?"
        onCancel={() => setShowLoginRequiredAlert(false)}
        onConfirm={() => {
          setShowLoginRequiredAlert(false);
          navigate(ROUTES.AUTH);
        }}
      />

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
                로그아웃 후 로그인 화면으로 이동합니다.
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
