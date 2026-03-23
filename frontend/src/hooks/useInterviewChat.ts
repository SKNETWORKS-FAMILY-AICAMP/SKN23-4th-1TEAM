import { useState, useCallback, useRef, useEffect } from "react";
import { useInferStore } from "../store/inferStore";
import { useAuthStore } from "../store/authStore";
import { inferApi } from "../api/inferApi";
import { axiosClient } from "../api/axiosClient";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  score?: number;
}

export const useInterviewChat = () => {
  const { jobRole, difficulty, persona, experienceText, questions, resumeType } =
    useInferStore.getState();
  const { user } = useAuthStore.getState();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isEnded, setIsEnded] = useState(false);

  const currentQIdxRef = useRef(0);
  const followupCountRef = useRef(0);
  const pendingQuestionRef = useRef("");
  // 중복 실행 방지용 Ref
  const initRef = useRef(false);

  useEffect(() => {
    const initInterviewSession = async () => {
      // React StrictMode 더블 렌더링에 의한 중복 방 생성 방지
      if (initRef.current) return;
      initRef.current = true;

      const sessionId = localStorage.getItem("current_session_id");

      if (sessionId) {
        try {
          setIsLoading(true);
          const res = await axiosClient.get(`/api/infer/sessions/${sessionId}`);
          const sessionData = res.data;

          if (sessionData.items && sessionData.items.length > 0) {
            const restoredMessages: ChatMessage[] = [];
            let lastAiQuestion = "";

            sessionData.items.forEach((detail: any) => {
              if (detail.question) {
                restoredMessages.push({
                  role: "assistant",
                  content: detail.question,
                });
                lastAiQuestion = detail.question;
              }
              if (detail.answer) {
                restoredMessages.push({
                  role: "user",
                  content: detail.answer,
                  score: detail.score,
                });
              }
            });

            setMessages(restoredMessages);
            pendingQuestionRef.current = lastAiQuestion;
            currentQIdxRef.current = sessionData.items.filter(
              (d: any) => !d.is_followup,
            ).length;
            return;
          }
        } catch (error) {
          console.error(error);
        } finally {
          setIsLoading(false);
        }
      } else {
        try {
          const res = await axiosClient.post("/api/infer/start", {
            job_role: jobRole || "기본 직무",
            difficulty: difficulty || "중",
            persona: persona || "깐깐한 기술팀장",
          });
          if (res.data?.session_id) {
            localStorage.setItem(
              "current_session_id",
              res.data.session_id.toString(),
            );
          }
        } catch (error) {
          console.error(error);
        }
      }

      const firstQ =
        questions && questions.length > 0
          ? questions[0].question
          : "간단하게 자기소개를 부탁드립니다.";
      const greeting = `안녕하세요. 오늘 ${jobRole || "기본 직무"} 직무 면접을 진행할 면접관입니다.\n\n첫 번째 질문입니다.\n**${firstQ}**`;

      setMessages([{ role: "assistant", content: greeting }]);
      pendingQuestionRef.current = firstQ;
    };

    initInterviewSession();
  }, [difficulty, jobRole, persona, questions]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      setMessages((prev) => [...prev, { role: "user", content: text }]);
      setIsLoading(true);

      try {
        const nextMainQuestion =
          questions && questions.length > currentQIdxRef.current + 1
            ? questions[currentQIdxRef.current + 1].question
            : null;

        const sessionIdStr = localStorage.getItem("current_session_id");
        const sessionId = sessionIdStr ? parseInt(sessionIdStr, 10) : null;
        const currentQuestionForSave = pendingQuestionRef.current;

        const payload = {
          session_id: sessionId,
          question: currentQuestionForSave,
          answer: text,
          input_mode: "text",
          job_role: jobRole || "기본 직무",
          difficulty: difficulty || "중",
          persona_style: persona || "깐깐한 기술팀장",
          user_id: user?.id ? String(user.id) : "guest",
          resume_text: experienceText || "",
          resume_type: resumeType,
          next_main_question: nextMainQuestion,
          followup_count: followupCountRef.current || 0,
          attitude: null,
        };

        const data = await inferApi.evaluateTurn(payload);

        let { reply_text, score, is_followup, feedback } = data;

        if (sessionId) {
          await axiosClient
            .post("/api/interview/details", {
              session_id: sessionId,
              turn_index: currentQIdxRef.current,
              question: currentQuestionForSave,
              answer: text,
              score: score || 0.0,
              feedback: feedback || "",
              is_followup: is_followup || false,
            })
            .catch((err) => console.error(err));
        }

        if (reply_text.includes("[INTERVIEW_END]")) {
          setIsEnded(true);
          reply_text = reply_text.replace("[INTERVIEW_END]", "").trim();

          // 면접이 종료되면 상태 업데이트 및 채점을 위해 백엔드 API 호출
          if (sessionId) {
            axiosClient
              .post("/api/infer/end", { session_id: sessionId })
              .catch((err) => console.error(err));
          }
        }

        if (reply_text.includes("[NEXT_MAIN]")) {
          currentQIdxRef.current += 1;
          followupCountRef.current = 0;
          reply_text = reply_text.replace("[NEXT_MAIN]", "").trim();
        } else if (is_followup) {
          followupCountRef.current += 1;
        }

        pendingQuestionRef.current = reply_text;

        setMessages((prev) => {
          const newMessages = [...prev];

          let lastUserIndex = -1;
          for (let i = newMessages.length - 1; i >= 0; i--) {
            if (newMessages[i].role === "user") {
              lastUserIndex = i;
              break;
            }
          }

          if (lastUserIndex !== -1) {
            newMessages[lastUserIndex].score = score;
          }

          return [...newMessages, { role: "assistant", content: reply_text }];
        });
      } catch (error: any) {
        console.error(error);
        alert("서버 통신 에러가 발생했습니다.");
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, jobRole, difficulty, persona, user, experienceText, questions, resumeType],
  );

  return { messages, isLoading, isEnded, sendMessage };
};
