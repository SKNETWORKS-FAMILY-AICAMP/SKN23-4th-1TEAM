import { useEffect, useState } from 'react';
import { boardApi } from '../../api/boardApi';
import { X, Heart, Send, Trash2 } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

interface Answer {
  id: number;
  content: string;
  author_name: string;
  user_id: number;
  like_count: number;
  created_at: string;
  is_liked_by_me?: boolean;
}

interface Props {
  questionId: number;
  onClose: () => void;
}

export const QuestionDetailModal = ({ questionId, onClose }: Props) => {
  const { user } = useAuthStore();
  const [questionContent, setQuestionContent] = useState('');
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [myAnswer, setMyAnswer] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchDetail = async () => {
    try {
      const data = await boardApi.getQuestionDetail(questionId);
      setQuestionContent(data.question.content);
      setAnswers(data.answers || []);
    } catch (error) {
      console.error("상세 로드 실패:", error);
    }
  };

  useEffect(() => {
    fetchDetail();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questionId]);

  const handleLike = async (answerId: number) => {
    try {
      await boardApi.toggleLike(answerId);
      fetchDetail();
    } catch (error) {
      console.error("좋아요 처리 실패:", error);
    }
  };

  const handleDelete = async (answerId: number) => {
    if (!window.confirm("내가 작성한 답변을 정말 삭제하시겠습니까?")) return;
    try {
      await boardApi.deleteAnswer(answerId);
      alert("삭제되었습니다.");
      fetchDetail();
    } catch (error) {
      console.error("삭제 실패:", error);
      alert("삭제 중 오류가 발생했습니다.");
    }
  };

  const handleSubmit = async () => {
    if (!myAnswer.trim() || myAnswer.length < 5) {
      alert("답변은 5자 이상 입력해주세요.");
      return;
    }
    if (!user?.id || !user?.name) {
      alert("로그인 정보가 필요합니다.");
      return;
    }

    setIsSubmitting(true);
    try {
      await boardApi.submitAnswer(questionId, myAnswer, Number(user.id), user.name);
      setMyAnswer('');
      fetchDetail();
    } catch (error) {
      console.error("답변 등록 실패:", error);
      alert("답변 등록 중 오류가 발생했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const topAnswer = answers.length > 0
    ? [...answers].sort((a, b) => b.like_count - a.like_count)[0]
    : null;

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('ko-KR', {
      year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    });
  };

  return (
    <div className="board-modal-overlay" onClick={onClose}>
      <div className="board-modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Q. {questionContent}</h2>
          <button className="btn-close" onClick={onClose}><X size={24} /></button>
        </div>

        <div className="modal-body">
          {topAnswer && topAnswer.like_count > 0 && (
            <div className="top-answer-section">
              <span className="section-label highlight">좋아요 상위 답변</span>
              <div className="answer-card top-card">
                <div className="author-info">
                  <span className="author-name">{topAnswer.author_name}</span>
                  <span className="date">{formatDate(topAnswer.created_at)}</span>
                </div>
                <p className="content">{topAnswer.content}</p>
                <button
                  className={`btn-like ${topAnswer.is_liked_by_me ? 'active' : ''}`}
                  onClick={() => handleLike(topAnswer.id)}
                >
                  <Heart size={14} fill={topAnswer.is_liked_by_me ? "currentColor" : "none"} />
                  좋아요 {topAnswer.like_count}
                </button>
              </div>
            </div>
          )}

          <div className="all-answers-section">
            <span className="section-label">전체 답변 ({answers.length})</span>
            {answers.map(ans => (
              <div key={ans.id} className="answer-card" style={{ position: 'relative' }}>

                {user?.id && Number(user.id) === ans.user_id && (
                  <button
                    onClick={() => handleDelete(ans.id)}
                    style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px' }}
                  >
                    <Trash2 size={14} /> 삭제
                  </button>
                )}

                <div className="author-info">
                  <span className="author-name">{ans.author_name}</span>
                  <span className="date">{formatDate(ans.created_at)}</span>
                </div>
                <p className="content">{ans.content}</p>
                <button
                  className={`btn-like ${ans.is_liked_by_me ? 'active' : ''}`}
                  onClick={() => handleLike(ans.id)}
                >
                  <Heart size={14} fill={ans.is_liked_by_me ? "currentColor" : "none"} />
                  좋아요 {ans.like_count}
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="modal-footer">
          <div className="input-wrapper">
            <textarea
              placeholder="이 질문에 대한 경험이나 생각을 자유롭게 남겨보세요. (최소 5자)"
              value={myAnswer}
              onChange={e => setMyAnswer(e.target.value)}
              disabled={isSubmitting}
            />
            <button
              className="btn-submit-answer"
              onClick={handleSubmit}
              disabled={isSubmitting || myAnswer.trim().length < 5}
            >
              <Send size={18} /> 보내기
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};