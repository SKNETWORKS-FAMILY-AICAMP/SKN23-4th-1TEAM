import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import * as pdfjsLib from "pdfjs-dist";
import html2canvas from "html2canvas"; // PDF 캡처용 라이브러리 추가
import jsPDF from "jspdf"; // PDF 생성용 라이브러리 추가
import { Header } from "../components/common/Header";
import { CustomAlert } from "../components/common/CustomAlert";
import { useAuthStore } from "../store/authStore";
import { resumeApi } from "../api/resumeApi";
import type { ResumeItem } from "../api/resumeApi";
import { useInferStore } from "../store/inferStore";
import { ROUTES } from "../constants/routes";
import "./ResumePage.scss";
import { GuideChatbot } from "../components/chat/GuideChatbot";

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.mjs",
  import.meta.url,
).toString();

const JOB_ROLES = [
  "Python 백엔드 개발자",
  "Java 백엔드 개발자",
  "프론트엔드 개발자",
  "AI/ML 엔지니어",
  "데이터 사이언티스트",
  "데이터 분석가",
  "데이터 엔지니어",
];

export const ResumePage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { setInferSettings } = useInferStore();

  const [resumes, setResumes] = useState<ResumeItem[]>([]);
  const [selectedResume, setSelectedResume] = useState<ResumeItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [pendingDeleteResumeId, setPendingDeleteResumeId] = useState<
    number | null
  >(null);

  const [selectedRole, setSelectedRole] = useState(JOB_ROLES[0]);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const dashboardRef = useRef<HTMLDivElement>(null); // PDF 저장을 위한 Ref 추가

  const fetchResumes = async () => {
    if (!user?.id) return;
    try {
      setLoading(true);
      const data = await resumeApi.listResumes(Number(user.id));
      setResumes(data.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResumes();
  }, [user]);

  const handleDelete = async (resumeId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    await resumeApi.deleteResume(resumeId);
    fetchResumes();
  };

  const extractText = async (file: File): Promise<string> => {
    if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
      const arrayBuffer = await file.arrayBuffer();
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
      let fullText = "";

      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        const pageText = textContent.items
          .map((item: any) => item.str)
          .join(" ");
        fullText += pageText + "\n";
      }
      return fullText;
    }

    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve((e.target?.result as string) || "");
      reader.readAsText(file, "utf-8");
    });
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError("이력서 파일을 업로드해주세요.");
      return;
    }
    if (!user?.id) return;

    setUploading(true);
    setUploadError("");
    try {
      const text = await extractText(uploadFile);
      if (!text.trim()) {
        setUploadError(
          "텍스트를 추출할 수 없습니다. 다른 형식의 파일을 사용해주세요.",
        );
        return;
      }
      await resumeApi.createResume({
        user_id: Number(user.id),
        title: uploadFile.name,
        job_role: selectedRole,
        resume_text: text,
      });
      setShowModal(false);
      setUploadFile(null);
      fetchResumes();
    } catch {
      setUploadError("분석 중 오류가 발생했습니다.");
    } finally {
      setUploading(false);
    }
  };

  const handleStartInterview = () => {
    if (!selectedResume) return;

    setInferSettings(
      selectedResume.job_role,
      "중",
      {
        method: "text",
        persona: "기본 면접관",
        questionCount: 5,
        resumeType: "file",
        experienceText: selectedResume.resume_text || "",
        questions: [],
      },
      true,
      selectedResume.id,
      selectedResume.title,
    );

    navigate(ROUTES.INTERVIEW);
  };

  // PDF 다운로드 핸들러 함수
  const handleDownloadPdf = async () => {
    if (!dashboardRef.current || !selectedResume) return;

    try {
      const canvas = await html2canvas(dashboardRef.current, {
        scale: 2,
        useCORS: true,
      });
      const imgData = canvas.toDataURL("image/png");

      const pdf = new jsPDF("p", "mm", "a4");
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();

      const imgHeight = (canvas.height * pdfWidth) / canvas.width;

      let heightLeft = imgHeight;
      let position = 0;

      pdf.addImage(imgData, "PNG", 0, position, pdfWidth, imgHeight);
      heightLeft -= pdfHeight;

      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, "PNG", 0, position, pdfWidth, imgHeight);
        heightLeft -= pdfHeight;
      }

      pdf.save(
        `이력서_분석_대시보드_${selectedResume.title.replace(/\.[^/.]+$/, "")}.pdf`,
      );
    } catch (error) {
      console.error("PDF 생성 실패:", error);
      alert("PDF 다운로드 중 오류가 발생했습니다.");
    }
  };

  const formatDate = (ds: string) =>
    ds ? ds.substring(0, 10).replace(/-/g, ".") : "";

  const searchKeyword = searchTerm.trim().toLowerCase();
  const filteredResumes = resumes.filter((r) => {
    if (!searchKeyword) return true;
    const title = (r.title || "").toLowerCase();
    const role = (r.job_role || "").toLowerCase();
    return title.includes(searchKeyword) || role.includes(searchKeyword);
  });

  if (selectedResume) {
    const data = selectedResume.analysis_result || {};
    const keywords = data.keywords || [];
    const matchRate = data.match_rate || 0;
    const matchFeedback = data.match_feedback || "분석 코멘트가 없습니다.";
    const questions = data.expected_questions || [];

    return (
      <div className="resume-page-layout">
        <Header />
        <main className="resume-main">
          {/* 상단 네비게이션 영역에 PDF 저장 버튼 추가 */}
          <div
            className="dashboard-nav"
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <button
              className="back-btn"
              onClick={() => setSelectedResume(null)}
            >
              이전으로 돌아가기
            </button>
            <button
              onClick={handleDownloadPdf}
              style={{
                padding: "8px 16px",
                backgroundColor: "#2563eb",
                color: "white",
                border: "none",
                borderRadius: "8px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              PDF 저장
            </button>
          </div>

          {/* PDF로 캡처할 영역을 dashboardRef로 감싸고 백그라운드 지정 */}
          <div
            ref={dashboardRef}
            style={{
              backgroundColor: "#f8fafc",
              padding: "20px",
              borderRadius: "12px",
            }}
          >
            <div className="page-header">
              <h1 className="hero-title">이력서 분석 대시보드</h1>
              <p className="hero-subtitle">
                <span className="highlight-text">{selectedResume.title}</span>{" "}
                파일의{" "}
                <span className="highlight-text">
                  {selectedResume.job_role}
                </span>{" "}
                직무 적합도 분석 결과입니다.
              </p>
            </div>

            <div className="dashboard-grid">
              <div className="dashboard-col">
                <div className="info-panel">
                  <h3 className="panel-header">추출된 기술 스택</h3>
                  <div className="badge-container">
                    {keywords.length > 0 ? (
                      keywords.map((k, i) => (
                        <span key={i} className="tech-badge">
                          {k}
                        </span>
                      ))
                    ) : (
                      <span className="empty-text">
                        기술 스택 정보가 없습니다.
                      </span>
                    )}
                  </div>
                </div>

                <div className="info-panel">
                  <h3 className="panel-header">직무 매칭 분석</h3>
                  <div className="match-header">
                    <span className="match-label">AI 종합 스코어</span>
                    <span className="match-score">{matchRate}%</span>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{ width: `${matchRate}%` }}
                    />
                  </div>
                  <div className="match-feedback">
                    <strong>상세 코멘트</strong>
                    <p>{matchFeedback}</p>
                  </div>
                </div>
              </div>

              <div className="dashboard-col">
                <div className="info-panel highlight-panel">
                  <h3 className="panel-header">예상 압박 면접 질문</h3>
                  <div className="questions-list">
                    {questions.length > 0 ? (
                      questions.map((q, i) => (
                        <div key={i} className="q-box">
                          <span className="q-num">Q{i + 1}</span>
                          <p className="q-text">{q}</p>
                        </div>
                      ))
                    ) : (
                      <span className="empty-text">
                        질문 데이터를 생성할 수 없습니다.
                      </span>
                    )}
                  </div>
                </div>

                <button
                  className="primary-action-btn"
                  onClick={handleStartInterview}
                >
                  해당 이력서로 모의면접 시작
                </button>

                <details className="data-expander">
                  <summary>원본 텍스트 데이터 확인</summary>
                  <textarea
                    className="resume-text-preview"
                    value={selectedResume.resume_text}
                    readOnly
                    rows={8}
                  />
                </details>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="resume-page-layout">
      <Header />
      <main className="resume-main">
        <div className="page-header">
          <h1 className="hero-title">이력서 보관함</h1>
          <p className="hero-subtitle">
            분석된 이력서를 관리하고 모의면접을 진행하세요.
          </p>
        </div>

        <div className="toolbar-section">
          <input
            type="text"
            className="search-input"
            placeholder="이력서 파일명 또는 직무로 검색..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button
            className="primary-action-btn"
            onClick={() => setShowModal(true)}
          >
            새 이력서 등록
          </button>
        </div>

        {loading ? (
          <div className="loading-state">데이터를 동기화 중입니다...</div>
        ) : (
          <div className="list-container">
            {filteredResumes.length === 0 ? (
              <div className="empty-state">조건에 맞는 이력서가 없습니다.</div>
            ) : (
              filteredResumes.map((r) => (
                <div
                  key={r.id}
                  className="list-item"
                  onClick={() => setSelectedResume(r)}
                >
                  <div className="item-info">
                    <span className="job-badge">{r.job_role}</span>
                    <h3 className="item-title" title={r.title}>
                      {r.title}
                    </h3>
                  </div>

                  <div className="item-meta">
                    <div className="meta-group">
                      <span className="meta-label">등록일</span>
                      <span className="meta-value">
                        {formatDate(r.created_at)}
                      </span>
                    </div>
                    <div className="meta-group">
                      <span className="meta-label">적합도</span>
                      <span className="meta-value highlight">
                        {r.analysis_result?.match_rate ?? 0}%
                      </span>
                    </div>
                  </div>

                  <div className="item-actions">
                    <button
                      className="btn-view"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedResume(r);
                      }}
                    >
                      결과 보기
                    </button>
                    <button
                      className="btn-delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        setPendingDeleteResumeId(r.id);
                      }}
                    >
                      삭제
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </main>
      <GuideChatbot />
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-container" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>새 이력서 분석 등록</h2>
              <button className="btn-close" onClick={() => setShowModal(false)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="modal-body">
              <div className="form-group">
                <label>지원 예정 직무</label>
                <select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                  className="input-field"
                >
                  {JOB_ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>이력서 원본 파일</label>
                <div
                  className="file-drop-area"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    style={{ display: "none" }}
                    accept=".pdf,.txt,.docx,.doc"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  />
                  {uploadFile ? (
                    <span className="file-name selected">
                      {uploadFile.name}
                    </span>
                  ) : (
                    <span className="file-name">
                      여기를 클릭하여 파일을 선택하세요 (PDF, TXT)
                    </span>
                  )}
                </div>
              </div>

              {uploadError && (
                <div className="error-message">{uploadError}</div>
              )}

              <button
                className="primary-action-btn full-width"
                type="submit"
                disabled={uploading}
              >
                {uploading ? "분석 처리 중..." : "등록 및 분석 시작"}
              </button>
            </form>
          </div>
        </div>
      )}

      <CustomAlert
        open={pendingDeleteResumeId !== null}
        title="이력서를 삭제하시겠습니까?"
        message="선택하신 이력서가 삭제됩니다."
        confirmText="삭제하기"
        cancelText="취소"
        onCancel={() => setPendingDeleteResumeId(null)}
        onConfirm={async () => {
          if (pendingDeleteResumeId === null) return;
          const resumeId = pendingDeleteResumeId;
          setPendingDeleteResumeId(null);
          await handleDelete(resumeId, {
            stopPropagation: () => undefined,
          } as React.MouseEvent);
        }}
      />
    </div>
  );
};
