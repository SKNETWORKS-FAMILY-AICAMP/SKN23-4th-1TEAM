import { useRef, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useWebRTC } from "../../hooks/useWebRTC";
import {
  Mic,
  Loader2,
  Play,
  Square,
  Download,
  PowerOff,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import "./VoiceInterview.scss";

export const VoiceInterview = () => {
  const {
    isConnected,
    isConnecting,
    isRecording,
    isAnalyzing,
    messages,
    localVideoRef,
    localStream,
    cameraDevices,
    selectedCameraId,
    setSelectedCameraId,
    cameraResolution,
    cameraQualityLabel,
    connect,
    disconnect,
    startRecording,
    stopRecording,
    downloadScript,
  } = useWebRTC();

  const [useCamera, setUseCamera] = useState(true);
  const [isMobileCameraCollapsed, setIsMobileCameraCollapsed] = useState(true);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAnalyzing]);

  useEffect(() => {
    if (!isConnected || !useCamera || !localVideoRef.current || !localStream)
      return;
    localVideoRef.current.srcObject = localStream;
    localVideoRef.current.play().catch(() => {});
  }, [isConnected, useCamera, localStream, localVideoRef]);

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  const getStatusMessage = () => {
    if (isConnecting) return "연결 중입니다. 잠시만 기다려주세요.";
    if (!isConnected) return "세션을 준비 중입니다. 마이크를 연결해주세요.";
    if (isAnalyzing) return "답변을 분석 중입니다...";
    if (isRecording)
      return "'녹음 중'입니다. 답변이 끝나면 '녹음 중지 및 제출'을 눌러주세요.";
    return "연결 완료. 답변 준비가 끝나면 '녹음 시작'을 눌러주세요.";
  };

  return (
    <div className="voice-interview-wrapper">
      <div
        className={`camera-section ${!useCamera && isConnected ? "camera-off" : ""} ${isMobileCameraCollapsed ? "mobile-collapsed" : ""}`}
      >
        <button
          type="button"
          className="mobile-camera-toggle"
          onClick={() => setIsMobileCameraCollapsed((prev) => !prev)}
        >
          <span>화면 {isMobileCameraCollapsed ? "펼치기" : "접기"}</span>
          {isMobileCameraCollapsed ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
        </button>

        <div className="video-container">
          {!isConnected ? (
            <div className="camera-placeholder">
              <div className="icon-circle">
                <Mic size={36} color="#0176f7" />
              </div>
              <h3>음성 면접 준비 완료</h3>
              <p>면접 환경 세팅을 위해 마이크를 연결해주세요.</p>

              <label className="camera-toggle-label">
                <input
                  type="checkbox"
                  checked={useCamera}
                  onChange={(event) => setUseCamera(event.target.checked)}
                />
                <span className="toggle-text">카메라 사용</span>
              </label>

              {useCamera && cameraDevices.length > 0 && (
                <label className="camera-select-group">
                  <span className="camera-select-label">카메라 선택</span>
                  <select
                    value={selectedCameraId}
                    onChange={(event) =>
                      setSelectedCameraId(event.target.value)
                    }
                    disabled={isConnected || isConnecting}
                  >
                    {cameraDevices.map((device) => (
                      <option key={device.deviceId} value={device.deviceId}>
                        {device.label}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              <button
                className="btn-start-voice"
                onClick={() => connect(useCamera)}
                disabled={isConnecting}
              >
                {isConnecting ? "연결 중..." : "마이크 연결"}
              </button>
            </div>
          ) : useCamera ? (
            <>
              <video
                ref={localVideoRef}
                autoPlay
                muted
                playsInline
                className="mirrored-video"
              />
              <div className="camera-metrics">
                <strong>{cameraQualityLabel}</strong>
                <span>
                  {cameraResolution
                    ? `${cameraResolution.width} x ${cameraResolution.height}`
                    : "해상도 확인 중"}
                </span>
              </div>
              {isRecording && (
                <div className="recording-indicator">
                  <span className="red-dot"></span> 녹음 중
                </div>
              )}
            </>
          ) : (
            <div className="camera-placeholder audio-only">
              <div className="wave-animation">
                <span></span>
                <span></span>
                <span></span>
                <span></span>
              </div>
              <h3>음성 연결 중</h3>
              <p>카메라 없이 음성으로만 진행합니다.</p>
            </div>
          )}
        </div>
      </div>

      <div className="transcript-section">
        <div className="control-panel">
          <div className="btn-group">
            <button
              className="ctrl-btn"
              onClick={() => connect(useCamera)}
              disabled={isConnected || isConnecting}
            >
              {isConnecting ? "연결 중..." : "마이크 연결"}
            </button>
            <button
              className="ctrl-btn primary"
              onClick={startRecording}
              disabled={!isConnected || isRecording || isAnalyzing}
            >
              <Play size={14} /> 녹음 시작
            </button>
            <button
              className="ctrl-btn danger"
              onClick={stopRecording}
              disabled={!isRecording}
            >
              <Square size={14} /> 녹음 중지 및 제출
            </button>
            <button
              className="ctrl-btn"
              onClick={disconnect}
              disabled={!isConnected && !isConnecting}
            >
              <PowerOff size={14} /> 세션 종료
            </button>
            <button
              className="ctrl-btn"
              onClick={downloadScript}
              disabled={messages.length === 0}
            >
              <Download size={14} /> 스크립트 다운로드
            </button>
          </div>
          <div className={`status-bar ${isRecording ? "recording" : ""}`}>
            {getStatusMessage()}
          </div>
        </div>

        <div className="chat-container">
          <div className="chat-header-title">음성 인식 요약</div>
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`message-row ${msg.sender === "user" ? "user" : "assistant"}`}
            >
              {msg.sender === "ai" && <div className="ai-profile-icon">AI</div>}

              <div className="message-content">
                {msg.sender === "ai" && (
                  <div className="ai-name">AI 면접관</div>
                )}
                <div
                  className={`bubble ${msg.sender === "user" ? "user" : "assistant"}`}
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.text}
                  </ReactMarkdown>
                </div>
                {msg.sender === "user" && (
                  <div
                    style={{
                      display: "flex",
                      gap: "8px",
                      alignItems: "center",
                      marginTop: "4px",
                    }}
                  >
                    {msg.score !== undefined && (
                      <div className="score-badge">
                        AI 평가 점수: {msg.score.toFixed(1)} / 10
                      </div>
                    )}
                    {msg.audioUrl && (
                      <a
                        href={msg.audioUrl}
                        download={`my_answer_${idx}.webm`}
                        style={{
                          fontSize: "12px",
                          color: "#0176f7",
                          textDecoration: "none",
                          fontWeight: "bold",
                        }}
                      >
                        음성 다운로드
                      </a>
                    )}
                  </div>
                )}
                {msg.sender === "user" && msg.attitudeSummary && (
                  <div className="attitude-summary-badge">
                    태도 분석: {msg.attitudeSummary}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isAnalyzing && (
            <div className="message-row assistant">
              <div className="ai-profile-icon">AI</div>
              <div className="message-content">
                <div className="bubble assistant typing">
                  <Loader2 className="spinner" size={16} /> 면접관이 답변을 분석
                  중입니다...
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
      </div>
    </div>
  );
};
