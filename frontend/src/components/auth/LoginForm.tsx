import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createPortal } from 'react-dom';
import { useAuthStore } from '../../store/authStore';
import { authApi } from '../../api/authApi';
import { ROUTES } from '../../constants/routes';

interface LoginFormProps {
  onSwitchMode: (mode: 'signup' | 'find') => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSwitchMode }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // 관리자 선택 모달 상태
  const [showAdminChoice, setShowAdminChoice] = useState(false);
  const [tempAdminData, setTempAdminData] = useState<any>(null);

  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);

  // 로그인 성공 처리 공통 함수
  const handleLoginSuccess = (userData: any, token: string) => {
    if (userData.role === 'admin') {
      setTempAdminData({ userData, token });
      setShowAdminChoice(true);
    } else {
      setAuth(userData, token);
      navigate(ROUTES.HOME);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
  
    const targetEmail = email.trim();
    const targetPassword = password.trim();

    if (!targetEmail || !targetPassword) {
      setError('아이디와 비밀번호를 모두 입력해주세요.');
      return;
    }
    
    // admin이 아닌 경우에만 이메일 정규식 검사 실행
    const emailPattern = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
    if (targetEmail !== 'admin' && !emailPattern.test(targetEmail)) {
      setError('유효한 이메일 형식을 입력해주세요.');
      return;
    }

    // 1. admin 하드코딩 예외 처리
    if (targetEmail === 'admin' && targetPassword === '1234') {
      const adminUser = {
        id: '999',
        email: 'admin',
        name: '관리자',
        role: 'admin',
        tier: 'premium' as const,
      };
      handleLoginSuccess(adminUser, 'admin_temp_token');
      return;
    }

    setIsLoading(true);

    try {
      // 💡 핵심 2: 공백이 제거된 데이터로 API 호출
      const data = await authApi.login({ email: targetEmail, password: targetPassword });
      
      handleLoginSuccess({
        id: data.id,
        email: data.email,
        tier: data.tier,
        name: data.name ?? undefined,
        profile_image_url: data.profile_image_url ?? undefined,
        role: data.role
      }, data.access_token);
      
    } catch (err: any) {
      console.error("로그인 실패 에러 상세:", err);

      const errMsg = err.response?.data?.detail;
      setError(typeof errMsg === 'string' ? errMsg : '로그인에 실패했습니다. (콘솔 로그를 확인해주세요)');
    } finally {
      setIsLoading(false);
    }
  };

  // 백엔드가 Multipass 등 가상환경에 있다면 이 주소의 localhost도 해당 IP로 바꿔야 합니다.
  const GOOGLE_URI = "http://localhost:8000/api/v1/auth/google/start";
  const KAKAO_URI = "http://localhost:8000/api/v1/auth/kakao/start";

  return (
    <div className="login-form-container">
      <div className="login-logo">AI<span>WORK</span></div>

      <form onSubmit={handleSubmit}>
        <div className="input-group">
          <input
            id="email"
            type="text"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="아이디(이메일)를 입력하세요"
            required
            autoComplete="email"
          />
        </div>

        <div className="input-group">
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="비밀번호를 입력하세요"
            required
            autoComplete="current-password"
          />
        </div>

        {error && <div className="custom-error-msg" style={{ color: '#e74c3c', fontSize: '13px', textAlign: 'center', marginBottom: '10px' }}>{error}</div>}

        <button type="submit" className="submit-btn" disabled={isLoading}>
          {isLoading ? '로그인 중' : '로그인'}
        </button>
      </form>

      <div className="helper-links">
        <button type="button" className="text-btn" onClick={() => onSwitchMode('find')} style={{ cursor: 'pointer', border: 'none', background: 'none', color: '#888' }}>
          비밀번호 찾기
        </button>
        <span className="helper-sep">|</span>
        <button type="button" className="text-btn" onClick={() => onSwitchMode('signup')} style={{ cursor: 'pointer', border: 'none', background: 'none', color: '#888' }}>
          회원가입
        </button>
      </div>
      
      <div className="divider-row">소셜 계정으로 로그인</div>
      
      <div className="social-btns">
        <a href={GOOGLE_URI} className="social-btn btn-google">
          <svg width="20" height="20" viewBox="0 0 48 48">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
          </svg>
          Google로 계속하기
        </a>
        <a href={KAKAO_URI} className="social-btn btn-kakao">
          <svg width="20" height="20" viewBox="0 0 24 24">
            <path fill="#3c1e1e" d="M12 3C6.477 3 2 6.477 2 10.5c0 2.611 1.563 4.911 3.938 6.258L4.5 21l4.688-2.344A11.3 11.3 0 0012 18c5.523 0 10-3.477 10-7.5S17.523 3 12 3z"/>
          </svg>
          카카오로 계속하기
        </a>
      </div>

      {/* 관리자 선택 모달 (Portal 사용) */}
      {showAdminChoice && createPortal(
        <div className="custom-modal-overlay">
          <div className="custom-modal text-center">
            <div className="admin-choice-box" style={{ 
              marginBottom: '20px', padding: '15px', backgroundColor: '#e3f2fd',
              borderRadius: '8px', border: '1px solid #90caf9'
            }}>
              <p style={{ color: '#0d47a1', fontWeight: 'bold', margin: 0, lineHeight: '1.5' }}>
                관리자 권한 인증 완료!<br />이동할 페이지를 선택하세요.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button 
                className="action-btn" 
                style={{ flex: 1, backgroundColor: '#f5f5f5', color: '#333', border: '1px solid #ddd', padding: '10px', borderRadius: '6px', cursor: 'pointer' }}
                onClick={() => {
                  setAuth(tempAdminData.userData, tempAdminData.token);
                  navigate(ROUTES.HOME);
                }}
              >
                기존 홈 화면
              </button>
              <button 
                className="action-btn primary" 
                style={{ flex: 1, backgroundColor: '#1976d2', color: '#fff', border: 'none', padding: '10px', borderRadius: '6px', cursor: 'pointer' }}
                onClick={() => {
                  setAuth(tempAdminData.userData, tempAdminData.token);
                  navigate('/admin'); // 관리자 전용 경로
                }}
              >
                관리자 페이지
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};