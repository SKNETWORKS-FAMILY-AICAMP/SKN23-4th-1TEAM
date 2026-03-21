import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import { useInferStore } from "../../store/inferStore";
import { inferApi } from "../../api/inferApi";
import { Download, List, RotateCcw, ChevronDown } from "lucide-react";
import "./InterviewReportModal.scss";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  score?: number;
}

interface Props {
  messages: ChatMessage[];
  onRestart: () => void;
}

export const InterviewReportModal = ({ messages, onRestart }: Props) => {
  const { jobRole, difficulty, experienceText } = useInferStore();
  const navigate = useNavigate();

  const [evaluation, setEvaluation] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadingText, setLoadingText] = useState(
    "AI가 면접 내용을 분석 중입니다...",
  );
  const [openSections, setOpenSections] = useState<Record<number, boolean>>({});

  const pdfRef = useRef<HTMLDivElement>(null);

  const userMessages = messages.filter(
    (m) => m.role === "user" && m.score !== undefined,
  );
  const avgScore =
    userMessages.length > 0
      ? userMessages.reduce((acc, m) => acc + (m.score || 0), 0) /
        userMessages.length
      : 0;
  const totalScore = Math.round((avgScore / 10) * 100);

  const getScoreColor = (score: number) => {
    if (score >= 80) return "#10b981";
    if (score >= 60) return "#f59e0b";
    return "#ef4444";
  };
  const scoreColor = getScoreColor(totalScore);

  useEffect(() => {
    if (!isLoading) return;
    const texts = [
      "AI가 면접 내용을 분석 중입니다...",
      "답변의 전문성과 논리력을 평가하고 있습니다...",
      "맞춤형 개선 피드백을 작성하는 중입니다...",
    ];
    let i = 0;
    const interval = setInterval(() => {
      i = (i + 1) % texts.length;
      setLoadingText(texts[i]);
    }, 2500);
    return () => clearInterval(interval);
  }, [isLoading]);

  useEffect(() => {
    const fetchEvaluation = async () => {
      try {
        const res = await inferApi.getEvaluationReport({
          messages: messages,
          job_role: jobRole || "기본 직무",
          difficulty: difficulty || "중",
          resume_text: experienceText || null,
        });

        let rawEval = res.evaluation || "평가 생성 실패";
        rawEval = rawEval.replace(
          /\*\*[\d\.]+\s*\/\s*100점\*\*/g,
          `**${totalScore} / 100점**`,
        );

        setEvaluation(rawEval);
        setOpenSections({ 0: true, 1: true });
      } catch (error) {
        console.error(error);
        setEvaluation("서버 통신 오류로 평가 리포트를 불러오지 못했습니다.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchEvaluation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const parseMarkdownIntoSections = (markdown: string) => {
    if (!markdown) return [];

    const sections: { title: string; content: string }[] = [];
    let inCodeBlock = false;
    let currentTitle = "면접 총평";
    let currentContent = "";

    const lines = markdown.split("\n");

    for (const line of lines) {
      if (line.trim().startsWith("```")) {
        inCodeBlock = !inCodeBlock;
      }

      const headingMatch = line.match(/^#{1,3}\s+(.+)$/);

      if (!inCodeBlock && headingMatch) {
        if (currentContent.trim()) {
          sections.push({
            title: currentTitle,
            content: currentContent.trim(),
          });
        }
        currentTitle = headingMatch[1].replace(/\*\*/g, "").trim();
        currentContent = "";
      } else {
        currentContent += line + "\n";
      }
    }

    if (currentContent.trim()) {
      sections.push({ title: currentTitle, content: currentContent.trim() });
    }

    return sections;
  };

  const parsedSections = parseMarkdownIntoSections(evaluation || "");

  const toggleSection = (index: number) => {
    setOpenSections((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  const handleDownloadTxt = () => {
    if (!evaluation) return;
    const element = document.createElement("a");
    const file = new Blob([evaluation], { type: "text/plain;charset=utf-8" });
    element.href = URL.createObjectURL(file);
    element.download = `AI면접_결과리포트_${jobRole || "기본직무"}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const handleDownloadPdf = async () => {
    if (!pdfRef.current || !evaluation) return;

    try {
      const allOpen: Record<number, boolean> = {};
      parsedSections.forEach((_, idx) => {
        allOpen[idx] = true;
      });
      setOpenSections(allOpen);

      await new Promise((resolve) => setTimeout(resolve, 300));

      const canvas = await html2canvas(pdfRef.current, { scale: 2 });
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

      pdf.save(`AI면접_결과리포트_${jobRole || "기본직무"}.pdf`);
    } catch (error) {
      console.error("PDF 생성 실패:", error);
      alert("PDF 다운로드 중 오류가 발생했습니다.");
    }
  };

  const handleGoRecords = () => {
    localStorage.removeItem("current_session_id");
    navigate("/records");
  };

  return (
    <div className="report-modal-overlay">
      <div className="report-modal-content">
        <div className="modal-scroll-body">
          <div
            ref={pdfRef}
            style={{ padding: "20px", backgroundColor: "#fff" }}
          >
            <h2>면접 결과 리포트</h2>

            <div className="score-circle-container">
              <div
                className="score-circle"
                style={{ "--score-color": scoreColor } as React.CSSProperties}
              >
                <svg className="progress-ring" viewBox="0 0 160 160">
                  <circle
                    className="progress-ring__bg"
                    cx="80"
                    cy="80"
                    r="74"
                  />
                  <circle
                    className="progress-ring__progress"
                    cx="80"
                    cy="80"
                    r="74"
                    style={{ strokeDashoffset: 465 - (465 * totalScore) / 100 }}
                  />
                </svg>
                <div className="score-content">
                  <span className="score-number" style={{ color: scoreColor }}>
                    {totalScore}
                  </span>
                  <span className="score-label">/ 100</span>
                </div>
              </div>
            </div>

            {!experienceText && (
              <div className="warning-banner">
                이력서를 연동하지 않은 자율 면접이므로, 직무 매칭률 평가는
                제한될 수 있습니다.
              </div>
            )}

            <div className="evaluation-box">
              {isLoading ? (
                <div className="loading-state">
                  {/* CSS 스피너 대신 loading.gif 이미지를 출력합니다. 
                      이미지 크기 조절이 필요하면 width 값을 변경하세요. */}
                  <img
                    src="/images/common/loading.gif"
                    alt="로딩 애니메이션"
                    style={{ width: "80px", marginBottom: "16px" }}
                  />
                  <p className="loading-text animate-pulse">{loadingText}</p>
                </div>
              ) : (
                <div className="accordion-list">
                  {parsedSections.map((section, idx) => (
                    <div
                      key={idx}
                      className={`accordion-item ${openSections[idx] ? "open" : ""}`}
                    >
                      <button
                        className="accordion-header"
                        onClick={() => toggleSection(idx)}
                      >
                        <span className="title">{section.title}</span>
                        <ChevronDown className="icon" size={20} />
                      </button>
                      {openSections[idx] && (
                        <div className="accordion-body markdown-content">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {section.content}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="modal-fixed-footer">
          <div style={{ display: "flex", gap: "10px", marginBottom: "12px" }}>
            <button
              className="btn-download"
              style={{
                flex: 1,
                backgroundColor: "#f8fafc",
                color: "#475569",
                border: "1px solid #cbd5e1",
              }}
              onClick={handleDownloadTxt}
              disabled={isLoading || !evaluation}
            >
              <Download size={18} /> TXT 저장
            </button>
            <button
              className="btn-download"
              style={{ flex: 1 }}
              onClick={handleDownloadPdf}
              disabled={isLoading || !evaluation}
            >
              <Download size={18} /> PDF 저장
            </button>
          </div>

          <div className="bottom-row">
            <button className="btn-restart" onClick={onRestart}>
              <RotateCcw size={18} /> 다시 시작
            </button>
            <button className="btn-home" onClick={handleGoRecords}>
              <List size={18} /> 내 기록 보러가기
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
