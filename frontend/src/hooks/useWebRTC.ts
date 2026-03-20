import { useState, useRef, useCallback, useEffect } from 'react';
import { inferApi, type AttitudeFramePayload } from '../api/inferApi';
import { useInferStore } from '../store/inferStore';
import { useAuthStore } from '../store/authStore';

export interface VoiceMessage {
  sender: 'user' | 'ai';
  text: string;
  score?: number;
  audioUrl?: string;
  attitudeSummary?: string;
}

interface CameraDeviceOption {
  deviceId: string;
  label: string;
}

interface CameraResolution {
  width: number;
  height: number;
}

const getQualityLabel = (height: number) => {
  if (height >= 1080) return '1080p+';
  if (height >= 720) return '720p';
  if (height >= 480) return '480p';
  return 'SD';
};

export const useWebRTC = () => {
  const { jobRole, difficulty, persona, experienceText, questions } = useInferStore.getState();
  const { user } = useAuthStore.getState();

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [messages, setMessages] = useState<VoiceMessage[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [cameraDevices, setCameraDevices] = useState<CameraDeviceOption[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState('');
  const [cameraResolution, setCameraResolution] = useState<CameraResolution | null>(null);
  const [cameraQualityLabel, setCameraQualityLabel] = useState('camera off');

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dataChannelRef = useRef<RTCDataChannel | null>(null);
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const currentQIdxRef = useRef(0);
  const followupCountRef = useRef(0);
  const pendingQuestionRef = useRef(questions?.[0]?.question || '간단하게 자기소개를 부탁드립니다.');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const initialPromptSentRef = useRef(false);
  const attitudeFramesRef = useRef<AttitudeFramePayload[]>([]);
  const attitudeCaptureTimerRef = useRef<number | null>(null);
  const recordingStartedAtRef = useRef(0);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!localVideoRef.current || !localStream) return;
    localVideoRef.current.srcObject = localStream;
    localVideoRef.current.play().catch(() => {});
  }, [localStream, isConnected]);

  const updateCameraMetrics = useCallback((stream: MediaStream | null) => {
    const videoTrack = stream?.getVideoTracks()[0];
    if (!videoTrack) {
      setCameraResolution(null);
      setCameraQualityLabel('camera off');
      return;
    }

    const settings = videoTrack.getSettings();
    const width = settings.width ?? 0;
    const height = settings.height ?? 0;

    if (!width || !height) {
      setCameraResolution(null);
      setCameraQualityLabel('camera on');
      return;
    }

    setCameraResolution({ width, height });
    setCameraQualityLabel(getQualityLabel(height));
  }, []);

  const refreshCameraDevices = useCallback(async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoInputs = devices
        .filter((device) => device.kind === 'videoinput')
        .map((device, index) => ({
          deviceId: device.deviceId,
          label: device.label || `카메라 ${index + 1}`,
        }));

      setCameraDevices(videoInputs);
      setSelectedCameraId((prev) => {
        if (videoInputs.some((device) => device.deviceId === prev)) return prev;
        return videoInputs[0]?.deviceId ?? '';
      });
    } catch (error) {
      console.error(error);
    }
  }, []);

  useEffect(() => {
    refreshCameraDevices();

    const handleDeviceChange = () => {
      refreshCameraDevices();
    };

    navigator.mediaDevices?.addEventListener?.('devicechange', handleDeviceChange);

    return () => {
      navigator.mediaDevices?.removeEventListener?.('devicechange', handleDeviceChange);
    };
  }, [refreshCameraDevices]);

  const captureAttitudeFrame = useCallback(() => {
    const video = localVideoRef.current;
    if (!video || video.readyState < 2 || video.videoWidth === 0 || video.videoHeight === 0) return;

    const canvas = captureCanvasRef.current ?? document.createElement('canvas');
    captureCanvasRef.current = canvas;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext('2d');
    if (!context) return;

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.82);
    const imageBase64 = dataUrl.split(',')[1];
    if (!imageBase64) return;

    attitudeFramesRef.current.push({
      t_ms: Math.max(0, Date.now() - recordingStartedAtRef.current),
      image_b64: imageBase64,
    });

    if (attitudeFramesRef.current.length > 12) {
      attitudeFramesRef.current = attitudeFramesRef.current.slice(-12);
    }
  }, []);

  const stopAttitudeSampling = useCallback(() => {
    if (attitudeCaptureTimerRef.current !== null) {
      window.clearInterval(attitudeCaptureTimerRef.current);
      attitudeCaptureTimerRef.current = null;
    }
  }, []);

  const startAttitudeSampling = useCallback(() => {
    stopAttitudeSampling();
    attitudeFramesRef.current = [];
    recordingStartedAtRef.current = Date.now();

    const hasVideoTrack = Boolean(localStream?.getVideoTracks().length);
    if (!hasVideoTrack) return;

    captureAttitudeFrame();
    attitudeCaptureTimerRef.current = window.setInterval(() => {
      captureAttitudeFrame();
    }, 500);
  }, [captureAttitudeFrame, localStream, stopAttitudeSampling]);

  const analyzeLatestAttitude = useCallback(async () => {
    stopAttitudeSampling();

    const frames = [...attitudeFramesRef.current];
    attitudeFramesRef.current = [];

    if (frames.length === 0) return null;

    try {
      return await inferApi.analyzeAttitude(frames);
    } catch (error) {
      console.error(error);
      return null;
    }
  }, [stopAttitudeSampling]);

  const evaluateAndSaveToDB = async (userText: string) => {
    try {
      setIsAnalyzing(true);
      const attitude = await analyzeLatestAttitude();

      const nextMainQuestion =
        questions && questions.length > currentQIdxRef.current + 1
          ? questions[currentQIdxRef.current + 1].question
          : null;
      const sessionId = localStorage.getItem('current_session_id');

      const payload = {
        session_id: sessionId ? parseInt(sessionId, 10) : null,
        question: pendingQuestionRef.current,
        answer: userText,
        job_role: jobRole || '기본 직무',
        difficulty: difficulty || '중',
        persona_style: persona || '친절한 기술 면접관',
        user_id: user?.id ? String(user.id) : 'guest',
        resume_text: experienceText || '',
        next_main_question: nextMainQuestion,
        followup_count: followupCountRef.current || 0,
        attitude,
      };

      const data = await inferApi.evaluateTurn(payload);
      let { reply_text, score, is_followup } = data;

      let isEnd = false;
      if (reply_text.includes('[NEXT_MAIN]')) {
        currentQIdxRef.current += 1;
        followupCountRef.current = 0;
        reply_text = reply_text.replace('[NEXT_MAIN]', '').trim();
      } else if (is_followup) {
        followupCountRef.current += 1;
      }

      if (reply_text.includes('[INTERVIEW_END]')) {
        isEnd = true;
        reply_text = reply_text.replace('[INTERVIEW_END]', '').trim();
      }

      pendingQuestionRef.current = reply_text;

      setMessages((prev) => {
        const next = [...prev];
        let lastUserIndex = -1;

        for (let i = next.length - 1; i >= 0; i -= 1) {
          if (next[i].sender === 'user') {
            lastUserIndex = i;
            break;
          }
        }

        if (lastUserIndex !== -1) {
          next[lastUserIndex].score = score;
          next[lastUserIndex].attitudeSummary = attitude?.summary_text || undefined;
        }

        return next;
      });

      if (isEnd) {
        alert('면접이 종료되었습니다. 면접 기록 페이지로 이동합니다.');
        window.location.href = '/mypage';
      }
    } catch (error) {
      console.error(error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const createMediaStream = useCallback(
    async (useCamera: boolean) => {
      const audio: MediaTrackConstraints | boolean = {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      };

      if (!useCamera) {
        return navigator.mediaDevices.getUserMedia({ audio, video: false });
      }

      const idealDeviceId = selectedCameraId ? { ideal: selectedCameraId } : undefined;
      const preferredFacingMode = selectedCameraId ? undefined : 'user';

      const attempts: MediaStreamConstraints[] = [
        {
          audio,
          video: {
            deviceId: idealDeviceId,
            facingMode: preferredFacingMode,
            width: { ideal: 1280 },
            height: { ideal: 720 },
            frameRate: { ideal: 24 },
          },
        },
        {
          audio,
          video: {
            deviceId: idealDeviceId,
            facingMode: preferredFacingMode,
          },
        },
        {
          audio,
          video: {
            facingMode: preferredFacingMode,
          },
        },
        { audio, video: true },
      ];

      let lastError: unknown = null;

      for (const constraints of attempts) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia(constraints);
          const videoTrack = stream.getVideoTracks()[0];

          if (videoTrack) {
            try {
              await videoTrack.applyConstraints({
                width: { ideal: 1920 },
                height: { ideal: 1080 },
                frameRate: { ideal: 30 },
              });
            } catch (constraintError) {
              try {
                await videoTrack.applyConstraints({
                  width: { ideal: 1280 },
                  height: { ideal: 720 },
                  frameRate: { ideal: 24 },
                });
              } catch (fallbackConstraintError) {
                console.warn('Unable to apply camera constraints.', fallbackConstraintError);
              }
            }
          }

          updateCameraMetrics(stream);
          return stream;
        } catch (error) {
          lastError = error;
        }
      }

      throw lastError;
    },
    [selectedCameraId, updateCameraMetrics],
  );

  const connect = useCallback(
    async (useCamera: boolean) => {
      if (isConnected || isConnecting) return;

      try {
        setIsConnecting(true);
        initialPromptSentRef.current = false;

        const { client_secret } = await inferApi.getRealtimeToken();
        const pc = new RTCPeerConnection();
        pcRef.current = pc;

        const ms = await createMediaStream(useCamera);
        const audioTrack = ms.getAudioTracks()[0];
        const videoTrack = ms.getVideoTracks()[0];

        if (audioTrack) audioTrack.enabled = false;

        setLocalStream(ms);
        if (audioTrack) pc.addTrack(audioTrack, ms);
        if (videoTrack) pc.addTrack(videoTrack, ms);
        await refreshCameraDevices();

        const recorder = new MediaRecorder(ms);
        mediaRecorderRef.current = recorder;

        recorder.ondataavailable = (event) => {
          if (event.data.size > 0) audioChunksRef.current.push(event.data);
        };

        recorder.onstop = () => {
          const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          const url = URL.createObjectURL(blob);
          audioChunksRef.current = [];

          setMessages((prev) => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0 && next[lastIndex].sender === 'user') {
              next[lastIndex].audioUrl = url;
            }
            return next;
          });
        };

        pc.ontrack = (event) => {
          const audioEl = document.createElement('audio');
          audioEl.autoplay = true;
          audioEl.srcObject = event.streams[0];
        };

        const dc = pc.createDataChannel('oai-events');
        dataChannelRef.current = dc;

        dc.onopen = () => {
          setIsConnected(true);
          setIsConnecting(false);

          dc.send(
            JSON.stringify({
              type: 'session.update',
              session: {
                modalities: ['audio', 'text'],
                instructions: `당신은 ${jobRole} 직무의 ${persona}입니다. 지원자와 모의 면접을 진행합니다. 음성으로만 말해주세요.`,
                input_audio_transcription: { model: 'whisper-1' },
                turn_detection: null,
              },
            }),
          );

          if (initialPromptSentRef.current) return;
          initialPromptSentRef.current = true;

          setTimeout(() => {
            if (!dataChannelRef.current || dataChannelRef.current.readyState !== 'open') return;

            const initPrompt = `지금 면접을 시작합니다. 지원자에게 인사하고 다음 질문을 직접 읽어주세요: "${pendingQuestionRef.current}"`;

            dataChannelRef.current.send(
              JSON.stringify({
                type: 'conversation.item.create',
                item: {
                  type: 'message',
                  role: 'user',
                  content: [{ type: 'input_text', text: initPrompt }],
                },
              }),
            );
            dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
          }, 1000);
        };

        dc.onmessage = async (event) => {
          const realtimeEvent = JSON.parse(event.data);

          if (realtimeEvent.type === 'response.audio_transcript.done') {
            setMessages((prev) => [...prev, { sender: 'ai', text: realtimeEvent.transcript }]);
          } else if (realtimeEvent.type === 'conversation.item.input_audio_transcription.completed') {
            const userTranscript = realtimeEvent.transcript.trim();
            if (userTranscript) {
              setMessages((prev) => [...prev, { sender: 'user', text: userTranscript }]);
              await evaluateAndSaveToDB(userTranscript);
            }
          }
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const response = await fetch('https://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17', {
          method: 'POST',
          body: offer.sdp,
          headers: {
            Authorization: `Bearer ${client_secret.value}`,
            'Content-Type': 'application/sdp',
          },
        });

        const answerSdp = await response.text();
        await pc.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: answerSdp }));
      } catch (error) {
        console.error(error);
        alert('마이크 또는 카메라 권한을 확인해주세요.');
      } finally {
        setIsConnecting(false);
      }
    },
    [createMediaStream, isConnected, isConnecting, jobRole, persona, refreshCameraDevices],
  );

  const disconnect = useCallback(() => {
    initialPromptSentRef.current = false;
    stopAttitudeSampling();
    attitudeFramesRef.current = [];

    if (localVideoRef.current) {
      localVideoRef.current.srcObject = null;
    }

    setLocalStream((prevStream) => {
      if (prevStream) {
        prevStream.getTracks().forEach((track) => track.stop());
      }
      return null;
    });

    setCameraResolution(null);
    setCameraQualityLabel('camera off');

    if (pcRef.current) pcRef.current.close();
    pcRef.current = null;
    dataChannelRef.current = null;
    setIsConnected(false);
    setIsConnecting(false);
    setIsRecording(false);
  }, [stopAttitudeSampling]);

  const startRecording = useCallback(() => {
    if (localStream && dataChannelRef.current) {
      const audioTrack = localStream.getAudioTracks()[0];
      if (audioTrack) audioTrack.enabled = true;
      setIsRecording(true);
      startAttitudeSampling();

      if (mediaRecorderRef.current?.state === 'inactive') {
        audioChunksRef.current = [];
        mediaRecorderRef.current.start();
      }

      dataChannelRef.current.send(JSON.stringify({ type: 'input_audio_buffer.clear' }));
    }
  }, [localStream, startAttitudeSampling]);

  const stopRecording = useCallback(() => {
    if (localStream && dataChannelRef.current) {
      const audioTrack = localStream.getAudioTracks()[0];
      if (audioTrack) audioTrack.enabled = false;
      setIsRecording(false);
      stopAttitudeSampling();

      if (mediaRecorderRef.current?.state === 'recording') {
        mediaRecorderRef.current.stop();
      }

      dataChannelRef.current.send(JSON.stringify({ type: 'input_audio_buffer.commit' }));
      dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
    }
  }, [localStream, stopAttitudeSampling]);

  const downloadScript = useCallback(() => {
    const scriptText = messages.map((message) => `[${message.sender === 'user' ? '지원자' : 'AI 면접관'}]\n${message.text}\n`).join('\n');
    const blob = new Blob([scriptText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'interview_script.txt';
    anchor.click();
    URL.revokeObjectURL(url);
  }, [messages]);

  return {
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
    refreshCameraDevices,
  };
};
