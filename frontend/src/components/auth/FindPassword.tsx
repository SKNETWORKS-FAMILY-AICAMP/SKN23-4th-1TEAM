import { useState, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { authApi } from "../../api/authApi";
import "./FindPassword.scss";

interface FindPasswordProps {
  onSwitchMode: (mode: "login" | "signup" | "find") => void;
}

export const FindPassword = ({ onSwitchMode }: FindPasswordProps) => {
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("");
  const [authCode, setAuthCode] = useState("");
  const [inputCode, setInputCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);

  const emailPattern = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
  const pwPattern = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[\W_]).{8,}$/;

  const handleKeyDown = (
    e: KeyboardEvent<HTMLInputElement>,
    callback: () => void,
  ) => {
    if (e.key === "Enter") {
      callback();
    }
  };

  const handleSendEmail = async () => {
    setError("");
    setSuccess("");
    if (!email || !emailPattern.test(email)) {
      setError("유효한 이메일 형식이 아닙니다.");
      return;
    }
    setIsLoading(true);
    try {
      const generatedCode = Math.floor(
        100000 + Math.random() * 900000,
      ).toString();
      await authApi.sendResetEmail({ email, auth_code: generatedCode });
      setAuthCode(generatedCode);
      setSuccess("인증번호가 발송되었습니다. 이메일함을 확인해주세요!");
      setStep(2);
    } catch (err: any) {
      setError(err.response?.data?.detail || "이메일 발송 실패");
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyCode = () => {
    if (inputCode === authCode) {
      setSuccess("");
      setStep(3);
    } else {
      setError("인증번호가 일치하지 않습니다.");
    }
  };

  const handleResetPassword = async () => {
    if (
      !newPassword ||
      !pwPattern.test(newPassword) ||
      newPassword !== confirmPassword
    ) {
      setError("비밀번호 형식이 맞지 않거나 일치하지 않습니다.");
      return;
    }
    setIsLoading(true);
    try {
      await authApi.resetPassword({ email, new_password: newPassword });
      setShowSuccessModal(true);
      setTimeout(() => onSwitchMode("login"), 3000);
    } catch (err: any) {
      setError("변경 실패");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="find-pw-container">
      <div className="login-logo">비밀번호 찾기</div>
      <p className="info-text-top">
        가입하신 아이디(이메일)을/를 입력해주세요.
      </p>
      {step === 1 && (
        <div className="step-container">
          <div className="input-group">
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => handleKeyDown(e, handleSendEmail)}
              placeholder="이메일을 입력하세요"
            />
          </div>
          {error && <div className="status-msg text-error">{error}</div>}
          {success && <div className="status-msg text-success">{success}</div>}
          <button
            className="submit-btn"
            onClick={handleSendEmail}
            disabled={isLoading}
          >
            이메일 인증
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="step-container">
          <div className="input-group">
            <input
              type="text"
              value={inputCode}
              onChange={(e) => setInputCode(e.target.value)}
              onKeyDown={(e) => handleKeyDown(e, handleVerifyCode)}
              placeholder="6자리 숫자 입력"
            />
          </div>
          {error && <div className="status-msg text-error">{error}</div>}
          {success && <div className="status-msg text-success">{success}</div>}
          <button className="submit-btn" onClick={handleVerifyCode}>
            인증 확인
          </button>
        </div>
      )}

      {step === 3 && (
        <div className="step-container">
          <div className="input-group">
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="새 비밀번호"
            />
          </div>
          <div className="input-group">
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              onKeyDown={(e) => handleKeyDown(e, handleResetPassword)}
              placeholder="새 비밀번호 확인"
            />
          </div>
          {error && <div className="status-msg text-error">{error}</div>}
          <button
            className="submit-btn"
            onClick={handleResetPassword}
            disabled={isLoading}
          >
            변경 완료
          </button>
        </div>
      )}

      <div className="helper-links">
        <button className="text-btn" onClick={() => onSwitchMode("login")}>
          로그인으로 돌아가기
        </button>
      </div>

      {showSuccessModal &&
        createPortal(
          <div className="success-modal-overlay">
            <div className="success-modal">
              <div className="icon">👾</div>
              <h2>변경 완료!</h2>
              <p>로그인 페이지로 이동합니다.</p>
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
};
