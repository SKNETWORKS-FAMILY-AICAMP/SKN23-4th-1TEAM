import { axiosClient } from "../../api/axiosClient";
import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { useInferStore } from "../../store/inferStore";
import { inferApi } from "../../api/inferApi";
import { extractTextFromFile } from "../../utils/pdfParser";
import { MessageSquare, Mic, FileText, Edit3, X, Loader2 } from "lucide-react";
import "./InterviewSetupModal.scss";

interface Props {
  onClose: () => void;
}

const normalizeQuestion = (text: string) =>
  text
    .toLowerCase()
    .replace(/\*\*/g, "")
    .replace(/\b(그럼|이번에는|혹시|좀 더|조금 더|자세히|구체적으로)\b/gu, " ")
    .replace(/\b(말씀해 주시겠어요|말씀해주시겠어요|설명해 주시겠어요|설명해주시겠어요|말씀해 주세요|설명해 주세요)\b/gu, " ")
    .replace(/기술들/g, "기술")
    .replace(/\s+/g, " ")
    .replace(/[^\p{L}\p{N}\s]/gu, "")
    .trim();

const isDuplicateQuestion = (source: string, candidate: string) => {
  const a = normalizeQuestion(source);
  const b = normalizeQuestion(candidate);

  if (!a || !b) return false;
  if (a === b) return true;
  if (a.includes(b) || b.includes(a)) return true;

  const aTokens = new Set(a.split(" ").filter(Boolean));
  const bTokens = new Set(b.split(" ").filter(Boolean));
  const smallerSize = Math.min(aTokens.size, bTokens.size);
  if (smallerSize === 0) return false;

  let overlap = 0;
  aTokens.forEach((token) => {
    if (bTokens.has(token)) overlap += 1;
  });

  return overlap / smallerSize >= 0.6;
};

const buildFallbackTechQuestions = (jobRole: string, count: number) => {
  const templates = [
    `${jobRole}로서 가장 자신 있는 프레임워크나 라이브러리를 하나 골라, 선택 이유와 실무 적용 사례를 설명해주세요.`,
    `${jobRole} 업무에서 성능 병목을 직접 해결한 경험이 있다면 원인 분석과 개선 방법을 설명해주세요.`,
    `${jobRole} 업무에서 데이터베이스 설계나 쿼리 최적화를 수행한 사례를 설명해주세요.`,
    `${jobRole} 업무에서 비동기 처리나 백그라운드 작업을 설계한 경험이 있다면 구조와 트레이드오프를 설명해주세요.`,
    `${jobRole} 업무에서 운영 장애나 예외 상황을 해결했던 경험을 기술적으로 설명해주세요.`,
    `${jobRole} 업무에서 테스트 자동화나 코드 품질 관리를 위해 적용한 방법을 설명해주세요.`,
  ];

  return Array.from({ length: count }, (_, index) => ({
    question: templates[index % templates.length],
  }));
};

export const InterviewSetupModal = ({ onClose }: Props) => {
  const { user } = useAuthStore();
  const setInferSettings = useInferStore((state) => state.setInferSettings);
  const navigate = useNavigate();

  const fileInputRef = useRef<HTMLInputElement>(null);

  const [method, setMethod] = useState<"text" | "voice">("text");
  const [persona, setPersona] = useState("깐깐한 기술팀장");
  const [jobRole, setJobRole] = useState("Python 백엔드 개발자");
  const [difficulty, setDifficulty] = useState("중");
  const [questionCount, setQuestionCount] = useState(5);

  const [resumeType, setResumeType] = useState<"file" | "direct">("file");
  const [experienceText, setExperienceText] = useState("");

  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [showConfirmClose, setShowConfirmClose] = useState(false);

  const isPro = user?.tier === "premium" || user?.role === "admin";

  const handleProSelect = (setter: any, value: string) => {
    if (!isPro) {
      alert(
        "PRO 등급 전용 기능입니다.\n(※ 프로젝트 시연을 위해 선택을 허용합니다)",
      );
    }
    setter(value);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleStart = async () => {
    const isResumeProvided =
      resumeType === "file"
        ? selectedFile !== null
        : experienceText.trim() !== "";

    if (!isResumeProvided) return;

    setIsUploading(true);
    let finalResumeText = experienceText;
    const userId = user?.id ? String(user.id) : "guest";

    try {
      if (resumeType === "file" && selectedFile) {
        try {
          const extracted = await extractTextFromFile(selectedFile);
          if (!extracted) throw new Error("추출된 텍스트 없음");
          finalResumeText = extracted;
        } catch (e) {
          console.error("PDF 추출 실패:", e);
          alert("PDF 텍스트 추출에 실패했습니다. PDF 파일이나 TXT 파일로 다시 시도해 주세요.");
          setIsUploading(false);
          return;
        }

        try {
          await inferApi.ingestResume(selectedFile, userId);
        } catch (e) {
          console.error("서버 전송 실패:", e);
          alert(
            "백엔드 서버로 이력서를 전송하는데 실패했습니다. 서버 상태를 확인해주세요.",
          );
          setIsUploading(false);
          return;
        }
      } else if (resumeType === "direct" && experienceText.trim()) {
        try {
          await inferApi.storeDirectTextRAG(experienceText, userId);
          finalResumeText = experienceText.trim();
        } catch (e) {
          console.error("직접 입력 전송 실패:", e);
          alert("백엔드 서버 연동에 실패했습니다.");
          setIsUploading(false);
          return;
        }
      }

      const fixedFirstQ = { question: "간단하게 자기소개를 부탁드립니다." };
      const remainCount = questionCount - 1;
      const resumeCount = finalResumeText ? Math.floor(remainCount / 2) : 0;
      const techCount = remainCount - resumeCount;

      let resumeQs: string[] = [];
      let techQs: string[] = [];
      const techFetchCount = techCount > 0 ? Math.max(techCount * 3, techCount + 2) : 0;

      if (finalResumeText) {
        try {
          const [analyzeRes, poolRes] = await Promise.all([
            inferApi.analyzeResume(finalResumeText, jobRole, resumeCount),
            inferApi.getQuestionPool(jobRole, difficulty, techFetchCount),
          ]);

          resumeQs = (analyzeRes.data?.expected_questions || []).slice(
            0,
            resumeCount,
          );
          techQs = poolRes.items?.map((item: any) => item.question) || [];
        } catch (e) {
          console.error("질문 배분 및 추출 실패:", e);
        }
      } else {
        try {
          const poolRes = await inferApi.getQuestionPool(
            jobRole,
            difficulty,
            Math.max(remainCount * 3, remainCount + 2),
          );
          techQs = poolRes.items?.map((item: any) => item.question) || [];
        } catch (e) {
          console.error("DB 기술 질문 호출 실패:", e);
        }
      }

      techQs = techQs.slice(0, techCount);

      const dedupedResumeQs = resumeQs.filter((question, index, array) => {
        return !array.slice(0, index).some((prev) => isDuplicateQuestion(prev, question));
      });
      const dedupedTechQs = techQs.filter((question, index, array) => {
        return !array.slice(0, index).some((prev) => isDuplicateQuestion(prev, question));
      });

      let mixedQuestions: { question: string }[] = [];
      const usedQuestions = [fixedFirstQ.question];
      const maxLength = Math.max(dedupedResumeQs.length, dedupedTechQs.length);

      for (let i = 0; i < maxLength; i++) {
        if (dedupedResumeQs[i]) {
          const resumeQuestion = dedupedResumeQs[i];
          const isDuplicate = usedQuestions.some((prev) =>
            isDuplicateQuestion(prev, resumeQuestion),
          );
          if (!isDuplicate) {
            mixedQuestions.push({ question: resumeQuestion });
            usedQuestions.push(resumeQuestion);
          }
        }
        if (dedupedTechQs[i]) {
          const techQuestion = dedupedTechQs[i];
          const isDuplicate = usedQuestions.some((prev) =>
            isDuplicateQuestion(prev, techQuestion),
          );
          if (!isDuplicate) {
            mixedQuestions.push({ question: techQuestion });
            usedQuestions.push(techQuestion);
          }
        }
      }

      let finalQuestions = [fixedFirstQ, ...mixedQuestions].slice(
        0,
        questionCount,
      );

      if (finalQuestions.length < questionCount) {
        const shortfall = questionCount - finalQuestions.length;
        const fallbackTechQuestions = buildFallbackTechQuestions(
          jobRole,
          shortfall * 2,
        );

        for (const fallbackQuestion of fallbackTechQuestions) {
          const isDuplicate = finalQuestions.some((existing) =>
            isDuplicateQuestion(existing.question, fallbackQuestion.question),
          );
          if (!isDuplicate) {
            finalQuestions.push(fallbackQuestion);
          }
          if (finalQuestions.length >= questionCount) {
            break;
          }
        }
      }

      try {
        const sessionResponse = await axiosClient.post("/api/infer/start", {
          job_role: jobRole,
          difficulty: difficulty,
          persona: persona,
          resume_used: isResumeProvided,
        });

        localStorage.setItem(
          "current_session_id",
          sessionResponse.data.session_id,
        );
      } catch (e) {
        console.error("면접 세션 생성 실패:", e);
        alert("서버와 연결하여 면접을 준비하는데 실패했습니다.");
        setIsUploading(false);
        return;
      }

      setInferSettings(
        jobRole,
        difficulty,
        {
          method,
          persona,
          questionCount,
          resumeType,
          experienceText: finalResumeText,
          questions: finalQuestions,
        },
        false,
      );

      onClose();
      navigate("/interview", { state: { method } });
    } catch (error) {
      console.error("알 수 없는 에러:", error);
      alert("처리 중 예상치 못한 오류가 발생했습니다.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleCloseClick = () => {
    setShowConfirmClose(true);
  };

  const confirmClose = () => {
    setShowConfirmClose(false);
    onClose();
    navigate("/");
  };

  const cancelClose = () => {
    setShowConfirmClose(false);
  };

  const isResumeProvided =
    resumeType === "file"
      ? selectedFile !== null
      : experienceText.trim() !== "";

  const isFormValid = Boolean(jobRole && difficulty && isResumeProvided);

  return (
    <>
      <div className="modal-overlay">
        <div className="setup-modal">
          <button className="close-btn" onClick={handleCloseClick}>
            <X size={24} />
          </button>

          <div className="modal-header">
            <h2>AI 모의면접 환경 설정</h2>
            <p>
              지원자님의 역량을 최대한 발휘할 수 있도록 면접 환경을
              설정해주세요.
            </p>
          </div>

          <div className="settings-grid">
            <div className="setting-section">
              <label className="section-label">
                <MessageSquare size={16} /> 진행 방식
              </label>
              <div className="btn-group">
                <button
                  className={`select-btn ${method === "text" ? "selected" : ""}`}
                  onClick={() => setMethod("text")}
                >
                  텍스트 면접
                </button>
                <button
                  className={`select-btn ${method === "voice" ? "selected" : ""}`}
                  onClick={() => setMethod("voice")}
                >
                  음성 면접
                </button>
              </div>
            </div>

            <div className="setting-section">
              <label className="section-label">
                <Mic size={16} /> 면접관 스타일
              </label>
              <div className="btn-group wrap">
                <button
                  className={`select-btn ${persona === "깐깐한 기술팀장" ? "selected" : ""}`}
                  onClick={() => setPersona("깐깐한 기술팀장")}
                >
                  깐깐한 기술팀장
                </button>
                <button
                  className={`select-btn ${persona === "부드러운 인사담당자" ? "selected" : ""}`}
                  onClick={() => setPersona("부드러운 인사담당자")}
                >
                  부드러운 <br></br>인사담당자
                </button>
                <button
                  className={`select-btn pro-btn ${persona === "스타트업 CTO" ? "selected" : ""}`}
                  onClick={() => handleProSelect(setPersona, "스타트업 CTO")}
                >
                  스타트업 CTO <span className="pro-badge">PRO</span>
                </button>
              </div>
            </div>
          </div>

          <div className="setting-section full-width">
            <label className="section-label">
              <Edit3 size={16} /> 세부 면접 설정
            </label>
            <div className="details-grid">
              <div className="input-field">
                <span>지원 직무</span>
                <select
                  value={jobRole}
                  onChange={(e) => setJobRole(e.target.value)}
                >
                  <option value="">직무를 선택해주세요</option>
                  <option value="Python 백엔드 개발자">
                    Python 백엔드 개발자
                  </option>
                  <option value="Java 백엔드 개발자">Java 백엔드 개발자</option>
                  <option value="AI/ML 엔지니어">AI/ML 엔지니어</option>
                  <option value="프론트엔드 개발자">프론트엔드 개발자</option>
                  <option value="데이터 사이언티스트">데이터 사이언티스트</option>
                  <option value="데이터 분석가">데이터 분석가</option>
                  <option value="데이터 엔지니어">데이터 엔지니어</option>
                </select>
              </div>
              <div className="input-field">
                <span>난이도</span>
                <select
                  value={difficulty}
                  onChange={(e) => {
                    if (e.target.value === "상")
                      handleProSelect(setDifficulty, "상");
                    else setDifficulty(e.target.value);
                  }}
                >
                  <option value="">난이도 선택</option>
                  <option value="하">하</option>
                  <option value="중">중</option>
                  <option value="상">상 (PRO)</option>
                </select>
              </div>
              <div className="slider-field">
                <div className="slider-header">
                  <span>질문 수</span>
                  <span className="count-badge">{questionCount}개</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={questionCount}
                  onChange={(e) => setQuestionCount(Number(e.target.value))}
                />
              </div>
            </div>
          </div>

          <div className="setting-section full-width resume-section">
            <label className="section-label">
              <FileText size={16} /> 이력서 및 경험 연동
            </label>
            <div className="resume-tabs">
              <button
                className={`resume-tab ${resumeType === "file" ? "active" : ""}`}
                onClick={() => setResumeType("file")}
              >
                이력서 파일 첨부
              </button>
              <button
                className={`resume-tab ${resumeType === "direct" ? "active" : ""}`}
                onClick={() => setResumeType("direct")}
              >
                직접 입력
              </button>
            </div>
            <div className="resume-content">
              {resumeType === "direct" ? (
                <textarea
                  placeholder="어필하고 싶은 기술 스택이나 프로젝트 경험을 간략히 적어주세요."
                  value={experienceText}
                  onChange={(e) => setExperienceText(e.target.value)}
                />
              ) : (
                <div
                  className={`file-dropzone ${selectedFile ? "has-file" : ""}`}
                  onClick={() => {
                    if (!selectedFile) fileInputRef.current?.click();
                  }}
                >
                  <input
                    type="file"
                    accept=".pdf,.txt,.doc,.docx"
                    ref={fileInputRef}
                    style={{ display: "none" }}
                    onChange={handleFileChange}
                  />

                  {selectedFile ? (
                    <div className="selected-file-view">
                      <FileText size={24} color="#0176f7" />
                      <span className="file-name">{selectedFile.name}</span>
                      <button
                        className="remove-file-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedFile(null);
                          if (fileInputRef.current)
                            fileInputRef.current.value = "";
                        }}
                      >
                        <X size={16} />
                      </button>
                    </div>
                  ) : (
                    <>
                      <FileText size={24} color="#999" />
                      <span>PDF, TXT 파일을 클릭하여 업로드하세요.</span>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          <button
            className="submit-btn"
            onClick={handleStart}
            disabled={!isFormValid || isUploading}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
            }}
          >
            {isUploading ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                이력서 기반 맞춤형 질문 생성 중...
              </>
            ) : isFormValid ? (
              "설정 완료 후 면접 시작"
            ) : (
              "이력서 첨부 또는 텍스트 입력을 완료해주세요"
            )}
          </button>
        </div>
      </div>

      {showConfirmClose && (
        <div className="confirm-close-overlay">
          <div className="confirm-close-modal">
            <h3>면접 설정 종료</h3>
            <p>
              설정 중인 내용이 저장되지 않습니다.
              <br />
              정말 홈으로 돌아가시겠습니까?
            </p>
            <div className="confirm-actions">
              <button className="cancel-btn" onClick={cancelClose}>
                계속 설정하기
              </button>
              <button className="confirm-btn" onClick={confirmClose}>
                종료하기
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
