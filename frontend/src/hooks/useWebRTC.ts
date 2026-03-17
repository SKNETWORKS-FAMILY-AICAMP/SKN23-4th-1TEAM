import { useState, useRef, useCallback } from 'react';
import { inferApi } from '../api/inferApi';
import { useInferStore } from '../store/inferStore';

export const useWebRTC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<Array<{ sender: string; text: string }>>([]);
  
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dataChannelRef = useRef<RTCDataChannel | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  
  // 비디오 태그에 연결할 Ref 추가 (화면 렌더링용)
  const localVideoRef = useRef<HTMLVideoElement>(null);

  const connect = useCallback(async () => {
    try {
      const { persona, jobRole } = useInferStore.getState();

      const { client_secret } = await inferApi.getRealtimeToken();
      const ephemeralToken = client_secret.value;

      const pc = new RTCPeerConnection();
      pcRef.current = pc;

      // 핵심 해결: 버튼을 누르는 순간(connect 함수 실행)에만 카메라/마이크 권한 요청
      const ms = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      localStreamRef.current = ms;
      
      // 비디오 태그에 화면 연결
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = ms;
      }

      // 오디오 트랙만 WebRTC로 전송 (비디오는 화면에만 보여주고 전송하지 않음)
      const audioTrack = ms.getAudioTracks()[0];
      pc.addTrack(audioTrack, ms);
      
      pc.ontrack = (e) => {
        const audioEl = document.createElement('audio');
        audioEl.autoplay = true;
        audioEl.srcObject = e.streams[0];
      };

      const dc = pc.createDataChannel('oai-events');
      dataChannelRef.current = dc;

      dc.onopen = () => {
        setIsConnected(true);
        
        // 시스템 설정(한국어, 음성/텍스트 모달리티) 주입
        const sessionUpdate = {
          type: 'session.update',
          session: {
            modalities: ['audio', 'text'],
            instructions: `당신은 ${jobRole} 직무의 ${persona}입니다. 지원자와 모의 면접을 진행합니다. 모든 질문과 답변은 반드시 '한국어(Korean)'로만 하세요. 절대 영어로 말하지 마세요.`,
            input_audio_transcription: { model: "whisper-1" } // STT 처리를 위해 필수
          }
        };
        dc.send(JSON.stringify(sessionUpdate));
      };

      dc.onmessage = (e) => {
        const event = JSON.parse(e.data);
        if (event.type === 'response.audio_transcript.done') {
          setMessages(prev => [...prev, { sender: 'ai', text: event.transcript }]);
        } else if (event.type === 'response.text.done') {
          setMessages(prev => [...prev, { sender: 'ai', text: event.text }]);
        } else if (event.type === 'conversation.item.input_audio_transcription.completed') {
          // 사용자의 음성이 텍스트로 변환되었을 때
          setMessages(prev => [...prev, { sender: 'user', text: event.transcript }]);
        }
      };

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const baseUrl = 'https://api.openai.com/v1/realtime';
      const model = 'gpt-4o-realtime-preview-2024-12-17';
      const response = await fetch(`${baseUrl}?model=${model}`, {
        method: 'POST',
        body: offer.sdp,
        headers: {
          Authorization: `Bearer ${ephemeralToken}`,
          'Content-Type': 'application/sdp'
        },
      });

      if (!response.ok) {
        throw new Error(`OpenAI Connection Failed: ${response.status}`);
      }

      const answerSdp = await response.text();
      const answer = new RTCSessionDescription({ type: 'answer', sdp: answerSdp });
      await pc.setRemoteDescription(answer);

    } catch (err) {
      console.error('WebRTC Connection failed:', err);
      setIsConnected(false);
    }
  }, []);

  const disconnect = useCallback(() => {
    // 연결 종료 시 브라우저가 잡고 있는 마이크/카메라 권한을 완벽하게 해제
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
      localStreamRef.current = null;
    }
    
    if (localVideoRef.current) {
      localVideoRef.current.srcObject = null;
    }
    
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    if (dataChannelRef.current) {
      dataChannelRef.current.close();
      dataChannelRef.current = null;
    }
    setIsConnected(false);
    setMessages([]);
  }, []);

  // 음성 모드에서도 텍스트를 보낼 수 있는 기능은 유지 (보조 수단)
  const sendTextMessage = useCallback((text: string) => {
    if (dataChannelRef.current && isConnected) {
      const event = {
        type: 'conversation.item.create',
        item: {
          type: 'message',
          role: 'user',
          content: [{ type: 'input_text', text }]
        }
      };
      dataChannelRef.current.send(JSON.stringify(event));
      dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
      setMessages(prev => [...prev, { sender: 'user', text }]);
    }
  }, [isConnected]);

  return { isConnected, messages, localVideoRef, connect, disconnect, sendTextMessage };
};