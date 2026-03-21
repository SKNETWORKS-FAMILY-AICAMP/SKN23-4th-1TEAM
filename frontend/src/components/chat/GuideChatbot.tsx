import { useState, useRef, useEffect, Fragment } from "react";
import { useNavigate } from "react-router-dom";
import {
  X,
  Paperclip,
  ArrowUp,
  Database,
  Save,
  Download,
  CheckCircle,
  AlertCircle,
  Info,
  Loader2,
} from "lucide-react";
import { useInferStore } from "../../store/inferStore";
import { inferApi } from "../../api/inferApi";
import { ROUTES } from "../../constants/routes";
import { homeApi } from "../../api/homeApi";
import { useAuthStore } from "../../store/authStore";
import { resumeApi } from "../../api/resumeApi";
import { axiosClient } from "../../api/axiosClient";
import "./GuideChatbot.scss";

interface Message {
  id: string;
  type: "user" | "bot";
  content: string;
  downloadContent?: string;
  downloadFilename?: string;
  saveResumePayload?: {
    title: string;
    text: string;
  };
}

interface SavedResume {
  id: string;
  title: string;
}

type ToastType = "success" | "error" | "warning";

export const GuideChatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      type: "bot",
      content:
        "안녕하세요! AIWORK 수석 어드바이저 사자개입니다.\n\n플랫폼 사용법, 취업 트렌드, 직무 고민 등 무엇이든 물어보세요. 실시간 웹 검색으로 2026년 최신 데이터를 기반으로 답변드립니다.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [showMentionMenu, setShowMentionMenu] = useState(false);
  const [selectedDbResume, setSelectedDbResume] = useState<SavedResume | null>(
    null,
  );
  const [savedResumes, setSavedResumes] = useState<SavedResume[]>([]);

  const [confirmModalPayload, setConfirmModalPayload] = useState<{
    title: string;
    text: string;
    msgId: string;
  } | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const [savedPayloadIds, setSavedPayloadIds] = useState<Set<string>>(
    new Set(),
  );
  const [toast, setToast] = useState<{
    message: string;
    type: ToastType;
  } | null>(null);

  const { user, isAuthenticated } = useAuthStore();
  const navigate = useNavigate();
  const { setInferSettings, setResumeUsed } = useInferStore();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 2500);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const showToast = (message: string, type: ToastType) => {
    setToast({ message, type });
  };

  useEffect(() => {
    const loadResumes = async () => {
      if (!user?.id) return;
      try {
        const data = await resumeApi.listResumes(Number(user.id));
        if (data && data.items) {
          const formattedData = data.items.map((item) => ({
            id: item.id.toString(),
            title: item.title,
          }));
          setSavedResumes(formattedData);
        }
      } catch (error) {
        console.error(error);
      }
    };
    if (isOpen) loadResumes();
  }, [isOpen, user?.id]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, selectedFile, selectedDbResume]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      const allowedExtensions = ["pdf", "txt"];
      const fileExtension = file.name.split(".").pop()?.toLowerCase();

      if (!fileExtension || !allowedExtensions.includes(fileExtension)) {
        showToast(
          "지원하지 않는 형식입니다. PDF 또는 TXT 파일만 올려주세요!",
          "warning",
        );
        if (fileInputRef.current) fileInputRef.current.value = "";
        return;
      }

      setSelectedFile(file);
      setSelectedDbResume(null);
    }
  };

  const removeFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removeDbResume = () => setSelectedDbResume(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInput(value);
    const words = value.split(" ");
    const lastWord = words[words.length - 1];
    setShowMentionMenu(lastWord.startsWith("@"));
  };

  const handleSelectMention = (resume: SavedResume) => {
    setSelectedDbResume(resume);
    setSelectedFile(null);
    const words = input.split(" ");
    words.pop();
    setInput(words.join(" ").trim());
    setShowMentionMenu(false);
    inputRef.current?.focus();
  };

  const handleQuickReply = (type: string) => {
    let aiResponse = "";
    switch (type) {
      case "zero-click":
        aiResponse =
          "Zero-click 사용법은 메인화면에서 챗봇에게\n**'나 내일 파이썬 백엔드 면접인데 빡세게 준비하게 해 줘'\n라고 치면? AI가 바로 사용자님을 맞춤형 면접장으로 이동시켜줍니다.\n(만약 원하는 세팅을 하지 않으면 기본 값으로 설정됩니다.)";
        break;
      case "manual":
        aiResponse =
          "AIWORK는 맞춤형 모의면접 플랫폼입니다.\n**이력서, 직무, 면접관 스타일을 자유롭게 설정해 실전 같은 AI 면접을 경험해 보세요.";
        break;
      case "resume":
        aiResponse =
          "이력서 분석 기능은 업로드하신 PDF나 텍스트 이력서를 벡터 DB에 저장하여,\n**지원자님의 이력서를 바탕으로 한 날카로운 꼬리질문을 생성하는\nAIWORK의 핵심 기술입니다.";
        break;
      default:
        return;
    }
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), type: "bot", content: aiResponse },
    ]);
  };

  const handleSend = async () => {
    if (!input.trim() && !selectedFile && !selectedDbResume) return;

    if (!isAuthenticated) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          type: "bot",
          content:
            "채팅 기능은 로그인 후 이용할 수 있습니다.\n\n로그인 페이지로 이동할게요.",
        },
      ]);
      setTimeout(() => {
        setIsOpen(false);
        navigate(ROUTES.AUTH);
      }, 900);
      return;
    }

    let attachedText = "";
    if (selectedFile) attachedText = `\n(첨부파일: ${selectedFile.name})`;
    else if (selectedDbResume)
      attachedText = `\n(저장된 이력서: ${selectedDbResume.title})`;

    const userMessageContent = input.trim()
      ? `${input}${attachedText}`
      : attachedText.trim();
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        type: "user",
        content: userMessageContent.trim(),
      },
    ]);

    const fileToUpload = selectedFile;
    const dbResumeToUse = selectedDbResume;
    const currentInput = input.trim();

    setInput("");
    removeFile();
    removeDbResume();
    setShowMentionMenu(false);
    setIsTyping(true);

    try {
      const hasInterviewKeyword =
        currentInput.includes("면접") ||
        currentInput.includes("준비") ||
        currentInput.includes("세팅") ||
        currentInput.includes("시작");
      const wantsScoreSummary =
        (currentInput.includes("면접") || currentInput.includes("기록")) &&
        (currentInput.includes("점수") ||
          currentInput.includes("평균") ||
          currentInput.includes("누적") ||
          currentInput.includes("총점"));
      const hasReportKeyword =
        currentInput.includes("성적") ||
        currentInput.includes("기록") ||
        currentInput.includes("결과") ||
        currentInput.includes("피드백") ||
        currentInput.includes("브리핑");
      const isInterviewIntent = hasInterviewKeyword && !hasReportKeyword;

      if (wantsScoreSummary && user?.id) {
        const scoreRes = await axiosClient.get(
          `/api/infer/sessions?user_id=${user.id}`,
        );
        const sessions = scoreRes.data.items || [];
        const completedScores = sessions
          .filter(
            (session: any) =>
              session.status === "COMPLETED" && session.total_score !== null,
          )
          .map((session: any) =>
            session.total_score <= 10
              ? session.total_score * 10
              : session.total_score,
          );

        let scoreMessage = "";

        if (completedScores.length === 0) {
          scoreMessage =
            "아직 완료된 면접 기록이 없어서 누적 점수를 계산할 수 없습니다.\n\n면접을 1회 이상 완료하면 평균 점수와 누적 기록을 바로 알려드릴게요.";
        } else {
          const totalScore = completedScores.reduce(
            (sum: number, score: number) => sum + score,
            0,
          );
          const averageScore = totalScore / completedScores.length;
          const bestScore = Math.max(...completedScores);

          scoreMessage =
            `현재 완료된 면접은 총 ${completedScores.length}회입니다.\n\n` +
            `평균 점수는 **${averageScore.toFixed(1)}점 / 100점**이고,\n` +
            `누적 합산 점수는 **${totalScore.toFixed(1)}점**입니다.\n` +
            `최고 점수는 **${bestScore.toFixed(1)}점 / 100점**입니다.`;
        }

        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            type: "bot",
            content: scoreMessage,
          },
        ]);

        setIsTyping(false);
        return;
      }

      const wantsProofread =
        currentInput.includes("첨삭") || currentInput.includes("교정");
      const wantsAnalysis =
        currentInput.includes("분석") ||
        currentInput.includes("평가") ||
        (!wantsProofread &&
          !isInterviewIntent &&
          (fileToUpload || dbResumeToUse));

      if (
        (fileToUpload || dbResumeToUse) &&
        wantsAnalysis &&
        !isInterviewIntent
      ) {
        const loadingId = Date.now().toString() + "_loading";
        let loadingText = "스마트 이력서 분석 중입니다...";

        if (wantsProofread && wantsAnalysis) {
          loadingText =
            "이력서 분석 및 첨삭을 동시에 진행 중입니다. 시간이 조금 더 걸릴 수 있습니다...";
        } else if (wantsProofread) {
          loadingText = "문서를 분석하고 첨삭을 진행 중입니다...";
        }

        setMessages((prev) => [
          ...prev,
          { id: loadingId, type: "bot", content: loadingText },
        ]);

        let finalChatMsg = "";
        let finalDownloadContent = "";
        let savePayload: any = undefined;

        if (wantsAnalysis) {
          if (fileToUpload) {
            const ingestRes = await inferApi.ingestResume(
              fileToUpload,
              `session_${Date.now()}`,
            );
            if (ingestRes.resume_text) {
              try {
                const analysisRes = await inferApi.analyzeResume(
                  ingestRes.resume_text,
                  "기본 직무",
                );
                const { keywords, match_feedback } = analysisRes.data;

                finalChatMsg += `### AI 이력서 분석 완료\n\n**강점 키워드:** ${keywords?.join(", ") || "없음"}\n\n**종합 피드백:** ${match_feedback || "분석 결과가 없습니다."}\n\n`;
                finalDownloadContent += `[AI 이력서 분석 결과]\n\n강점 키워드: ${keywords?.join(", ") || "없음"}\n\n종합 피드백: ${match_feedback || "분석 결과가 없습니다."}\n\n--------------------------------\n\n`;

                savePayload = {
                  title: fileToUpload.name,
                  text: ingestRes.resume_text,
                };
              } catch (e) {
                finalChatMsg += `### AI 이력서 분석\n\n이력서 분석 중 일부 오류가 발생했습니다.\n\n`;
              }
            }
          } else if (dbResumeToUse) {
            await new Promise((r) => setTimeout(r, 1000));
            finalChatMsg += `### AI 이력서 로드 완료\n\nDB에 저장된 [${dbResumeToUse.title}] 이력서가 성공적으로 로드되었습니다.\n\n`;
          }
        }

        if (wantsAnalysis && wantsProofread) {
          finalChatMsg += `---\n\n`;
        }

        if (wantsProofread) {
          const documentType = currentInput.includes("자소서")
            ? "cover_letter"
            : "resume";
          let feedbackContent = "";

          if (fileToUpload) {
            const response = await homeApi.proofreadFile(
              fileToUpload,
              documentType,
            );
            feedbackContent = response.feedback;
          } else if (dbResumeToUse) {
            feedbackContent = `[DB 이력서 첨삭 결과 테스트]\n${dbResumeToUse.title} 문서의 첨삭이 완료되었습니다.\n(현재 DB 문서는 가짜 데이터입니다.)`;
          }

          finalChatMsg += `### 첨삭 완료\n\n첨삭이 완료되었습니다. 결과는 아래 다운로드 버튼을 통해 확인하세요.`;
          finalDownloadContent += `[AI 이력서 첨삭 결과]\n\n${feedbackContent}`;
        }

        setMessages((prev) => prev.filter((m) => m.id !== loadingId));
        setResumeUsed(true);

        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            type: "bot",
            content: finalChatMsg.trim(),
            downloadContent: finalDownloadContent.trim() || undefined,
            downloadFilename: `AIWORK_이력서_통합리포트_${Date.now()}.txt`,
            saveResumePayload: savePayload,
          },
        ]);

        setIsTyping(false);
        return;
      }

      let finalDbResumeToUse = dbResumeToUse;

      if (isInterviewIntent && !fileToUpload && !dbResumeToUse) {
        if (savedResumes.length > 0) {
          finalDbResumeToUse = savedResumes[0];
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString() + "_auto",
              type: "bot",
              content: `(이력서를 지정하지 않으셔서, 보관함의 최신 이력서인 **[${finalDbResumeToUse!.title}]**를 바탕으로 면접을 준비할게요!)`,
            },
          ]);
        } else {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString() + "_no_resume",
              type: "bot",
              content: `(현재 보관함에 이력서가 없네요. 이번 면접은 이력서 기반 꼬리질문 없이 **[직무 및 기술 집중 면접]**으로 진행됩니다.)`,
            },
          ]);
        }
      }

      let agentMessage = currentInput;
      if (finalDbResumeToUse) {
        agentMessage += `\n(참조: 사용자가 '${finalDbResumeToUse.title}' 이력서를 선택했습니다.)`;
      } else if (fileToUpload) {
        agentMessage += `\n(참조: 사용자가 '${fileToUpload.name}' 파일을 첨부했습니다.)`;
      }

      const response = await axiosClient.post("/api/v1/agent/chat", {
        message: agentMessage,
      });
      const agentData = response.data;

      let finalBotMessage = agentData.message || "응답을 처리할 수 없습니다.";
      if (
        agentData.action === "navigate" &&
        agentData.target_page !== "interview"
      ) {
        if (finalBotMessage.includes("면접")) {
          if (
            agentData.target_page === "mypage" ||
            agentData.target_page === "my_info"
          )
            finalBotMessage = "네, 마이페이지로 이동합니다.";
          else if (agentData.target_page === "history")
            finalBotMessage = "네, 내 기록 페이지로 이동합니다.";
          else if (
            agentData.target_page === "board" ||
            agentData.target_page === "community"
          )
            finalBotMessage = "네, 커뮤니티(게시판)로 이동합니다.";
          else if (agentData.target_page === "resume")
            finalBotMessage = "네, 이력서 보관함으로 이동합니다.";
          else if (agentData.target_page === "home")
            finalBotMessage = "네, 메인 화면으로 이동합니다.";
        }
      }

      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), type: "bot", content: finalBotMessage },
      ]);

      if (agentData.action === "navigate") {
        if (agentData.target_page === "interview") {
          const params = agentData.session_params || {};

          let rType: "direct" | "file" = "direct";
          let rId: number | undefined = undefined;
          let rTitle: string | undefined = undefined;
          let rUsed = false;

          if (finalDbResumeToUse !== null) {
            rType = "file";
            rId = Number(finalDbResumeToUse.id);
            rTitle = finalDbResumeToUse.title;
            rUsed = true;
          } else if (fileToUpload !== null) {
            rType = "file";
            rTitle = fileToUpload.name;
            rUsed = true;
          }

          const parsedJobRole = params.job_role || "Python 백엔드 개발자";
          const parsedDifficulty = params.difficulty || "중";
          const parsedPersona = params.persona || "깐깐한 기술팀장";
          const parsedMethod = currentInput.includes("음성") ? "voice" : "text";

          try {
            const sessionResponse = await axiosClient.post("/api/infer/start", {
              job_role: parsedJobRole,
              difficulty: parsedDifficulty,
              persona: parsedPersona,
              resume_used: rUsed,
              resume_id: rId,
            });

            localStorage.setItem(
              "current_session_id",
              sessionResponse.data.session_id,
            );

            setInferSettings(
              parsedJobRole,
              parsedDifficulty,
              {
                method: parsedMethod,
                persona: parsedPersona,
                questionCount: 5,
                resumeType: rType,
                experienceText: "",
                questions: [],
              },
              rUsed,
              rId,
              rTitle,
            );

            setTimeout(() => {
              setIsOpen(false);
              navigate(ROUTES.INTERVIEW, { state: { resume: rUsed } });
            }, 1500);
          } catch (e) {
            showToast("면접 세션을 생성하는데 실패했습니다.", "error");
          }
        } else if (agentData.target_page === "history") {
          setTimeout(() => {
            setIsOpen(false);
            navigate("/history");
          }, 1000);
        } else if (
          agentData.target_page === "mypage" ||
          agentData.target_page === "my_info"
        ) {
          setTimeout(() => {
            setIsOpen(false);
            navigate(ROUTES.MY_INFO);
          }, 1000);
        } else if (agentData.target_page === "resume") {
          setTimeout(() => {
            setIsOpen(false);
            navigate("/resume");
          }, 1000);
        } else if (agentData.target_page === "home") {
          setTimeout(() => {
            setIsOpen(false);
            navigate("/");
          }, 1000);
        } else if (
          agentData.target_page === "board" ||
          agentData.target_page === "community"
        ) {
          setTimeout(() => {
            setIsOpen(false);
            navigate("/board");
          }, 1000);
        }
      }
    } catch (error: any) {
      setMessages((prev) => prev.filter((m) => !m.id.endsWith("_loading")));
      const errorDetail =
        error.response?.data?.detail ||
        error.message ||
        "알 수 없는 서버 오류 (500)";
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          type: "bot",
          content: `요청을 처리하는 도중 서버 오류가 발생했습니다.\n\n**백엔드 에러 내용:** \n${errorDetail}`,
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const executeSaveResume = async () => {
    if (!confirmModalPayload || isSaving) return;
    if (!user) {
      showToast("로그인이 필요합니다.", "warning");
      return;
    }

    setIsSaving(true);
    try {
      await resumeApi.createResume({
        user_id: Number(user.id),
        title: confirmModalPayload.title,
        job_role: "기본 직무",
        resume_text: confirmModalPayload.text,
      });
      showToast("성공적으로 저장되었습니다!", "success");
      setSavedPayloadIds((prev) =>
        new Set(prev).add(confirmModalPayload.msgId),
      );
      setConfirmModalPayload(null);
    } catch (error) {
      showToast("이력서 저장에 실패했습니다.", "error");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownload = (content: string, filename: string) => {
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getToastIcon = (type: ToastType) => {
    switch (type) {
      case "success":
        return <CheckCircle size={20} />;
      case "warning":
        return <Info size={20} />;
      case "error":
        return <AlertCircle size={20} />;
    }
  };

  return (
    <div className="chatbot-wrapper">
      {toast && (
        <div className={`chatbot-toast-alert ${toast.type}`}>
          {getToastIcon(toast.type)}
          <span className="toast-message">{toast.message}</span>
        </div>
      )}

      {confirmModalPayload && (
        <div className="confirm-modal-overlay">
          <div className="confirm-modal-content">
            <div className="confirm-icon">
              <Save size={32} />
            </div>
            <h3>이력서를 보관함에 저장할까요?</h3>
            <p>
              저장된 이력서는 다음 면접이나 첨삭 시<br />
              간편하게 다시 불러올 수 있습니다.
            </p>
            <div className="confirm-actions">
              <button
                className="btn-cancel"
                onClick={() => setConfirmModalPayload(null)}
                disabled={isSaving}
              >
                건너뛰기
              </button>
              <button
                className="btn-proceed"
                onClick={executeSaveResume}
                disabled={isSaving}
              >
                {isSaving ? (
                  <span
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "8px",
                    }}
                  >
                    <Loader2 size={16} className="spinner" /> 저장 중...
                  </span>
                ) : (
                  "저장하기"
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {isOpen && (
        <div className="chatbot-window">
          <div className="chat-header">
            <div className="header-info">
              <div className="bot-avatar">🦁</div>
              <div className="bot-title">
                <h3>AIWORK 가이드 봇</h3>
                <span>
                  <span className="dot"></span> 온라인 &middot; 실시간 탐색 연동
                </span>
              </div>
            </div>
            <button className="close-btn" onClick={() => setIsOpen(false)}>
              <X size={20} />
            </button>
          </div>

          <div className="chat-body">
            {messages.map((msg, index) => (
              <div key={msg.id} className={`message-row ${msg.type}`}>
                {msg.type === "bot" && <div className="msg-avatar">🦁</div>}

                <div className="message-content">
                  <div className="message-bubble">
                    {msg.content.split("\n").map((line, i) => (
                      <Fragment key={i}>
                        {line.startsWith("**") ? (
                          <strong>{line.replace(/\*\*/g, "")}</strong>
                        ) : line.startsWith("###") ? (
                          <h4 style={{ margin: "8px 0" }}>
                            {line.replace("###", "")}
                          </h4>
                        ) : line.startsWith("---") ? (
                          <hr
                            style={{
                              border: "none",
                              borderTop: "1px dashed #e2e8f0",
                              margin: "12px 0",
                            }}
                          />
                        ) : (
                          line
                        )}
                        <br />
                      </Fragment>
                    ))}

                    {(msg.downloadContent || msg.saveResumePayload) && (
                      <div className="bubble-actions-row">
                        {msg.downloadContent && (
                          <button
                            className="bubble-action-btn btn-txt"
                            onClick={() =>
                              handleDownload(
                                msg.downloadContent!,
                                msg.downloadFilename!,
                              )
                            }
                          >
                            <Download size={14} /> TXT 저장
                          </button>
                        )}
                        {msg.saveResumePayload && (
                          <button
                            className={`bubble-action-btn btn-save ${savedPayloadIds.has(msg.id) ? "saved" : ""}`}
                            onClick={() =>
                              setConfirmModalPayload({
                                ...msg.saveResumePayload!,
                                msgId: msg.id,
                              })
                            }
                            disabled={savedPayloadIds.has(msg.id)}
                          >
                            {savedPayloadIds.has(msg.id) ? (
                              <>
                                <CheckCircle size={14} /> 저장 완료
                              </>
                            ) : (
                              <>
                                <Save size={14} /> 이력서 저장
                              </>
                            )}
                          </button>
                        )}
                      </div>
                    )}

                    {index === 0 && msg.type === "bot" && (
                      <div className="quick-actions">
                        <button onClick={() => handleQuickReply("zero-click")}>
                          Zero-Click 사용법
                        </button>
                        <button onClick={() => handleQuickReply("manual")}>
                          AIWORK 사용법
                        </button>
                        <button onClick={() => handleQuickReply("resume")}>
                          이력서 분석
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="message-row bot">
                <div className="msg-avatar">🦁</div>
                <div className="message-bubble loading">
                  <div className="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-container">
            {showMentionMenu && (
              <div className="mention-menu">
                <div className="mention-header">내 이력서 불러오기</div>
                <ul className="mention-list">
                  {savedResumes.map((resume) => (
                    <li
                      key={resume.id}
                      onClick={() => handleSelectMention(resume)}
                    >
                      <div className="icon-wrapper">
                        <Database size={18} />
                      </div>
                      <span className="resume-title">{resume.title}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <input
              type="file"
              ref={fileInputRef}
              style={{ display: "none" }}
              accept=".pdf,.txt"
              onChange={handleFileSelect}
            />

            {(selectedFile || selectedDbResume) && (
              <div className="file-preview-chip">
                {selectedFile ? (
                  <Paperclip size={14} />
                ) : (
                  <Database size={14} />
                )}
                <span className="file-name">
                  {selectedFile ? selectedFile.name : selectedDbResume?.title}
                </span>
                <button
                  type="button"
                  onClick={selectedFile ? removeFile : removeDbResume}
                >
                  <X size={14} />
                </button>
              </div>
            )}

            <div className="chat-input-pill">
              <button
                type="button"
                className="clip-btn"
                onClick={() => fileInputRef.current?.click()}
                title="이력서 첨부"
              >
                <Paperclip size={20} />
              </button>

              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={handleInputChange}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder="질문을 입력하거나 @를 눌러 이력서를 불러오세요..."
                disabled={isTyping}
              />

              <button
                className={`send-btn ${input.trim() || selectedFile || selectedDbResume ? "active" : ""}`}
                onClick={handleSend}
                disabled={
                  (!input.trim() && !selectedFile && !selectedDbResume) ||
                  isTyping
                }
              >
                <ArrowUp size={18} strokeWidth={3} />
              </button>
            </div>
          </div>
        </div>
      )}

      {!isOpen && (
        <button className="chatbot-toggle" onClick={() => setIsOpen(true)}>
          <div className="toggle-avatar">🦁</div>
        </button>
      )}
    </div>
  );
};
