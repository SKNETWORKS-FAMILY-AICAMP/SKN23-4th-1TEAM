import { useState, useRef, useCallback } from 'react';
import { inferApi } from '../api/inferApi';
import { useInferStore } from '../store/inferStore';
import { useAuthStore } from '../store/authStore';

export interface VoiceMessage {
  sender: 'user' | 'ai';
  text: string;
  score?: number;
  audioUrl?: string; 
}

export const useWebRTC = () => {
  const { jobRole, difficulty, persona, experienceText, questions } = useInferStore.getState();
  const { user } = useAuthStore.getState();

  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [messages, setMessages] = useState<VoiceMessage[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dataChannelRef = useRef<RTCDataChannel | null>(null);
  const localVideoRef = useRef<HTMLVideoElement>(null);

  const currentQIdxRef = useRef(0);
  const followupCountRef = useRef(0);
  const pendingQuestionRef = useRef(questions?.[0]?.question || "간단하게 자기소개를 부탁드립니다.");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const evaluateAndSaveToDB = async (userText: string) => {
    try {
      setIsAnalyzing(true);
      const nextMainQuestion = questions && questions.length > currentQIdxRef.current + 1 
          ? questions[currentQIdxRef.current + 1].question : null;
      const sessionId = localStorage.getItem('current_session_id');

      const payload = {
        session_id: sessionId ? parseInt(sessionId, 10) : null,
        question: pendingQuestionRef.current,
        answer: userText,
        job_role: jobRole || "기본 직무",
        difficulty: difficulty || "중",
        persona_style: persona || "깐깐한 기술팀장",
        user_id: user?.id ? String(user.id) : "guest",
        resume_text: experienceText || "", 
        next_main_question: nextMainQuestion,
        followup_count: followupCountRef.current || 0,
        attitude: null,
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

      setMessages(prev => {
        const newMessages = [...prev];
        let lastUserIndex = -1;
        for (let i = newMessages.length - 1; i >= 0; i--) {
          if (newMessages[i].sender === 'user') { lastUserIndex = i; break; }
        }
        if (lastUserIndex !== -1) newMessages[lastUserIndex].score = score;
        return newMessages;
      });

      if (isEnd) {
         alert("면접이 종료되었습니다. 면접 기록 페이지로 이동합니다.");
         window.location.href = '/mypage'; 
      }

    } catch (error) {
      console.error(error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const connect = useCallback(async (useCamera: boolean) => {
    try {
      const { client_secret } = await inferApi.getRealtimeToken();
      const pc = new RTCPeerConnection();
      pcRef.current = pc;

      const ms = await navigator.mediaDevices.getUserMedia({ video: useCamera, audio: true });
      
      const audioTrack = ms.getAudioTracks()[0];
      audioTrack.enabled = false;
      
      setLocalStream(ms);
      pc.addTrack(audioTrack, ms);

      const recorder = new MediaRecorder(ms);
      mediaRecorderRef.current = recorder;
      
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      
      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const url = URL.createObjectURL(blob);
        audioChunksRef.current = [];
        
        setMessages(prev => {
          const newMsgs = [...prev];
          const lastIdx = newMsgs.length - 1;
          if (lastIdx >= 0 && newMsgs[lastIdx].sender === 'user') {
            newMsgs[lastIdx].audioUrl = url;
          }
          return newMsgs;
        });
      };
      
      pc.ontrack = (e) => {
        const audioEl = document.createElement('audio');
        audioEl.autoplay = true;
        audioEl.srcObject = e.streams[0];
      };

      const dc = pc.createDataChannel('oai-events');
      dataChannelRef.current = dc;

      dc.onopen = () => {
        setIsConnected(true);
        dc.send(JSON.stringify({
          type: 'session.update',
          session: {
            modalities: ['audio', 'text'],
            instructions: `당신은 ${jobRole} 직무의 ${persona}입니다. 지원자와 모의 면접을 진행합니다. 한국어로만 말하세요.`,
            input_audio_transcription: { model: "whisper-1" },
            turn_detection: null
          }
        }));

        setTimeout(() => {
          const initPrompt = `지금 면접을 시작합니다. 지원자에게 인사하고 다음 질문을 직접 육성으로 말해주세요: "${pendingQuestionRef.current}"`;
          dc.send(JSON.stringify({
            type: 'conversation.item.create',
            item: {
              type: 'message',
              role: 'user',
              content: [{ type: 'input_text', text: initPrompt }]
            }
          }));
          dc.send(JSON.stringify({ type: 'response.create' }));
        }, 1000);
      };

      dc.onmessage = async (e) => {
        const event = JSON.parse(e.data);
        if (event.type === 'response.audio_transcript.done') {
          setMessages(prev => [...prev, { sender: 'ai', text: event.transcript }]);
        } else if (event.type === 'conversation.item.input_audio_transcription.completed') {
          const userTranscript = event.transcript.trim();
          if (userTranscript) {
            setMessages(prev => [...prev, { sender: 'user', text: userTranscript }]);
            await evaluateAndSaveToDB(userTranscript);
          }
        }
      };

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const response = await fetch(`https://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17`, {
        method: 'POST',
        body: offer.sdp,
        headers: { Authorization: `Bearer ${client_secret.value}`, 'Content-Type': 'application/sdp' },
      });

      const answerSdp = await response.text();
      await pc.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: answerSdp }));
    } catch (err) {
      console.error(err);
      alert('마이크/카메라 권한을 허용해주세요.');
    }
  }, [jobRole, persona]);

  const disconnect = useCallback(() => {
    setLocalStream(prevStream => {
      if (prevStream) {
        prevStream.getTracks().forEach(track => track.stop());
      }
      return null;
    });
    
    if (pcRef.current) pcRef.current.close();
    setIsConnected(false);
    setIsRecording(false);
  }, []);

  const startRecording = useCallback(() => {
    if (localStream && dataChannelRef.current) {
      const audioTrack = localStream.getAudioTracks()[0];
      if (audioTrack) audioTrack.enabled = true;
      setIsRecording(true);
      
      if (mediaRecorderRef.current?.state === 'inactive') {
        audioChunksRef.current = [];
        mediaRecorderRef.current.start();
      }
      
      dataChannelRef.current.send(JSON.stringify({ type: 'input_audio_buffer.clear' }));
    }
  }, [localStream]);

  const stopRecording = useCallback(() => {
    if (localStream && dataChannelRef.current) {
      const audioTrack = localStream.getAudioTracks()[0];
      if (audioTrack) audioTrack.enabled = false;
      setIsRecording(false);
      
      if (mediaRecorderRef.current?.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
      
      dataChannelRef.current.send(JSON.stringify({ type: 'input_audio_buffer.commit' }));
      dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
    }
  }, [localStream]);

  const downloadScript = useCallback(() => {
    const scriptText = messages.map(m => `[${m.sender === 'user' ? '지원자' : 'AI 면접관'}]\n${m.text}\n`).join('\n');
    const blob = new Blob([scriptText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'interview_script.txt';
    a.click();
    URL.revokeObjectURL(url);
  }, [messages]);

  return { 
    isConnected, isRecording, isAnalyzing, messages, localVideoRef, 
    connect, disconnect, startRecording, stopRecording, downloadScript 
  };
};