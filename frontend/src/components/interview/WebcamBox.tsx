import { useEffect } from "react";
import { Camera, CameraOff, AlertCircle, ShieldAlert } from "lucide-react";
import { useWebcam } from "../../hooks/useWebcam";

export const WebcamBox = () => {
  const { videoRef, isWebcamActive, error, startWebcam, stopWebcam } =
    useWebcam();

  useEffect(() => {
    startWebcam();
    return () => stopWebcam();
  }, [startWebcam, stopWebcam]);

  // 권한 거절 에러 여부 판단
  const isPermissionError = error?.includes("권한을 허용");

  return (
    <div className="webcam-box glass-panel">
      <div className="webcam-header">
        <h3>Interview Feed</h3>
        <div className="status-indicator">
          {isWebcamActive ? (
            <span className="active">
              <Camera size={16} /> Live
            </span>
          ) : (
            <span className="inactive">
              <CameraOff size={16} /> Offline
            </span>
          )}
        </div>
      </div>

      <div className="video-container">
        {error ? (
          <div className="error-state">
            {isPermissionError ? (
              <ShieldAlert size={40} strokeWidth={1.5} />
            ) : (
              <AlertCircle size={40} strokeWidth={1.5} />
            )}
            {/* 에러 메시지 줄바꿈 처리 */}
            {error.split("\n").map((line, i) => (
              <p key={i} style={{ margin: "4px 0" }}>
                {line}
              </p>
            ))}
            <button
              className="retry-btn"
              onClick={startWebcam}
              style={{
                marginTop: "16px",
                padding: "8px 22px",
                borderRadius: "8px",
                border: "1px solid currentColor",
                background: "transparent",
                cursor: "pointer",
                fontWeight: 700,
                fontSize: "14px",
              }}
            >
              다시 시도
            </button>
          </div>
        ) : (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={isWebcamActive ? "active" : ""}
            style={{ transform: "scaleX(-1)" }}
          />
        )}
        {!isWebcamActive && !error && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>카메라를 초기화하는 중입니다...</p>
          </div>
        )}
      </div>

      <div className="webcam-controls">
        <button
          onClick={isWebcamActive ? stopWebcam : startWebcam}
          className={`control-btn ${isWebcamActive ? "danger" : "primary"}`}
        >
          {isWebcamActive ? <CameraOff size={20} /> : <Camera size={20} />}
        </button>
      </div>
    </div>
  );
};
