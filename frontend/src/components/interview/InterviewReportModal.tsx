import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInferStore } from '../../store/inferStore';
import { inferApi } from '../../api/inferApi';
import { Loader2, Download, Home, RotateCcw } from 'lucide-react';
import './InterviewReportModal.scss';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  score?: number;
}

interface Props {
  messages: ChatMessage[];
  onRestart: () => void;
}

export const InterviewReportModal = ({ messages, onRestart }: Props) => {
  const { jobRole, difficulty, experienceText } = useInferStore();
  const navigate = useNavigate();

  const [evaluation, setEvaluation] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // 1. 평균 점수 계산 (10점 만점 -> 100점 만점 환산)
  const userMessages = messages.filter(m => m.role === 'user' && m.score !== undefined);
  const avgScore = userMessages.length > 0
    ? userMessages.reduce((acc, m) => acc + (m.score || 0), 0) / userMessages.length
    : 0;
  const totalScore = Math.round((avgScore / 10) * 100);

  // 2. 컴포넌트 마운트 시 AI 평가 리포트 요청
  useEffect(() => {
    const fetchEvaluation = async () => {
      try {
        const res = await inferApi.getEvaluationReport({
          messages: messages,
          job_role: jobRole || "기본 직무",
          difficulty: difficulty || "중",
          resume_text: experienceText || null
        });   
        
        let rawEval = res.evaluation || "평가 생성 실패";
        rawEval = rawEval.replace(/\*\*[\d\.]+\s*\/\s*100점\*\*/g, `**${totalScore} / 100점**`);
        
        setEvaluation(rawEval);
      } catch (error) {
        console.error("평가 리포트 생성 실패:", error);
        setEvaluation("서버 통신 오류로 평가 리포트를 불러오지 못했습니다.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchEvaluation();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 3. TXT 다운로드 기능
  const handleDownload = () => {
    if (!evaluation) return;
    const element = document.createElement("a");
    const file = new Blob([evaluation], { type: 'text/plain;charset=utf-8' });
    element.href = URL.createObjectURL(file);
    element.download = "interview_report.txt";
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const handleGoHome = () => {
    navigate('/');
  };

  return (
    <div className="report-modal-overlay">
      <div className="report-modal-content">
        <h2>면접 결과 리포트</h2>

        {/* 점수 원형 UI */}
        <div className="score-circle-container">
          <div className="score-circle">
            <span className="score-number">{totalScore}</span>
            <span className="score-label">/ 100</span>
          </div>
        </div>

        {!experienceText && (
          <div className="warning-banner">
            이력서를 연동하지 않은 자율 면접이므로, 직무/이력서 매칭률 점수 및 평가는 제한될 수 있습니다.
          </div>
        )}

        {/* AI 평가 결과 영역 */}
        <div className="evaluation-box">
          {isLoading ? (
            <div className="loading-state">
              <Loader2 className="animate-spin" size={32} color="#0176f7" />
              <p>AI가 면접 내용을 꼼꼼하게 분석 중입니다...</p>
            </div>
          ) : (
            <div className="markdown-content">
              {/* React에서는 dangerouslySetInnerHTML 또는 줄바꿈 처리가 필요합니다 */}
              {evaluation?.split('\n').map((line, i) => (
                <span key={i}>
                  {line.replace(/\*\*(.*?)\*\*/g, '$1')} <br/>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* 하단 버튼 영역 */}
        <div className="action-buttons">
          <button 
            className="btn-download" 
            onClick={handleDownload} 
            disabled={isLoading || !evaluation}
          >
            <Download size={18} /> 결과 리포트 저장 (TXT)
          </button>
          
          <div className="bottom-row">
            <button className="btn-restart" onClick={onRestart}>
              <RotateCcw size={18} /> 다시 시작
            </button>
            <button className="btn-home" onClick={handleGoHome}>
              <Home size={18} /> 내 기록 보러가기
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};