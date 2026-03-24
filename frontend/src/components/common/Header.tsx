import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { ROUTES } from "../../constants/routes";
import { authApi } from "../../api/authApi";
import { LoginModal } from "./LoginModal";
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
  // 💡 openLoginModal 함수 추가
  const { isAuthenticated, user, clearAuth, openLoginModal } = useAuthStore();
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);
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
      openLoginModal(); 
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

      {/* 💡 모든 페이지에서 공통으로 띄워질 커스텀 로그인 모달! */}
      <LoginModal />

      <CustomAlert
        open={showLogoutModal}
        title={"로그아웃 하시겠습니까?"}
        message={"로그아웃 후 로그인 화면으로 이동합니다."}
        confirmText={"확인"}
        cancelText={"취소"}
        onConfirm={executeLogout}
        onCancel={() => setShowLogoutModal(false)}
      />
    </>
  );
};
