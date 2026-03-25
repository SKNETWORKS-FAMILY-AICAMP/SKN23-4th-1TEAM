import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface GuideMessage {
  id: string;
  type: "user" | "bot";
  content: string;
  downloadContent?: string;
  downloadFilename?: string;
  saveResumePayload?: {
    title: string;
    text: string;
  };
}

export interface SavedResume {
  id: string;
  title: string;
}

export type ToastType = "success" | "error" | "warning";

export interface ConfirmModalPayload {
  title: string;
  text: string;
  msgId: string;
}

interface GuideChatbotState {
  ownerUserId: string | null;
  isOpen: boolean;
  input: string;
  messages: GuideMessage[];
  selectedDbResume: SavedResume | null;
  savedPayloadIds: string[];
  confirmModalPayload: ConfirmModalPayload | null;
  toast: {
    message: string;
    type: ToastType;
  } | null;

  setOwnerUserId: (userId: string | null) => void;
  setIsOpen: (value: boolean) => void;
  setInput: (value: string) => void;
  setSelectedDbResume: (resume: SavedResume | null) => void;
  setConfirmModalPayload: (payload: ConfirmModalPayload | null) => void;
  setToast: (toast: { message: string; type: ToastType } | null) => void;

  addMessage: (message: GuideMessage) => void;
  setMessages: (messages: GuideMessage[]) => void;
  removeMessageById: (id: string) => void;
  removeLoadingMessages: () => void;
  markPayloadSaved: (msgId: string) => void;
  resetChat: () => void;
}

const initialMessages: GuideMessage[] = [
  {
    id: "1",
    type: "bot",
    content:
      "안녕하세요! AIWORK 수석 어드바이저 사자개입니다.\n\n플랫폼 사용법, 취업 트렌드, 직무 고민 등 무엇이든 물어보세요. 실시간 웹 검색으로 2026년 최신 데이터를 기반으로 답변드립니다.",
  },
];

export const useGuideChatbotStore = create<GuideChatbotState>()(
  persist(
    (set) => ({
      ownerUserId: null,
      isOpen: false,
      input: "",
      messages: initialMessages,
      selectedDbResume: null,
      savedPayloadIds: [],
      confirmModalPayload: null,
      toast: null,

      setOwnerUserId: (userId) => set({ ownerUserId: userId }),
      setIsOpen: (value) => set({ isOpen: value }),
      setInput: (value) => set({ input: value }),
      setSelectedDbResume: (resume) => set({ selectedDbResume: resume }),
      setConfirmModalPayload: (payload) =>
        set({ confirmModalPayload: payload }),
      setToast: (toast) => set({ toast }),

      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),

      setMessages: (messages) => set({ messages }),

      removeMessageById: (id) =>
        set((state) => ({
          messages: state.messages.filter((msg) => msg.id !== id),
        })),

      removeLoadingMessages: () =>
        set((state) => ({
          messages: state.messages.filter(
            (msg) => !msg.id.endsWith("_loading"),
          ),
        })),

      markPayloadSaved: (msgId) =>
        set((state) => ({
          savedPayloadIds: state.savedPayloadIds.includes(msgId)
            ? state.savedPayloadIds
            : [...state.savedPayloadIds, msgId],
        })),

      resetChat: () =>
        set({
          ownerUserId: null,
          isOpen: false,
          input: "",
          messages: initialMessages,
          selectedDbResume: null,
          savedPayloadIds: [],
          confirmModalPayload: null,
          toast: null,
        }),
    }),
    {
      name: "guide-chatbot-storage",
      partialize: (state) => ({
        ownerUserId: state.ownerUserId,
        isOpen: state.isOpen,
        input: state.input,
        messages: state.messages,
        selectedDbResume: state.selectedDbResume,
        savedPayloadIds: state.savedPayloadIds,
        confirmModalPayload: state.confirmModalPayload,
        toast: state.toast,
      }),
    },
  ),
);
