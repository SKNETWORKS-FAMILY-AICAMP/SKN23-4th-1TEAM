import { useEffect, useState } from "react";
import { Header } from "../components/common/Header";
import { boardApi } from "../api/boardApi";
import { QuestionDetailModal } from "../components/board/QuestionDetailModal";
import { CreateQuestionModal } from "../components/board/CreateQuestionModal";
import { Trash2, AlertCircle, CheckCircle, Info, Trash } from "lucide-react";
import { useAuthStore } from "../store/authStore";
import "./Board.scss";
import { GuideChatbot } from "../components/chat/GuideChatbot";

interface Question {
  id: number;
  content: string;
  answer_count?: number;
}

type ToastType = "success" | "error" | "warning";

interface ToastState {
  message: string;
  type: ToastType;
}

export const BoardPage = () => {
  const { user } = useAuthStore();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedQuestionId, setSelectedQuestionId] = useState<number | null>(
    null,
  );
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const [toast, setToast] = useState<ToastState | null>(null);
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);

  const fetchQuestions = async () => {
    try {
      setLoading(true);
      const data = await boardApi.getQuestions();
      setQuestions(data.items || []);
    } catch (error) {
      console.error("질문 목록 로드 실패:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuestions();
  }, []);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 2500);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const showToast = (message: string, type: ToastType) => {
    setToast({ message, type });
  };

  const handleDeleteClick = (e: React.MouseEvent, questionId: number) => {
    e.stopPropagation();
    setDeleteTargetId(questionId);
  };

  const executeDelete = async () => {
    if (!deleteTargetId) return;

    try {
      await boardApi.deleteQuestion(deleteTargetId);
      showToast("질문이 성공적으로 삭제되었습니다.", "success");
      fetchQuestions();
    } catch (error: any) {
      if (error.response?.status === 403) {
        showToast("관리자 권한이 없습니다.", "error");
      } else {
        showToast("삭제 중 오류가 발생했습니다.", "error");
      }
    } finally {
      setDeleteTargetId(null);
    }
  };

  const getToastIcon = (type: ToastType) => {
    switch (type) {
      case "success":
        return <CheckCircle size={20} />;
      case "warning":
        return <Info size={20} />;
      case "error":
        return <AlertCircle size={20} />;
    }
  };

  return (
    <div className="board-page-layout">
      {toast && (
        <div className={`toast-alert ${toast.type}`}>
          {getToastIcon(toast.type)}
          <span className="toast-message">{toast.message}</span>
        </div>
      )}

      <Header />
      <main className="board-main">
        <div className="board-hero">
          <div className="hero-content">
            <h1 className="hero-title">인성면접 질문 둘러보기</h1>
            <p className="hero-subtitle">
              실제 면접에서 사용했던 표현, 고민 포인트, 답변 방식을 자유롭게
              공유해보세요.
            </p>
          </div>
          <button
            className="btn-create-question"
            onClick={() => setIsCreateModalOpen(true)}
          >
            새 질문 등록하기
          </button>
        </div>

        {loading ? (
          <div className="loading-state">데이터를 불러오는 중입니다...</div>
        ) : (
          <div className="questions-grid">
            {questions.map((q, idx) => (
              <div key={q.id} className="question-card">
                {user?.role === "admin" && (
                  <button
                    className="btn-admin-delete"
                    onClick={(e) => handleDeleteClick(e, q.id)}
                    title="관리자 권한으로 질문 삭제"
                  >
                    <Trash2 size={18} />
                  </button>
                )}

                <div className="card-top">
                  <span className="q-label">질문 {idx + 1}</span>
                  <h3
                    className={`q-content ${user?.role === "admin" ? "admin-padding" : ""}`}
                  >
                    {q.content}
                  </h3>
                </div>
                <div className="card-bottom">
                  <span className="answer-count">
                    답변 {q.answer_count || 0}개
                  </span>
                  <button
                    className="btn-view"
                    onClick={() => setSelectedQuestionId(q.id)}
                  >
                    답변 보기
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
      <GuideChatbot />
      {deleteTargetId && (
        <div className="confirm-modal-overlay">
          <div className="confirm-modal-content">
            <div className="confirm-icon">
              <Trash size={28} />
            </div>
            <h3>질문을 완전히 삭제할까요?</h3>
            <p>
              삭제된 질문과 모든 답변은 복구할 수 없습니다.
              <br />
              정말 삭제하시겠습니까?
            </p>
            <div className="confirm-actions">
              <button
                className="btn-cancel"
                onClick={() => setDeleteTargetId(null)}
              >
                취소
              </button>
              <button className="btn-proceed" onClick={executeDelete}>
                삭제하기
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedQuestionId && (
        <QuestionDetailModal
          questionId={selectedQuestionId}
          onClose={() => setSelectedQuestionId(null)}
        />
      )}

      {isCreateModalOpen && (
        <CreateQuestionModal
          onClose={() => setIsCreateModalOpen(false)}
          onSuccess={fetchQuestions}
        />
      )}
    </div>
  );
};
