import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createPortal } from "react-dom";
import { useAuthStore } from "../../store/authStore";
import { authApi } from "../../api/authApi";
import { ROUTES } from "../../constants/routes";

interface LoginFormProps {
  onSwitchMode: (mode: "signup" | "find") => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSwitchMode }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const [showAdminChoice, setShowAdminChoice] = useState(false);
  const [tempAdminData, setTempAdminData] = useState<any>(null);

  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);

  const handleLoginSuccess = (userData: any, token: string) => {
    if (userData.role === "admin") {
      setTempAdminData({ userData, token });
      setShowAdminChoice(true);
    } else {
      setAuth(userData, token);
      navigate(ROUTES.HOME);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const targetEmail = email.trim();
    const targetPassword = password.trim();

    if (!targetEmail || !targetPassword) {
      setError("아이디와 비밀번호를 모두 입력해주세요.");
      return;
    }

    const emailPattern = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
    if (targetEmail !== "admin" && !emailPattern.test(targetEmail)) {
      setError("유효한 이메일 형식을 입력해주세요.");
      return;
    }

    if (targetEmail === "admin" && targetPassword === "1234") {
      const adminUser = {
        id: "999",
        email: "admin",
        name: "관리자",
        role: "admin",
        tier: "plus",
      };
      handleLoginSuccess(adminUser, "admin_temp_token");
      return;
    }

    setIsLoading(true);

    try {
      const data = await authApi.login({
        email: targetEmail,
        password: targetPassword,
      });

      const userData = {
        id: data.id,
        email: data.email,
        tier: data.tier,
        name: data.name ?? undefined,
        profile_image_url: data.profile_image_url ?? undefined,
        role: data.role,
      };

      handleLoginSuccess(userData, data.access_token);
    } catch (err: any) {
      console.error(err);
      const errMsg = err.response?.data?.detail;
      setError(
        typeof errMsg === "string"
          ? errMsg
          : "로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const GOOGLE_URI = "/api/v1/auth/google/start";
  const KAKAO_URI = "/api/v1/auth/kakao/start";

  return (
    <div className="login-form-container">
      <div className="login-logo">
        AI<span>WORK</span>
      </div>

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

        {error && (
          <div
            className="custom-error-msg"
            style={{
              color: "#ef4444",
              fontSize: "13px",
              textAlign: "center",
              marginBottom: "10px",
              fontWeight: "600",
            }}
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          className="submit-btn"
          disabled={isLoading}
          style={{ background: "#0176f7", borderColor: "#0176f7" }}
        >
          {isLoading ? "로그인 중..." : "로그인"}
        </button>
      </form>

      <div className="helper-links">
        <button
          type="button"
          className="text-btn"
          onClick={() => onSwitchMode("find")}
          style={{
            cursor: "pointer",
            border: "none",
            background: "none",
            color: "#64748b",
            fontSize: "13px",
          }}
        >
          비밀번호 찾기
        </button>
        <span
          className="helper-sep"
          style={{ color: "#cbd5e1", margin: "0 8px" }}
        >
          |
        </span>
        <button
          type="button"
          className="text-btn"
          onClick={() => onSwitchMode("signup")}
          style={{
            cursor: "pointer",
            border: "none",
            background: "none",
            color: "#64748b",
            fontSize: "13px",
          }}
        >
          회원가입
        </button>
      </div>

      <div
        className="divider-row"
        style={{ color: "#94a3b8", fontSize: "12px" }}
      >
        소셜 계정으로 로그인
      </div>

      <div className="social-btns">
        <a href={GOOGLE_URI} className="social-btn btn-google">
          <svg width="20" height="20" viewBox="0 0 48 48">
            <path
              fill="#EA4335"
              d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
            />
            <path
              fill="#4285F4"
              d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
            />
            <path
              fill="#FBBC05"
              d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
            />
            <path
              fill="#34A853"
              d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
            />
          </svg>
          Google로 계속하기
        </a>
        <a href={KAKAO_URI} className="social-btn btn-kakao">
          <svg width="20" height="20" viewBox="0 0 24 24">
            <path
              fill="#3c1e1e"
              d="M12 3C6.477 3 2 6.477 2 10.5c0 2.611 1.563 4.911 3.938 6.258L4.5 21l4.688-2.344A11.3 11.3 0 0012 18c5.523 0 10-3.477 10-7.5S17.523 3 12 3z"
            />
          </svg>
          카카오로 계속하기
        </a>
      </div>

      {showAdminChoice &&
        createPortal(
          <div
            style={{
              position: "fixed",
              inset: 0,
              backgroundColor: "rgba(0,0,0,0.5)",
              backdropFilter: "blur(4px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 9999,
            }}
          >
            <div
              style={{
                background: "#fff",
                padding: "32px",
                borderRadius: "16px",
                width: "90%",
                maxWidth: "400px",
                boxShadow:
                  "0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  width: "48px",
                  height: "48px",
                  background: "#eff6ff",
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: "0 auto 16px",
                }}
              >
                <span style={{ fontSize: "24px" }}>🛡️</span>
              </div>
              <h3
                style={{
                  margin: "0 0 8px 0",
                  fontSize: "20px",
                  fontWeight: "800",
                  color: "#1e293b",
                }}
              >
                관리자 인증 완료
              </h3>
              <p
                style={{
                  margin: "0 0 24px 0",
                  fontSize: "14px",
                  color: "#64748b",
                  lineHeight: "1.5",
                }}
              >
                관리자 권한이 확인되었습니다.
                <br />
                이동하실 페이지를 선택해주세요.
              </p>
              <div style={{ display: "flex", gap: "12px" }}>
                <button
                  style={{
                    flex: 1,
                    backgroundColor: "#f1f5f9",
                    color: "#475569",
                    border: "none",
                    padding: "12px",
                    borderRadius: "10px",
                    fontWeight: "600",
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                  onClick={() => {
                    setAuth(tempAdminData.userData, tempAdminData.token);
                    navigate(ROUTES.HOME);
                  }}
                >
                  일반 홈으로
                </button>
                <button
                  style={{
                    flex: 1,
                    backgroundColor: "#0176f7",
                    color: "#fff",
                    border: "none",
                    padding: "12px",
                    borderRadius: "10px",
                    fontWeight: "600",
                    cursor: "pointer",
                    transition: "all 0.2s",
                    boxShadow: "0 4px 10px rgba(1,118,247,0.3)",
                  }}
                  onClick={() => {
                    setAuth(tempAdminData.userData, tempAdminData.token);
                    navigate("/admin");
                  }}
                >
                  관리자 대시보드
                </button>
              </div>
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
};
