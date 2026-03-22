export interface EvaluationPayload {
  session_id?: number | null;
  question: string;
  answer: string;
  job_role?: string;
  difficulty?: string;
  persona_style?: string;
  user_id?: string;
  resume_text?: string | null;
  next_main_question?: string | null;
  followup_count?: number;
  attitude?: {
    summary_text?: string;
    metrics?: Record<string, unknown>;
    events?: Array<Record<string, unknown>>;
  } | null;
}

export interface EvaluationResponse {
  reply_text: string;
  score: number;
  feedback: string;
  is_followup?: boolean;
  [key: string]: unknown;
}
