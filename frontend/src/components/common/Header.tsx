import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { ROUTES } from '../../constants/routes';
import './Header.scss';

export const Header = () => {
  const { isAuthenticated, user, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  const handleNavClick = (path: string) => {
    if (!isAuthenticated) {
      alert('로그인이 필요한 서비스입니다.');
      navigate(ROUTES.AUTH);
      return;
    }
    navigate(path);
  };

  return (
    <header className="main-header">
      <div className="logo-container" onClick={() => navigate(ROUTES.HOME)}>
        <img src="/favicon.png" alt="AIWORK Logo" className="logo-img" />
        <span className="logo-text">WORK</span>
      </div>
      
      <nav className="nav-links">
        <button className="nav-btn" onClick={() => handleNavClick(ROUTES.INTERVIEW)}>AI 면접</button>
        <button className="nav-btn" onClick={() => handleNavClick('/resume')}>이력서</button>
        <button className="nav-btn" onClick={() => handleNavClick('/mypage')}>내 기록</button>
        <button className="nav-btn" onClick={() => handleNavClick('/my_info')}>마이페이지</button>
      </nav>

      <div className="auth-actions">
        {isAuthenticated ? (
          <>
            <span className="user-greeting">{user?.name}님</span>
            <button className="logout-btn" onClick={clearAuth}>로그아웃</button>
          </>
        ) : (
          <button className="login-btn" onClick={() => navigate(ROUTES.AUTH)}>로그인 / 회원가입</button>
        )}
      </div>
    </header>
  );
};