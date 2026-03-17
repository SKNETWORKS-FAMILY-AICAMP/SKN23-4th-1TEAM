import React, { useState, useRef, useEffect } from 'react';
import { useInterviewChat } from '../../hooks/useInterviewChat';
import { InterviewReportModal } from './InterviewReportModal';
import './TextInterview.scss';

export const TextInterview = () => {
  const { messages, isLoading, isEnded, sendMessage } = useInterviewChat();
  const [inputText, setInputText] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputText.trim() && !isLoading && !isEnded) {
      sendMessage(inputText);
      setInputText('');
    }
  };

  return (
    <div className="text-interview-wrapper">
      <div className="guide-banner">
        <strong>텍스트 면접 모드 가이드</strong>
        <p>하단의 입력창에 답변을 타이핑하여 제출해 주세요. 카메라는 사용되지 않으며, 채팅창을 넓게 사용합니다.</p>
      </div>

      <div className="chat-container">
        {messages.length === 0 && (
          <div className="system-msg">면접관이 질문을 준비하고 있습니다...</div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`message-row ${msg.role}`}>
            {msg.role === 'assistant' && <div className="ai-profile-icon">👾</div>}
            
            <div className="message-content">
              {msg.role === 'assistant' && <div className="ai-name">AI 면접관</div>}
              
              <div className={`bubble ${msg.role}`}>
                {msg.content}
              </div>
              
              {/* 유저 점수 뱃지 */}
              {msg.role === 'user' && msg.score !== undefined && (
                <div className="score-badge">AI 평가 점수: {msg.score.toFixed(1)} / 10</div>
              )}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message-row assistant">
            <div className="ai-profile-icon">👾</div>
            <div className="message-content">
              <div className="bubble assistant typing">답변을 분석 중입니다...</div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* 둥근 형태의 채팅 입력창 */}
      <form className="chat-input-area" onSubmit={handleSubmit}>
        <div className="input-wrapper">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={isEnded ? "면접이 종료되었습니다." : "메시지를 입력하세요"}
            disabled={isLoading || isEnded}
            rows={1}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <button type="submit" disabled={!inputText.trim() || isLoading || isEnded} className="btn-submit">
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
            </svg>
          </button>
        </div>
      </form>

      {/* 면접 종료 시 결과 리포트 모달 출력 */}
      {isEnded && (
        <InterviewReportModal 
          messages={messages} 
          onRestart={() => window.location.reload()} 
        />
      )}
    </div>
  );
};