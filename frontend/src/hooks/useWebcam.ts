import { useRef, useState, useCallback, useEffect } from 'react';

export const useWebcam = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isWebcamActive, setIsWebcamActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startWebcam = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        // audio is handled separately by WebRTC Realtime API usually, 
        // but can be included here if needed for local recording.
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsWebcamActive(true);
      setError(null);
    } catch (err: unknown) {
      console.error('Error accessing webcam:', err);
      
      let message = '카메라를 시작할 수 없습니다. 다시 시도해 주세요.';
      if (err instanceof DOMException) {
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          message = '카메라 및 마이크 권한을 허용해 주세요.\n브라우저 주소창 왼쪽 🔒 아이콘을 클릭하여 권한을 허용한 후 새로고침하세요.';
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
          message = '연결된 카메라 장치를 찾을 수 없습니다. 카메라가 연결되어 있는지 확인해 주세요.';
        } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
          message = '카메라가 다른 앱에서 사용 중입니다. 다른 앱을 종료한 후 다시 시도해 주세요.';
        }
      }
      
      setError(message);
      setIsWebcamActive(false);
    }
  }, []);

  const stopWebcam = useCallback(() => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      const tracks = stream.getTracks();
      tracks.forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    setIsWebcamActive(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopWebcam();
    };
  }, [stopWebcam]);

  return {
    videoRef,
    isWebcamActive,
    error,
    startWebcam,
    stopWebcam
  };
};
