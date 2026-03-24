import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import { useInferStore } from "../../store/inferStore";
import { inferApi } from "../../api/inferApi";
import { ROUTES } from "../../constants/routes";
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
    "AI媛 硫댁젒 ?댁슜??遺꾩꽍 以묒엯?덈떎...",
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
      "AI媛 硫댁젒 ?댁슜??遺꾩꽍 以묒엯?덈떎...",
      "?듬????꾨Ц?깃낵 ?쇰━?μ쓣 ?됯??섍퀬 ?덉뒿?덈떎...",
      "留욎땄??媛쒖꽑 ?쇰뱶諛깆쓣 ?묒꽦?섎뒗 以묒엯?덈떎...",
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
      if (userMessages.length === 0) {
        setEvaluation(
          [
            "# 1. 醫낇빀 ?먯닔",
            "",
            "?듬????댁슜???놁뼱 ?꾩쭅 ?됯?瑜??앹꽦?????놁뒿?덈떎.",
            "",
            "# 2. BEST ?듬?",
            "",
            "?꾩쭅 ?쒖텧???듬????놁뒿?덈떎.",
            "",
            "# 3. 蹂댁셿 ?ъ씤??,
            "",
            "吏덈Ц???듬????쒖텧?????ㅼ떆 由ы룷?몃? ?뺤씤??二쇱꽭??",
          ].join("\n"),
        );
        setOpenSections({ 0: true, 1: true, 2: true });
        setIsLoading(false);
        return;
      }

      try {
        const res = await inferApi.getEvaluationReport({
          messages: messages,
          job_role: jobRole || "湲곕낯 吏곷Т",
          difficulty: difficulty || "以?,
          resume_text: experienceText || null,
        });

        let rawEval = res.evaluation || "?됯? ?앹꽦 ?ㅽ뙣";
        rawEval = rawEval.replace(
          /\*\*[\d\.]+\s*\/\s*100??*\*/g,
          `**${totalScore} / 100??*`,
        );

        setEvaluation(rawEval);
        setOpenSections({ 0: true, 1: true });
      } catch (error) {
        console.error(error);
        setEvaluation("?쒕쾭 ?듭떊 ?ㅻ쪟濡??됯? 由ы룷?몃? 遺덈윭?ㅼ? 紐삵뻽?듬땲??");
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
    let currentTitle = "硫댁젒 珥앺룊";
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
    element.download = `AI硫댁젒_寃곌낵由ы룷??${jobRole || "湲곕낯吏곷Т"}.txt`;
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

      pdf.save(`AI硫댁젒_寃곌낵由ы룷??${jobRole || "湲곕낯吏곷Т"}.pdf`);
    } catch (error) {
      console.error("PDF ?앹꽦 ?ㅽ뙣:", error);
      alert("PDF ?ㅼ슫濡쒕뱶 以??ㅻ쪟媛 諛쒖깮?덉뒿?덈떎.");
    }
  };

  const handleGoRecords = () => {
    localStorage.removeItem("current_session_id");
    navigate(ROUTES.RECORDS);
  };

  return (
    <div className="report-modal-overlay">
      <div className="report-modal-content">
        <div className="modal-scroll-body">
          <div
            ref={pdfRef}
            style={{ padding: "20px", backgroundColor: "#fff" }}
          >
            <h2>硫댁젒 寃곌낵 由ы룷??/h2>

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
                ?대젰?쒕? ?곕룞?섏? ?딆? ?먯쑉 硫댁젒?대?濡? 吏곷Т 留ㅼ묶瑜??됯???
                ?쒗븳?????덉뒿?덈떎.
              </div>
            )}

            <div className="evaluation-box">
              {isLoading ? (
                <div className="loading-state">
                  {/* CSS ?ㅽ뵾?????loading.gif ?대?吏瑜?異쒕젰?⑸땲?? 
                      ?대?吏 ?ш린 議곗젅???꾩슂?섎㈃ width 媛믪쓣 蹂寃쏀븯?몄슂. */}
                  <img
                    src="/images/common/loading.gif"
                    alt="濡쒕뵫 ?좊땲硫붿씠??
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
                style={{ flex: 1 }}
                onClick={handleDownloadTxt}
                disabled={isLoading || !evaluation}
              >
              <Download size={18} /> TXT ???
            </button>
            <button
              className="btn-download"
              style={{ flex: 1 }}
              onClick={handleDownloadPdf}
              disabled={isLoading || !evaluation}
            >
              <Download size={18} /> PDF ???
            </button>
          </div>

          <div className="bottom-row">
            <button className="btn-restart" onClick={onRestart}>
              <RotateCcw size={18} /> ?ㅼ떆 ?쒖옉
            </button>
            <button className="btn-home" onClick={handleGoRecords}>
              <List size={18} /> 내 기록 보기
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

