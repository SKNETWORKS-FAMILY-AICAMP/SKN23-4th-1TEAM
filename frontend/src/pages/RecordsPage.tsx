import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import { Download } from "lucide-react";
import { Header } from "../components/common/Header";
import { CustomAlert } from "../components/common/CustomAlert";
import { GuideChatbot } from "../components/chat/GuideChatbot";
import { axiosClient } from "../api/axiosClient";
import { ROUTES } from "../constants/routes";
import { useAuthStore } from "../store/authStore";
import "./RecordsPage.scss";

interface InterviewSession {
  id: number;
  job_role: string;
  difficulty: string;
  status: string;
  total_score: number | null;
  started_at: string;
}

interface InterviewDetail {
  id: number;
  turn_index: number;
  question: string;
  answer: string;
  score: number | null;
  feedback: string;
  is_followup: boolean;
}

const SessionDetailModal = ({
  sessionId,
  onClose,
}: {
  sessionId: number;
  onClose: () => void;
}) => {
  const [details, setDetails] = useState<InterviewDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const pdfRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchDetails = async () => {
      try {
        const res = await axiosClient.get(`/api/infer/sessions/${sessionId}`);
        setDetails(res.data.items || []);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    void fetchDetails();
  }, [sessionId]);

  const handleDownloadPdf = async () => {
    if (!pdfRef.current) return;

    let captureContainer: HTMLDivElement | null = null;

    try {
      // Scrollable modal content can be clipped by html2canvas. Clone the
      // printable area offscreen so the full height is rendered before capture.
      captureContainer = document.createElement("div");
      captureContainer.style.position = "fixed";
      captureContainer.style.left = "-100000px";
      captureContainer.style.top = "0";
      captureContainer.style.width = `${pdfRef.current.scrollWidth || pdfRef.current.clientWidth}px`;
      captureContainer.style.padding = "0";
      captureContainer.style.margin = "0";
      captureContainer.style.background = "#ffffff";
      captureContainer.style.zIndex = "-1";
      captureContainer.style.overflow = "visible";

      const clone = pdfRef.current.cloneNode(true) as HTMLDivElement;
      clone.style.width = "100%";
      clone.style.maxHeight = "none";
      clone.style.height = "auto";
      clone.style.overflow = "visible";

      captureContainer.appendChild(clone);
      document.body.appendChild(captureContainer);

      const canvas = await html2canvas(clone, {
        scale: 2,
        backgroundColor: "#ffffff",
        useCORS: true,
        width: clone.scrollWidth,
        height: clone.scrollHeight,
        windowWidth: clone.scrollWidth,
        windowHeight: clone.scrollHeight,
      });

      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF("p", "mm", "a4");
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfPageHeight = pdf.internal.pageSize.getHeight();
      const imgHeight = (canvas.height * pdfWidth) / canvas.width;

      let heightLeft = imgHeight;
      let position = 0;

      pdf.addImage(imgData, "PNG", 0, position, pdfWidth, imgHeight);
      heightLeft -= pdfPageHeight;

      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, "PNG", 0, position, pdfWidth, imgHeight);
        heightLeft -= pdfPageHeight;
      }

      pdf.save(`면접상세기록_세션${sessionId}.pdf`);
    } catch (error) {
      console.error("PDF 생성 실패:", error);
      alert("PDF 다운로드 중 오류가 발생했습니다.");
    } finally {
      if (captureContainer) {
        document.body.removeChild(captureContainer);
      }
    }
  };

  const scoredDetails = details.filter((d) => d.score !== null);
  const avgScore =
    scoredDetails.length > 0
      ? scoredDetails.reduce((sum, d) => sum + (d.score || 0), 0) /
        scoredDetails.length
      : 0;
  const highCount = scoredDetails.filter((d) => (d.score || 0) >= 7).length;
  const lowCount = scoredDetails.filter((d) => (d.score || 0) < 5).length;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h2>세션 #{sessionId} 상세 기록</h2>
          <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
            <button
              onClick={handleDownloadPdf}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                backgroundColor: "#2563eb",
                color: "white",
                border: "none",
                padding: "8px 14px",
                borderRadius: "6px",
                fontSize: "13px",
                fontWeight: "bold",
                cursor: "pointer",
              }}
            >
              <Download size={16} /> PDF 저장
            </button>
            <button className="btn-close" onClick={onClose}>
              &times;
            </button>
          </div>
        </div>

        {loading ? (
          <p className="modal-message">데이터를 불러오는 중입니다...</p>
        ) : details.length === 0 ? (
          <p className="modal-message empty">
            이 세션에 저장된 상세 기록이 없습니다.
          </p>
        ) : (
          <div ref={pdfRef} style={{ padding: "10px", backgroundColor: "#fff" }}>
            <div className="score-summary-box">
              <div className="summary-item">
                <div className="label">종합 점수</div>
                <div className="value">{(avgScore * 10).toFixed(1)}점</div>
              </div>
              <div className="summary-item">
                <div className="label">총 답변</div>
                <div className="value">{details.length}개</div>
              </div>
              <div className="summary-item">
                <div className="label">우수 답변</div>
                <div className="value text-green">{highCount}개</div>
              </div>
              <div className="summary-item">
                <div className="label">보완 필요</div>
                <div className="value text-red">{lowCount}개</div>
              </div>
            </div>

            <div className="detail-list">
              {details.map((d, idx) => (
                <div key={idx} className="detail-card-item">
                  {Boolean(d.is_followup) && (
                    <span className="tag-followup">꼬리질문</span>
                  )}

                  <div className="q-section">
                    <div className="q-header">
                      Q{d.turn_index + 1}. 면접관 질문
                      {d.score !== null && (
                        <span
                          className={`score ${
                            d.score >= 7 ? "green" : d.score >= 5 ? "orange" : "red"
                          }`}
                        >
                          {d.score.toFixed(1)}/10
                        </span>
                      )}
                    </div>
                    <div className="q-text">{d.question || "(질문 없음)"}</div>
                  </div>

                  <div className="a-section">
                    <div className="a-header">지원자 답변</div>
                    <div className="a-text">{d.answer || "(답변 없음)"}</div>
                  </div>

                  {d.feedback && (
                    <div className="feedback-section">
                      <div className="feedback-header">피드백</div>
                      <div className="feedback-text">{d.feedback}</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <button className="btn-close-full" onClick={onClose}>
          닫기
        </button>
      </div>
    </div>
  );
};

export const RecordsPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [records, setRecords] = useState<InterviewSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(
    null,
  );
  const [pendingDeleteSessionId, setPendingDeleteSessionId] = useState<
    number | null
  >(null);

  const fetchRecords = async () => {
    if (!user?.id) return;

    try {
      setLoading(true);
      const response = await axiosClient.get(
        `/api/infer/sessions?user_id=${user.id}`,
      );
      setRecords(response.data.items || []);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchRecords();
  }, [user]);

  const handleConfirmedDelete = async (sessionId: number) => {
    try {
      await axiosClient.delete(`/api/interview/sessions/${sessionId}`);
      alert("면접 기록을 삭제했습니다.");
      void fetchRecords();
    } catch (error: any) {
      console.error(error);
      if (error.response?.status === 401 || error.response?.status === 405) {
        alert("삭제 권한이 없거나 로그인 상태가 만료되었습니다.");
      } else {
        alert("삭제에 실패했습니다.");
      }
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, "0")}.${String(date.getDate()).padStart(2, "0")} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
  };

  const getScoreColorClass = (score: number | null) => {
    if (score === null) return "score-none";
    const scaledScore = score <= 10 ? score * 10 : score;
    if (scaledScore >= 80) return "score-high";
    if (scaledScore >= 60) return "score-medium";
    return "score-low";
  };

  return (
    <div className="records-page-layout">
      <Header />
      <main className="records-main">
        <div className="page-header flex-header">
          <div>
            <h1 className="hero-title">내 면접 기록</h1>
            <p className="hero-subtitle">
              진행 완료한 결과 확인 및 기록을 관리할 수 있습니다.
            </p>
          </div>
          <button
            className="primary-action-btn sm"
            onClick={() => navigate(ROUTES.INTERVIEW)}
          >
            새 모의면접 시작
          </button>
        </div>

        {loading ? (
          <div className="loading-state">데이터를 불러오는 중입니다...</div>
        ) : records.length === 0 ? (
          <div className="empty-state">
            <h3 className="empty-title">아직 면접 기록이 없습니다.</h3>
            <p className="empty-desc">
              모의 면접을 시작해 첫 번째 기록을 만들어보세요.
            </p>
            <button
              className="primary-action-btn"
              onClick={() => navigate(ROUTES.INTERVIEW)}
            >
              모의면접 하러 가기
            </button>
          </div>
        ) : (
          <div className="records-grid">
            {records.map((record) => (
              <div key={record.id} className="record-card">
                <div className="card-header">
                  <div className="role-info">
                    <span className="job-badge">{record.job_role}</span>
                    <span className="diff-badge">{record.difficulty}</span>
                  </div>
                  <button
                    className="btn-delete"
                    onClick={() => setPendingDeleteSessionId(record.id)}
                  >
                    삭제
                  </button>
                </div>

                <div className="card-body">
                  <div className="score-section">
                    <span className="score-label">
                      {record.status === "COMPLETED"
                        ? "종합 평가 점수"
                        : "진행 상태"}
                    </span>
                    <div className="score-value-wrapper">
                      <span
                        className={`score-value ${getScoreColorClass(record.total_score)}`}
                      >
                        {record.status === "COMPLETED" ? (
                          record.total_score !== null ? (
                            `${(
                              record.total_score <= 10
                                ? record.total_score * 10
                                : record.total_score
                            ).toFixed(1)} / 100`
                          ) : (
                            "채점 중"
                          )
                        ) : (
                          <span
                            className="status-in-progress"
                            style={{ color: "#ef4444" }}
                          >
                            중단됨
                          </span>
                        )}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="card-footer">
                  <span className="date-text">
                    일시: {formatDate(record.started_at)}
                  </span>
                  {record.status === "COMPLETED" ? (
                    <button
                      className="btn-view-detail"
                      onClick={() => setSelectedSessionId(record.id)}
                    >
                      상세 리포트 보기
                    </button>
                  ) : (
                    <span
                      style={{
                        fontSize: "13px",
                        color: "#ef4444",
                        fontWeight: "bold",
                      }}
                    >
                      미완료 면접 (삭제 권장)
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <GuideChatbot />

      {selectedSessionId !== null && (
        <SessionDetailModal
          sessionId={selectedSessionId}
          onClose={() => setSelectedSessionId(null)}
        />
      )}

      <CustomAlert
        open={pendingDeleteSessionId !== null}
        title="기록을 삭제할까요?"
        message={
          pendingDeleteSessionId !== null
            ? `세션 #${pendingDeleteSessionId} 기록은 삭제 후 복구할 수 없습니다.`
            : ""
        }
        confirmText="삭제하기"
        cancelText="취소"
        onCancel={() => setPendingDeleteSessionId(null)}
        onConfirm={async () => {
          if (pendingDeleteSessionId === null) return;
          const sessionId = pendingDeleteSessionId;
          setPendingDeleteSessionId(null);
          await handleConfirmedDelete(sessionId);
        }}
      />
    </div>
  );
};
