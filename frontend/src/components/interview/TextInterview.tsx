import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useInterviewChat } from "../../hooks/useInterviewChat";
import { InterviewReportModal } from "./InterviewReportModal";
import "./TextInterview.scss";

interface TextInterviewProps {
  onMessagesChange?: (
    messages: { role: "user" | "assistant"; content: string; score?: number }[],
  ) => void;
}

export const TextInterview = ({ onMessagesChange }: TextInterviewProps) => {
  const { messages, isLoading, isEnded, sendMessage } = useInterviewChat();
  const [inputText, setInputText] = useState("");

  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    onMessagesChange?.(messages);
  }, [messages, onMessagesChange]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 250)}px`;
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputText.trim() && !isLoading && !isEnded) {
      sendMessage(inputText);
      setInputText("");

      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  return (
    <div className="text-interview-wrapper">
      <div className="guide-banner">
        <strong>텍스트 면접 모드 가이드</strong>
        <p>
          하단의 입력창에 답변을 타이핑하여 제출해 주세요. 카메라는 사용되지
          않으며, 채팅창을 넓게 사용합니다.
        </p>
      </div>

      <div className="chat-container">
        {messages.length === 0 && (
          <div className="system-msg">면접관이 질문을 준비하고 있습니다...</div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message-row ${msg.role}`}>
            {msg.role === "assistant" && (
              <div className="ai-profile-icon">👾</div>
            )}

            <div className="message-content">
              {msg.role === "assistant" && (
                <div className="ai-name">AI 면접관</div>
              )}

              <div className={`bubble ${msg.role}`}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              </div>

              {msg.role === "user" && msg.score !== undefined && (
                <div className="score-badge">
                  AI 평가 점수: {msg.score.toFixed(1)} / 10
                </div>
              )}
            </div>
          </div>
        ))}

        {/* ✅ 수정: 로딩 상태일 때 GIF 이미지 출력 */}
        {isLoading && (
          <div className="message-row assistant">
            <div className="ai-profile-icon">👾</div>
            <div className="message-content">
              <div className="bubble assistant typing">
                <img
                  src="/images/common/loading.gif"
                  alt="답변 작성 중..."
                  className="typing-gif"
                />
                <span className="typing-text">
                  면접관이 답변을 분석 중입니다...
                </span>
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <form className="chat-input-area" onSubmit={handleSubmit}>
        <div className="input-wrapper">
          <textarea
            ref={textareaRef}
            value={inputText}
            onChange={handleInput}
            placeholder={
              isEnded ? "면접이 종료되었습니다." : "답변을 입력하세요"
            }
            disabled={isLoading || isEnded}
            rows={1}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <button
            type="submit"
            disabled={!inputText.trim() || isLoading || isEnded}
            className="btn-submit"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
            </svg>
          </button>
        </div>
      </form>

      {isEnded && (
        <InterviewReportModal
          messages={messages}
          onRestart={() => window.location.reload()}
        />
      )}
    </div>
  );
};
