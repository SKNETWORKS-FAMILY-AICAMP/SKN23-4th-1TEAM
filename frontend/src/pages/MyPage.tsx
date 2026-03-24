import { useEffect, useRef, useState } from "react";
import { loadPaymentWidget } from "@tosspayments/payment-widget-sdk";
import type { PaymentWidgetInstance } from "@tosspayments/payment-widget-sdk";
import { useAuthStore } from "../store/authStore";
import { useNavigate } from "react-router-dom";
import { Header } from "../components/common/Header";
import {
  ChevronRight,
  ArrowLeft,
  Plus,
  Upload,
  X,
  AlertCircle,
} from "lucide-react";
import { authApi } from "../api/authApi";
import "./MyPage.scss";
import { GuideChatbot } from "../components/chat/GuideChatbot";

const clientKey = "test_gck_docs_Ovk5rk1EwkEbP0W43n07xlzm";
const customerKey = "test_customer_key_12345";

export const MyPage = () => {
  const { user, updateTier, clearAuth, setUser } = useAuthStore();
  const navigate = useNavigate();

  const paymentWidgetRef = useRef<PaymentWidgetInstance | null>(null);
  const paymentMethodsWidgetRef = useRef<ReturnType<
    PaymentWidgetInstance["renderPaymentMethods"]
  > | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [price, setPrice] = useState(9900);
  const [isWidgetReady, setIsWidgetReady] = useState(false);
  const [showUpgrade, setShowUpgrade] = useState(false);

  const [showPhotoModal, setShowPhotoModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [pwStep, setPwStep] = useState(1);
  const [authCode, setAuthCode] = useState("");
  const [inputCode, setInputCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwError, setPwError] = useState("");
  const [isPwLoading, setIsPwLoading] = useState(false);

  const [showCancelSuccessModal, setShowCancelSuccessModal] = useState(false);
  const [expireDate, setExpireDate] = useState("");

  const [confirmModal, setConfirmModal] = useState<{
    title: string;
    desc: React.ReactNode;
    iconBg: string;
    iconColor: string;
    btnText: string;
    onConfirm: () => void;
  } | null>(null);

  const defaultAvatar =
    "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png";
  const pwPattern = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[\W_]).{8,}$/;

  const showToast = (message: string) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(null), 3000);
  };

  useEffect(() => {
    if (!showUpgrade || user?.tier === "premium") return;

    const fetchPaymentWidget = async () => {
      try {
        const paymentWidget = await loadPaymentWidget(clientKey, customerKey);
        const paymentMethodsWidget = paymentWidget.renderPaymentMethods(
          "#payment-widget",
          { value: price },
          { variantKey: "DEFAULT" },
        );
        paymentWidget.renderAgreement("#agreement", {
          variantKey: "AGREEMENT",
        });

        paymentWidgetRef.current = paymentWidget;
        paymentMethodsWidgetRef.current = paymentMethodsWidget;
        setIsWidgetReady(true);
      } catch (error) {
        console.error("Failed to load Toss Payments widget:", error);
      }
    };

    fetchPaymentWidget();
  }, [showUpgrade, price, user?.tier]);

  const handlePayment = async () => {
    const paymentWidget = paymentWidgetRef.current;
    if (!paymentWidget) return;

    try {
      await paymentWidget.requestPayment({
        orderId: `order_${Math.random().toString(36).substring(2, 10)}`,
        orderName: "PRO 멤버십 구독 (월간)",
        successUrl: `${window.location.origin}${window.location.pathname}?success=true`,
        failUrl: `${window.location.origin}${window.location.pathname}?fail=true`,
        customerEmail: user?.email,
        customerName: user?.name,
      });
    } catch (error) {
      console.error("Payment blocked or failed:", error);
    }
  };

  useEffect(() => {
    const handlePaymentResult = async () => {
      const params = new URLSearchParams(window.location.search);

      if (!user || !user.email) return;

      if (params.get("success") === "true") {
        try {
          await authApi.upgradeTier();
          updateTier("premium");
          showToast("PRO 구독이 완료되었습니다!");
        } catch (error) {
          console.error("Upgrade failed:", error);
          showToast("등급 업데이트 중 오류가 발생했습니다.");
        } finally {
          window.history.replaceState({}, "", window.location.pathname);
        }
      } else if (params.get("fail") === "true") {
        showToast("결제에 실패했습니다. 다시 시도해 주세요.");
        window.history.replaceState({}, "", window.location.pathname);
      }
    };

    handlePaymentResult();
  }, [user, updateTier]);

  const openCancelSubscriptionModal = () => {
    setConfirmModal({
      title: "PRO 구독을 해지하시겠습니까?",
      desc: (
        <>
          해지를 예약하시더라도, 이번 결제 주기가 끝나는
          <br />
          다음 갱신일 전까지는 PRO 혜택이 유지됩니다.
        </>
      ),
      iconBg: "#fef2f2",
      iconColor: "#ef4444",
      btnText: "해지 예약하기",
      onConfirm: async () => {
        try {
          const res = await authApi.downgradeTier();
          setExpireDate(res.expire_date);

          if (user) {
            setUser({
              ...user,
              is_cancel_scheduled: 1,
              pro_expire_date: res.expire_date,
            });
          }

          setConfirmModal(null);
          setShowCancelSuccessModal(true);
        } catch (error) {
          console.error("Cancel subscription failed:", error);
          showToast("구독 해지 처리 중 오류가 발생했습니다.");
          setConfirmModal(null);
        }
      },
    });
  };

  const handleReactivateSubscription = () => {
    setConfirmModal({
      title: "구독 유지를 결정하셨나요?",
      desc: "해지 예약이 취소되며, PRO 멤버십 혜택을 계속 이용하실 수 있습니다.",
      iconBg: "#eff6ff",
      iconColor: "#0176f7",
      btnText: "확인",
      onConfirm: async () => {
        try {
          await authApi.reactivateSubscription();
          setConfirmModal(null);
          showToast("구독이 다시 활성화되었습니다!");

          if (user) {
            setUser({
              ...user,
              is_cancel_scheduled: 0,
              pro_expire_date: null,
            });
          }
        } catch (error) {
          setConfirmModal(null);
          showToast("구독 유지 처리에 실패했습니다.");
        }
      },
    });
  };

  const openWithdrawModal = () => {
    setConfirmModal({
      title: "정말 탈퇴하시겠습니까?",
      desc: (
        <>
          모든 면접 기록과 이력서 정보가 삭제되며
          <br />
          복구할 수 없습니다.
        </>
      ),
      iconBg: "#fef2f2",
      iconColor: "#ef4444",
      btnText: "탈퇴하기",
      onConfirm: async () => {
        try {
          await authApi.withdraw();
          clearAuth();
          navigate("/auth");
        } catch (error) {
          console.error(error);
          showToast("회원 탈퇴 처리 중 오류가 발생했습니다.");
        } finally {
          setConfirmModal(null);
        }
      },
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleUploadPhoto = async () => {
    if (!selectedFile || !user) return;
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const data = await authApi.updateProfileImage(formData);
      const newImageUrl = data.profile_image_url;

      useAuthStore.setState((state: any) => ({
        user: { ...state.user, profile_image_url: newImageUrl },
      }));

      setShowPhotoModal(false);
      setPreviewUrl(null);
      setSelectedFile(null);
      showToast("프로필 사진 변경 완료!");
    } catch (error) {
      console.error(error);
      showToast("이미지 업로드에 실패했습니다.");
    } finally {
      setIsUploading(false);
    }
  };

  const resetPwModalState = () => {
    setPwStep(1);
    setAuthCode("");
    setInputCode("");
    setNewPassword("");
    setConfirmPassword("");
    setPwError("");
    setShowPasswordModal(false);
  };

  const handlePwSendEmail = async () => {
    if (!user?.email) return;
    setPwError("");
    setIsPwLoading(true);
    try {
      const generatedCode = Math.floor(
        100000 + Math.random() * 900000,
      ).toString();
      await authApi.sendResetEmail({
        email: user.email,
        auth_code: generatedCode,
      });
      setAuthCode(generatedCode);
      setPwStep(2);
      showToast("이메일로 인증 코드가 발송되었습니다.");
    } catch (err: any) {
      setPwError(
        err.response?.data?.detail || "인증 코드 발송에 실패했습니다.",
      );
    } finally {
      setIsPwLoading(false);
    }
  };

  const handlePwVerifyCode = () => {
    setPwError("");
    if (inputCode === authCode) {
      setPwStep(3);
    } else {
      setPwError("인증 코드가 일치하지 않습니다.");
    }
  };

  const handlePwChange = async () => {
    if (!user?.email) return;
    setPwError("");

    if (!newPassword || !pwPattern.test(newPassword)) {
      setPwError("영문, 숫자, 특수문자를 포함하여 8자리 이상이어야 합니다.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwError("비밀번호가 일치하지 않습니다.");
      return;
    }

    setIsPwLoading(true);
    try {
      await authApi.resetPassword({
        email: user.email,
        new_password: newPassword,
      });
      resetPwModalState();
      showToast("비밀번호가 안전하게 변경되었습니다.");
    } catch (err: any) {
      setPwError(err.response?.data?.detail || "비밀번호 변경에 실패했습니다.");
    } finally {
      setIsPwLoading(false);
    }
  };

  return (
    <div className="mypage-layout">
      {toastMessage && <div className="toast-notification">{toastMessage}</div>}

      <Header />

      <main className="mypage-content">
        <label className="page-header-title">내 정보 관리</label>

        <div className="profile-hero-card">
          <div className="profile-hero-inner">
            <div
              className="avatar-wrap"
              onClick={() => setShowPhotoModal(true)}
            >
              <img
                src={user?.profile_image_url || defaultAvatar}
                alt="Profile"
                className="avatar"
              />
              <div className="avatar-overlay">
                <Plus size={24} />
              </div>
            </div>
            <div className="info-wrap">
              <div className="name-row">
                <h2>{user?.name || "게스트"}</h2>
                <span className={`tier-badge ${user?.tier || "normal"}`}>
                  {user?.tier === "premium" ? "PRO 회원" : "NORMAL 회원"}
                </span>
              </div>
              <p className="email">{user?.email}</p>
            </div>
          </div>
        </div>

        <section className="info-section">
          <div className="section-title">계정 정보</div>
          <div className="list-row">
            <div>
              <div className="list-label">이메일 (아이디)</div>
              <div className="list-value">{user?.email}</div>
            </div>
          </div>
          <div className="list-row">
            <div>
              <div className="list-label">이름</div>
              <div className="list-value">{user?.name}</div>
            </div>
          </div>
          <div className="list-row no-border">
            <div>
              <div className="list-label">회원 등급</div>
              <div className="list-value tier">
                {user?.tier === "premium" ? "PRO 회원" : "NORMAL 회원"}
              </div>
            </div>

            {/* 1. NORMAL 회원일 때 (업그레이드 버튼) */}
            {user?.tier !== "premium" && (
              <button
                className="upgrade-action-btn"
                onClick={() => setShowUpgrade(true)}
              >
                PRO 업그레이드
              </button>
            )}

            {/* 2. PRO 회원일 때 (해지 여부에 따른 버튼 분기) */}
            {user?.tier === "premium" &&
              (user?.is_cancel_scheduled ? (
                /* 해지 예약 상태 -> 구독 유지 버튼 */
                <button
                  className="upgrade-action-btn"
                  onClick={handleReactivateSubscription}
                >
                  구독 유지하기
                </button>
              ) : (
                /* 정상 구독 상태 -> 구독 해지 버튼 */
                <button
                  className="upgrade-action-btn"
                  onClick={openCancelSubscriptionModal}
                >
                  구독 해지
                </button>
              ))}
          </div>
        </section>

        <section className="info-section">
          <div className="section-title">보안</div>
          <div
            className="list-row action-row no-border"
            onClick={() => setShowPasswordModal(true)}
          >
            <div>
              <div className="list-label">비밀번호</div>
              <div className="list-value">••••••••</div>
            </div>
            <ChevronRight className="arrow-icon" size={20} />
          </div>
        </section>

        <div className="footer-actions">
          <p className="footer-desc">더 이상 서비스를 이용하지 않으시나요?</p>
          <div className="btn-group">
            <button className="withdraw-btn" onClick={openWithdrawModal}>
              회원 탈퇴
            </button>
          </div>
        </div>
      </main>
      <GuideChatbot />
      {/* 공통 커스텀 컨펌 모달 (해지 재확인, 탈퇴 등) */}
      {confirmModal && (
        <div className="upgrade-modal-overlay">
          <div className="confirm-modal-content">
            <div
              className="confirm-icon"
              style={{
                background: confirmModal.iconBg,
                color: confirmModal.iconColor,
              }}
            >
              <AlertCircle size={32} />
            </div>
            <h3>{confirmModal.title}</h3>
            <p>{confirmModal.desc}</p>
            <div className="confirm-actions">
              <button
                className="btn-cancel"
                onClick={() => setConfirmModal(null)}
              >
                취소하기
              </button>
              <button
                className="btn-proceed"
                onClick={confirmModal.onConfirm}
                style={{ background: confirmModal.iconColor }}
              >
                {confirmModal.btnText}
              </button>
            </div>
          </div>
        </div>
      )}

      {showCancelSuccessModal && (
        <div className="upgrade-modal-overlay">
          <div
            className="confirm-modal-content"
            style={{ padding: "40px 32px 32px" }}
          >
            <div
              className="confirm-icon"
              style={{
                background: "#f0fdf4",
                color: "#16a34a",
                fontSize: "32px",
                width: "64px",
                height: "64px",
                borderRadius: "50%",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: "24px",
              }}
            >
              ✓
            </div>
            <h3
              style={{
                fontSize: "20px",
                fontWeight: 800,
                color: "#111",
                marginBottom: "12px",
              }}
            >
              구독 해지 예약 완료
            </h3>
            <p
              style={{
                fontSize: "15px",
                color: "#64748b",
                lineHeight: "1.6",
                marginBottom: "28px",
              }}
            >
              정상적으로 해지 예약이 처리되었습니다.
              <br />
              <strong style={{ color: "#0176f7" }}>{expireDate}</strong>까지는
              <br />
              PRO 혜택을 계속 이용하실 수 있습니다.
            </p>
            <div
              className="confirm-actions"
              style={{ display: "flex", width: "100%" }}
            >
              <button
                className="btn-proceed"
                onClick={() => setShowCancelSuccessModal(false)}
                style={{
                  background: "#0176f7",
                  color: "#fff",
                  width: "100%",
                  padding: "14px 0",
                  borderRadius: "12px",
                  fontSize: "15px",
                  fontWeight: 700,
                  border: "none",
                  cursor: "pointer",
                }}
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PRO 멤버십 업그레이드 모달 */}
      {showUpgrade && (
        <div className="upgrade-modal-overlay">
          <div className="upgrade-modal">
            <div className="modal-header">
              <button
                className="back-btn"
                onClick={() => setShowUpgrade(false)}
              >
                <ArrowLeft size={20} />
              </button>
              <h2>PRO 멤버십 업그레이드</h2>
            </div>
            <div className="modal-body">
              <div className="plan-card">
                <h3>무제한 AI 면접과 이력서 정밀 분석</h3>
                <div className="price-tag">
                  <span className="amount">₩9,900</span>
                  <span className="period">/ 월</span>
                </div>
              </div>

              <div className="payment-widget-container">
                <div id="payment-widget" />
                <div id="agreement" />
                <button
                  className="checkout-btn"
                  onClick={handlePayment}
                  disabled={!isWidgetReady}
                >
                  {isWidgetReady ? "결제하기" : "결제 모듈 불러오는 중..."}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 프로필 사진 변경 모달 */}
      {showPhotoModal && (
        <div className="upgrade-modal-overlay">
          <div className="photo-modal">
            <div className="photo-modal-header">
              <h3>프로필 사진 올리기</h3>
              <button
                onClick={() => {
                  setShowPhotoModal(false);
                  setPreviewUrl(null);
                  setSelectedFile(null);
                }}
              >
                <X size={20} />
              </button>
            </div>
            <div className="photo-modal-body">
              <input
                type="file"
                ref={fileInputRef}
                accept="image/png, image/jpeg, image/jpg"
                onChange={handleFileChange}
                style={{ display: "none" }}
              />

              <div
                className="preview-container"
                onClick={() => fileInputRef.current?.click()}
              >
                {previewUrl ? (
                  <img
                    src={previewUrl}
                    alt="Preview"
                    className="preview-image"
                  />
                ) : (
                  <div className="empty-preview">
                    <Upload size={32} color="#9ca3af" />
                    <span>이미지 파일 선택</span>
                  </div>
                )}
              </div>

              <button
                className="apply-btn"
                onClick={handleUploadPhoto}
                disabled={!selectedFile || isUploading}
              >
                {isUploading ? "서버에 저장 중..." : "적용하기"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 비밀번호 변경 모달 */}
      {showPasswordModal && (
        <div className="upgrade-modal-overlay">
          <div className="photo-modal">
            <div className="photo-modal-header">
              <h3>비밀번호 변경</h3>
              <button onClick={resetPwModalState}>
                <X size={20} />
              </button>
            </div>
            <div className="photo-modal-body">
              {pwStep === 1 && (
                <>
                  <div style={{ textAlign: "center", marginBottom: "16px" }}>
                    <div style={{ fontSize: "32px", marginBottom: "8px" }}>
                      📧
                    </div>
                    <p
                      style={{
                        fontSize: "13px",
                        color: "#555",
                        lineHeight: "1.5",
                      }}
                    >
                      가입하신 이메일로 인증 코드를 발송합니다.
                      <br />
                      <b style={{ color: "#0176f7" }}>{user?.email}</b>
                    </p>
                  </div>
                  {pwError && (
                    <div
                      style={{
                        fontSize: "13px",
                        color: "#e74c3c",
                        textAlign: "center",
                        marginBottom: "12px",
                      }}
                    >
                      {pwError}
                    </div>
                  )}
                  <button
                    className="apply-btn"
                    onClick={handlePwSendEmail}
                    disabled={isPwLoading}
                  >
                    {isPwLoading ? "발송 중..." : "인증 코드 발송"}
                  </button>
                </>
              )}

              {pwStep === 2 && (
                <>
                  <div style={{ textAlign: "center", marginBottom: "16px" }}>
                    <div style={{ fontSize: "32px", marginBottom: "8px" }}>
                      🔑
                    </div>
                    <p style={{ fontSize: "13px", color: "#555" }}>
                      이메일로 발송된 6자리 코드를 입력해주세요.
                    </p>
                  </div>
                  <input
                    type="text"
                    value={inputCode}
                    onChange={(e) => setInputCode(e.target.value)}
                    placeholder="6자리 입력"
                    maxLength={6}
                    style={{
                      width: "100%",
                      padding: "12px",
                      borderRadius: "8px",
                      border: "1px solid #e2e8f0",
                      marginBottom: "12px",
                    }}
                  />
                  {pwError && (
                    <div
                      style={{
                        fontSize: "13px",
                        color: "#e74c3c",
                        textAlign: "center",
                        marginBottom: "12px",
                      }}
                    >
                      {pwError}
                    </div>
                  )}
                  <button className="apply-btn" onClick={handlePwVerifyCode}>
                    확인
                  </button>
                </>
              )}

              {pwStep === 3 && (
                <>
                  <div style={{ textAlign: "center", marginBottom: "16px" }}>
                    <div style={{ fontSize: "32px", marginBottom: "8px" }}>
                      🔒
                    </div>
                    <p style={{ fontSize: "13px", color: "#555" }}>
                      새로운 비밀번호를 설정해주세요.
                    </p>
                  </div>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="새 비밀번호"
                    style={{
                      width: "100%",
                      padding: "12px",
                      borderRadius: "8px",
                      border: "1px solid #e2e8f0",
                      marginBottom: "12px",
                    }}
                  />
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="새 비밀번호 확인"
                    style={{
                      width: "100%",
                      padding: "12px",
                      borderRadius: "8px",
                      border: "1px solid #e2e8f0",
                      marginBottom: "12px",
                    }}
                  />
                  {pwError && (
                    <div
                      style={{
                        fontSize: "13px",
                        color: "#e74c3c",
                        textAlign: "center",
                        marginBottom: "12px",
                      }}
                    >
                      {pwError}
                    </div>
                  )}
                  <button
                    className="apply-btn"
                    onClick={handlePwChange}
                    disabled={isPwLoading}
                  >
                    {isPwLoading ? "변경 중..." : "비밀번호 변경 완료"}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
