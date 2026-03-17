import React, { useRef, useEffect, useState } from 'react';
import { useWebRTC } from '../../hooks/useWebRTC';
import { Mic, Video, Send } from 'lucide-react';
import './VoiceInterview.scss';

export const VoiceInterview = () => {
  const { isConnected, messages, localVideoRef, connect, sendTextMessage } = useWebRTC();
  const [inputText, setInputText] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  // 새 메시지가 올 때마다 스크롤을 맨 아래로 이동
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 보조 수단(텍스트 입력) 전송 처리
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputText.trim() && isConnected) {
      sendTextMessage(inputText);
      setInputText('');
    }
  };

  return (
    <div className="voice-interview-wrapper">
      {/* 1. 좌측: 카메라 영역 (지연 실행 및 거울 모드 적용) */}
      <div className="camera-section">
        <div className="video-container">
          {!isConnected ? (
            // [지연 실행 로직] 연결 전에는 카메라를 켜지 않고 안내 문구와 버튼만 렌더링
            <div className="camera-placeholder">
              <div className="icon-circle">
                <Video size={32} color="#bb38d0" />
              </div>
              <h3>음성 면접 대기 중</h3>
              <p>아래 버튼을 눌러 카메라와 마이크를 켜고 면접을 시작해주세요.</p>
              <button className="btn-start-camera" onClick={connect}>
                <Mic size={18} /> 면접 시작하기
              </button>
            </div>
          ) : (
            // [거울 모드 적용] 연결 시 mirrored-video 클래스가 적용된 비디오 송출
            <>
              <video 
                ref={localVideoRef} 
                autoPlay 
                muted 
                playsInline 
                className="mirrored-video" 
              />
              <div className="recording-indicator">
                <span className="red-dot"></span> 녹화 및 분석 중
              </div>
            </>
          )}
        </div>
      </div>

      {/* 2. 우측: 실시간 음성 인식(STT) 대화 기록 영역 */}
      <div className="transcript-section">
        <div className="guide-banner">
          <strong>음성 인식 모드 가이드</strong>
          <p>답변을 말씀하시면 실시간으로 텍스트로 변환됩니다. 발음이나 철자 교정을 위해 하단 입력창을 보조로 사용할 수 있습니다.</p>
        </div>

        <div className="chat-container">
          {messages.length === 0 && isConnected && (
            <div className="system-msg">AI 면접관이 연결되었습니다. 면접관의 질문을 기다려주세요...</div>
          )}
          
          {messages.map((msg, idx) => (
            <div key={idx} className={`message-row ${msg.sender === 'user' ? 'user' : 'assistant'}`}>
              {msg.sender === 'ai' && <div className="ai-profile-icon">👾</div>}
              
              <div className="message-content">
                {msg.sender === 'ai' && <div className="ai-name">AI 면접관</div>}
                <div className={`bubble ${msg.sender === 'user' ? 'user' : 'assistant'}`}>
                  {msg.text}
                </div>
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* 보조 수단: 음성 인식 오류 시 텍스트로 타이핑할 수 있는 백업 입력창 */}
        <form className="chat-input-area" onSubmit={handleSubmit}>
          <div className="input-wrapper">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={!isConnected ? "면접이 시작되면 입력할 수 있습니다." : "보조 텍스트 입력창 (음성 인식 오류 시 사용)"}
              disabled={!isConnected}
            />
            <button type="submit" disabled={!inputText.trim() || !isConnected} className="btn-submit">
              <Send size={18} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};