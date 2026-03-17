import { useState, useCallback, useRef, useEffect } from 'react';
import { useInferStore } from '../store/inferStore';
import { inferApi } from '../api/inferApi';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  score?: number;
}

export const useInterviewChat = () => {
  const { jobRole, difficulty, persona, userId, experienceText, questions } = useInferStore.getState();
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isEnded, setIsEnded] = useState(false);
  
  const currentQIdxRef = useRef(0);
  const followupCountRef = useRef(0);
  const pendingQuestionRef = useRef("간단하게 자기소개를 부탁드립니다."); 

  useEffect(() => {
    if (messages.length === 0) {
      const firstQ = (questions && questions.length > 0) ? questions[0].question : "간단하게 자기소개를 부탁드립니다.";
      const greeting = `안녕하세요. 오늘 ${jobRole || '기본 직무'} 직무 면접을 진행할 면접관입니다.\n\n첫 번째 질문입니다.\n**${firstQ}**`;
      
      setMessages([{ role: 'assistant', content: greeting }]);
      pendingQuestionRef.current = firstQ;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); 

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setIsLoading(true);

    try {
      const nextMainQuestion = 
        questions && questions.length > currentQIdxRef.current + 1 
          ? questions[currentQIdxRef.current + 1].question 
          : null;

      const payload = {
        question: pendingQuestionRef.current || "면접 질문",
        answer: text,
        job_role: jobRole || "기본 직무",
        difficulty: difficulty || "중",
        persona_style: persona || "깐깐한 기술팀장",
        user_id: userId ? String(userId) : "guest",
        resume_text: experienceText || "", 
        next_main_question: nextMainQuestion,
        followup_count: followupCountRef.current || 0,
        attitude: null,
      };

      const data = await inferApi.evaluateTurn(payload);
      
      let { reply_text, score, is_followup } = data;

      if (reply_text.includes('[INTERVIEW_END]')) {
        setIsEnded(true);
        reply_text = reply_text.replace('[INTERVIEW_END]', '').trim();
      }
      
      if (reply_text.includes('[NEXT_MAIN]')) {
        currentQIdxRef.current += 1;
        followupCountRef.current = 0;
        reply_text = reply_text.replace('[NEXT_MAIN]', '').trim();
      } else if (is_followup) {
        followupCountRef.current += 1;
      }

      pendingQuestionRef.current = reply_text;

      setMessages(prev => {
        const newMessages = [...prev];
        const lastUserIndex = newMessages.findLastIndex(m => m.role === 'user');
        if (lastUserIndex !== -1) {
          newMessages[lastUserIndex].score = score;
        }
        return [...newMessages, { role: 'assistant', content: reply_text }];
      });

    } catch (error: any) {
      console.error("평가 API 호출 실패:", error);
      alert(`서버 통신 에러: ${error.response?.status || error.message || '알 수 없음'}\n개발자 도구(F12)의 Network 탭을 확인해주세요.`);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, jobRole, difficulty, persona, userId, experienceText, questions]);

  return { messages, isLoading, isEnded, sendMessage };
};