import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { axiosClient } from "../api/axiosClient";
import { InterviewReportModal } from "../components/interview/InterviewReportModal";
import { InterviewSetupModal } from "../components/interview/InterviewSetupModal";
import { TextInterview } from "../components/interview/TextInterview";
import { VoiceInterview } from "../components/interview/VoiceInterview";
import { useInferStore } from "../store/inferStore";
import "./Interview.scss";
import { GuideChatbot } from "../components/chat/GuideChatbot";

type ReportMessage = {
  role: "user" | "assistant";
  content: string;
  score?: number;
};

export const Interview = () => {
  const {
    jobRole,
    difficulty,
    method,
    persona,
    questionCount,
    clearInferSettings,
  } = useInferStore();
  const navigate = useNavigate();
  const location = useLocation();
  const routeMethod = location.state?.method as "text" | "voice" | undefined;
  const persistedMethod = localStorage.getItem("interview_method") as
    | "text"
    | "voice"
    | null;
  const effectiveMethod = routeMethod || method || persistedMethod;
  const hasPreparedSettings = Boolean(jobRole && difficulty && effectiveMethod);

  const [isSetupModalOpen, setIsSetupModalOpen] =
    useState(!hasPreparedSettings);
  const [showEndModal, setShowEndModal] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportMessages, setReportMessages] = useState<ReportMessage[]>([]);

  useEffect(() => {
    if (hasPreparedSettings) {
      setIsSetupModalOpen(false);
      return;
    }
    localStorage.removeItem("current_session_id");
    setIsSetupModalOpen(true);
  }, [hasPreparedSettings]);

  const confirmEndInterview = async () => {
    try {
      const sessionId = localStorage.getItem("current_session_id");

      if (sessionId) {
        try {
          await axiosClient.post("/api/infer/end", {
            session_id: Number(sessionId),
          });
        } catch (endError) {
          console.error("면접 종료 점수 저장 재시도:", endError);
          await axiosClient.put(`/api/interview/sessions/${sessionId}`, {
            status: "COMPLETED",
          });
        }
      }

      setShowEndModal(false);
      setShowReportModal(true);
    } catch (error) {
      console.error("면접 종료 처리 중 오류:", error);
      navigate("/");
    }
  };

  const handleRestart = () => {
    localStorage.removeItem("current_session_id");
    clearInferSettings();
    window.location.reload();
  };

  return (
    <div className="interview-page-container">
      <header className="unified-interview-header">
        <div className="header-left">
          <div className="ai-icon-box">👾</div>
          <div className="title-area">
            <h1>
              AI 면접관{" "}
              <span className="badge-persona">
                {persona || "깐깐한 기술 면접관"}
              </span>
            </h1>
            <p className="meta-info">
              {jobRole || "기본 직무"} · 난이도 {difficulty || "중급"} · 총{" "}
              {questionCount || 5}문항
            </p>
          </div>
        </div>
        <button
          className="btn-end-interview"
          onClick={() => setShowEndModal(true)}
        >
          면접 종료 및 저장
        </button>
      </header>

      <main className="interview-main-content">
        {!isSetupModalOpen &&
          (effectiveMethod === "voice" ? (
            <VoiceInterview onMessagesChange={setReportMessages} />
          ) : (
            <TextInterview onMessagesChange={setReportMessages} />
          ))}
      </main>
      <GuideChatbot />

      {isSetupModalOpen && (
        <InterviewSetupModal onClose={() => setIsSetupModalOpen(false)} />
      )}

      {showEndModal && (
        <div className="modal-overlay">
          <div
            className="custom-modal-content"
            style={{
              background: "white",
              padding: "30px",
              borderRadius: "16px",
              maxWidth: "400px",
            }}
          >
            <h3 style={{ marginTop: 0 }}>면접 최종 종료</h3>
            <p style={{ color: "#666", lineHeight: 1.5, marginBottom: "24px" }}>
              면접을 종료하시겠습니까?
              <br />
              최종 제출 후 결과 리포트가 표시됩니다.
            </p>
            <div
              style={{ display: "flex", flexDirection: "column", gap: "10px" }}
            >
              <button
                onClick={confirmEndInterview}
                style={{
                  padding: "12px",
                  background: "#ef4444",
                  border: "none",
                  borderRadius: "8px",
                  fontWeight: "bold",
                  cursor: "pointer",
                  color: "white",
                }}
              >
                최종 제출하고 완전 종료
              </button>
              <button
                onClick={() => setShowEndModal(false)}
                style={{
                  padding: "12px",
                  background: "transparent",
                  border: "1px solid #cbd5e1",
                  borderRadius: "8px",
                  fontWeight: "bold",
                  cursor: "pointer",
                  marginTop: "8px",
                }}
              >
                취소 (계속 진행)
              </button>
            </div>
          </div>
        </div>
      )}

      {showReportModal && (
        <InterviewReportModal
          messages={reportMessages}
          onRestart={handleRestart}
        />
      )}
    </div>
  );
};
