import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import "./LoginModal.scss";

export const LoginModal = () => {
  const navigate = useNavigate();
  const { isLoginModalOpen, closeLoginModal } = useAuthStore();

  if (!isLoginModalOpen) return null;

  return (
    <div className="login-modal-overlay" onClick={closeLoginModal}>
      <div className="login-modal-container" onClick={(e) => e.stopPropagation()}>
        <h2>
          로그인 후 이용해주세요
        </h2>
        <p>
          3초 만에 소셜 로그인하고<br />
          마우스 클릭 없는 혁신적인 AI 면접을 경험하세요.
        </p>
        <div className="modal-btn-group">
          <button 
            className="btn-login-go" 
            onClick={() => {
              closeLoginModal();
              navigate("/auth");
            }}
          >
            로그인하러 가기
          </button>
          <button 
            className="btn-go-back" 
            onClick={closeLoginModal}
          >
            이전 페이지로 돌아가기
          </button>
        </div>
      </div>
    </div>
  );
};