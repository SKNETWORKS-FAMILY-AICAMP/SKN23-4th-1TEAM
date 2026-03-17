import { create } from 'zustand';

interface InferState {
  jobRole: string | null;
  difficulty: string | null;
  method: 'text' | 'voice' | null;
  persona: string | null;
  questionCount: number | null;
  resumeType: 'file' | 'direct' | null;
  experienceText: string | null;
  resumeData: Record<string, any> | null;
  resumeUsed: boolean;
  questions: { question: string }[] | null;
  resumeId: number | null;
  resumeTitle: string | null;

  setInferSettings: (
    jobRole: string,
    difficulty: string,
    extraSettings: {
      method: 'text' | 'voice';
      persona: string;
      questionCount: number;
      resumeType: 'file' | 'direct';
      experienceText: string;
      questions: { question: string }[];
    },
    resumeUsed: boolean,
    resumeId?: number,
    resumeTitle?: string
  ) => void;
  setResumeUsed: (used: boolean) => void;
  clearInferSettings: () => void;
}

export const useInferStore = create<InferState>((set) => ({
  jobRole: null,
  difficulty: null,
  method: null,
  persona: null,
  questionCount: null,
  resumeType: null,
  experienceText: null,
  resumeData: null,
  resumeUsed: false,
  questions: null,
  resumeId: null,
  resumeTitle: null,
  
  setInferSettings: (jobRole, difficulty, extraSettings, resumeUsed, resumeId = null, resumeTitle = null) =>
    set({
      jobRole,
      difficulty,
      method: extraSettings.method,
      persona: extraSettings.persona,
      questionCount: extraSettings.questionCount,
      resumeType: extraSettings.resumeType,
      experienceText: extraSettings.experienceText,
      questions: extraSettings.questions,
      resumeUsed,
      resumeId,
      resumeTitle
    }),
    
  setResumeUsed: (used) => set({ resumeUsed: used }),

  clearInferSettings: () => set({
    jobRole: null,
    difficulty: null,
    method: null,
    persona: null,
    questionCount: null,
    resumeType: null,
    experienceText: null,
    resumeData: null,
    resumeUsed: false,
    questions: null,
    resumeId: null,
    resumeTitle: null
  }),
}));