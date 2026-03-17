import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { LoginForm } from '../components/auth/LoginForm';
import { SignUpForm } from '../components/auth/SignUpForm';
import { FindPassword } from '../components/auth/FindPassword';
import './Auth.scss';

export const Auth = () => {
  const [searchParams] = useSearchParams();
  const initialMode = (searchParams.get('mode') as 'login' | 'signup' | 'find') || 'login';
  
  const [mode, setMode] = useState<'login' | 'signup' | 'find'>(initialMode);

  useEffect(() => {
    const modeParam = searchParams.get('mode') as 'login' | 'signup' | 'find';
    if (modeParam) setMode(modeParam);
  }, [searchParams]);

  const handleSwitchMode = (newMode?: 'login' | 'signup' | 'find') => {
    if (typeof newMode === 'string') {
      setMode(newMode);
    } else {
      setMode('login');
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box glass-panel">
        {mode === 'login' && <LoginForm onSwitchMode={handleSwitchMode} />}
        {mode === 'signup' && <SignUpForm onSwitchMode={() => handleSwitchMode('login')} />}
        {mode === 'find' && <FindPassword onSwitchMode={handleSwitchMode} />}
      </div>
    </div>
  );
};