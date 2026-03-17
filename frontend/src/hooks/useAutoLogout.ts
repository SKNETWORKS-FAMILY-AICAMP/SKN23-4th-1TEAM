import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { authApi } from '../api/authApi';

export const useAutoLogout = (timeoutMinutes: number = 30) => {
  const navigate = useNavigate();
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleLogout = async () => {
    try {
      // 백엔드 로그아웃 API 호출 (리프레시 토큰 및 쿠키 삭제)
      await authApi.logout(); 
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      // 프론트엔드 상태 초기화 및 이동
      clearAuth();
      alert(`${timeoutMinutes}분 동안 활동이 없어 자동 로그아웃 되었습니다.`);
      navigate('/auth');
    }
  };

  const resetTimer = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    
    // 밀리초 단위 계산 (30분 = 30 * 60 * 1000 = 1,800,000ms)
    timerRef.current = setTimeout(handleLogout, timeoutMinutes * 60 * 1000);
  };

  useEffect(() => {
    // 로그인 상태가 아닐 때는 타이머를 돌리지 않음
    if (!isAuthenticated) return;

    // 감지할 사용자 활동 이벤트 목록
    const events = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'];
    
    // 이벤트 발생 시 타이머 초기화 함수 연결
    events.forEach((event) => window.addEventListener(event, resetTimer));
    
    // 컴포넌트 마운트 시 최초 타이머 시작
    resetTimer();

    // 클린업 함수
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      events.forEach((event) => window.removeEventListener(event, resetTimer));
    };
  }, [isAuthenticated, timeoutMinutes]);
};