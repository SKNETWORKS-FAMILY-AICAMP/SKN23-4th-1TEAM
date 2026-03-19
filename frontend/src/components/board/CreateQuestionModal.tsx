import { useState, useEffect } from 'react';
import { X, Sparkles, Loader2, AlertCircle, CheckCircle, Info } from 'lucide-react';
import { boardApi } from '../../api/boardApi';

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

type ToastType = 'success' | 'error' | 'warning';

interface ToastState {
  message: string;
  type: ToastType;
}

export const CreateQuestionModal = ({ onClose, onSuccess }: Props) => {
  const [rawContent, setRawContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [rejectedContent, setRejectedContent] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false); // 확인 모달 상태 추가

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        setToast(null);
        if (toast.type === 'success') {
          onSuccess();
          onClose();
        }
      }, 2500);
      return () => clearTimeout(timer);
    }
  }, [toast, onClose, onSuccess]);

  const showToast = (message: string, type: ToastType) => {
    setToast({ message, type });
  };

  const handlePreSubmit = () => {
    if (rawContent.trim().length < 5) {
      showToast("질문 내용을 조금 더 자세히 적어주세요.", "warning");
      return;
    }

    if (rawContent === rejectedContent) {
      showToast("이미 반려된 내용입니다. 텍스트를 수정한 후 다시 시도해주세요.", "warning");
      return;
    }

    setShowConfirm(true);
  };

  const handleSubmit = async () => {
    setShowConfirm(false);
    setIsSubmitting(true);
    
    try {
      await boardApi.createQuestion(rawContent);
      showToast("AI가 질문을 다듬어 성공적으로 등록했습니다!", "success");
    } catch (error: any) {
      setRejectedContent(rawContent);

      if (error.response?.status === 409) {
        showToast("이미 게시판에 비슷한 내용의 질문이 등록되어 있습니다! 다른 질문을 올려보세요.", "warning");
      } else if (error.response?.status === 422) {
        const detail = error.response.data.detail;
        if (detail === "INVALID_CONTENT") {
          showToast("면접과 관련 없는 내용이나 장난스러운 글은 등록할 수 없어요.", "error");
        } else if (detail === "TECHNICAL_CONTENT") {
          showToast("인성면접에 올바르지 않은 질문입니다. (기술 면접 질문 감지)", "error");
        } else {
          showToast("질문 등록에 실패했습니다.", "error");
        }
      } else {
        showToast("서버와 통신 중 오류가 발생했습니다.", "error");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const getToastIcon = (type: ToastType) => {
    switch (type) {
      case 'success': return <CheckCircle size={20} />;
      case 'warning': return <Info size={20} />;
      case 'error': return <AlertCircle size={20} />;
    }
  };

  return (
    <div className="board-modal-overlay" onClick={onClose}>
      
      {toast && (
        <div className={`toast-alert ${toast.type}`}>
          {getToastIcon(toast.type)}
          <span className="toast-message">{toast.message}</span>
        </div>
      )}

      <div className="board-modal-content create-modal-content" onClick={e => e.stopPropagation()} style={{ position: 'relative' }}>
        <div className="modal-header">
          <h2>새 면접 질문 등록하기</h2>
          <button className="btn-close" onClick={onClose} disabled={isSubmitting}><X size={24} /></button>
        </div>

        <div className="modal-body">
          <span className="section-label">어떤 인성 면접 질문을 받으셨나요?</span>
          <p className="guide-text">
            받았던 질문이나 상황을 편하게 적어주세요. <br/>
            AI가 내용을 분석하여 기술 질문 및 부적절한 내용을 필터링하고, <strong>깔끔한 면접 질문 형태로 자동 교정</strong>하여 등록해 드립니다.
          </p>

          <textarea
            className="question-textarea"
            placeholder="예: 저번 프로젝트에서 팀원이랑 싸웠을 때 어떻게 대처했냐고 물어봤어요."
            value={rawContent}
            onChange={e => {
              setRawContent(e.target.value);
              if (rejectedContent && e.target.value !== rejectedContent) {
                setRejectedContent(null);
              }
            }}
            disabled={isSubmitting}
          />
        </div>

        <div className="modal-footer modal-footer-actions">
          <button className="btn-cancel" onClick={onClose} disabled={isSubmitting}>
            취소
          </button>
          <button
            className="btn-submit"
            onClick={handlePreSubmit}
            disabled={isSubmitting || rawContent.trim().length < 5 || rawContent === rejectedContent}
          >
            {isSubmitting ? <Loader2 className="spinner" size={18} /> : <Sparkles size={18} />}
            {isSubmitting ? 'AI가 질문 교정 중...' : 'AI 교정 후 등록'}
          </button>
        </div>

        {showConfirm && (
          <div className="confirm-modal-overlay">
            <div className="confirm-modal-content">
              <div className="confirm-icon">
                <Sparkles size={28} />
              </div>
              <h3>질문을 등록하시겠습니까?</h3>
              <p>AI가 작성하신 내용을 분석하고<br/>깔끔한 면접 질문으로 교정하여 게시판에 등록합니다.</p>
              <div className="confirm-actions">
                <button className="btn-cancel" onClick={() => setShowConfirm(false)}>취소</button>
                <button className="btn-proceed" onClick={handleSubmit}>진행하기</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};