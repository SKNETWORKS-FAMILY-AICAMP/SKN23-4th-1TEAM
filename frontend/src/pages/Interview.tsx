import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInferStore } from '../store/inferStore';
import { ROUTES } from '../constants/routes';

import { TextInterview } from '../components/interview/TextInterview';
import { VoiceInterview } from '../components/interview/VoiceInterview';
import { InterviewSetupModal } from '../components/interview/InterviewSetupModal';
import { CustomModal } from '../components/common/CustomModal';
import './Interview.scss';

export const Interview = () => {
  const { jobRole, difficulty, method, persona, questionCount } = useInferStore();
  const navigate = useNavigate();

  const [isSetupModalOpen, setIsSetupModalOpen] = useState(false);
  const [showEndModal, setShowEndModal] = useState(false);

  // 직무/난이도 세팅이 안 되어 있으면 무조건 설정 모달부터 띄움
  useEffect(() => {
    if (!jobRole || !difficulty) {
      setIsSetupModalOpen(true);
    }
  }, [jobRole, difficulty]);

  const confirmEndInterview = () => {
    setShowEndModal(false);
    navigate(ROUTES.HOME);
  };

  return (
    <div className="interview-page-container">
      {/* 1. 텍스트/음성 공통 적용: 개쩌는 통합 헤더 */}
      <header className="unified-interview-header">
        <div className="header-left">
          <div className="ai-icon-box">👾</div>
          <div className="title-area">
            <h1>AI 면접관 <span className="badge-persona">{persona}</span></h1>
            <p className="meta-info">
              {jobRole} · 난이도 {difficulty} · 총 {questionCount || 5}문항
            </p>
          </div>
        </div>
        <button className="btn-end-interview" onClick={() => setShowEndModal(true)}>
          면접 종료
        </button>
      </header>

      {/* 2. 모드에 따른 컴포넌트 완벽 격리 (권한 꼬임 원천 차단) */}
      <main className="interview-main-content">
        {!isSetupModalOpen && (
          method === 'text' 
            ? <TextInterview /> 
            : <VoiceInterview /> // 추후 음성 컴포넌트 작성
        )}
      </main>

      {/* 3. 모달 제어 */}
      {isSetupModalOpen && (
        <InterviewSetupModal onClose={() => setIsSetupModalOpen(false)} />
      )}

      {showEndModal && (
        <CustomModal 
          title="면접 종료"
          message={<>진행 중인 면접을 정말 종료하시겠습니까?<br/>지금까지의 내용은 저장되지 않을 수 있습니다.</>}
          onCancel={() => setShowEndModal(false)}
          onConfirm={confirmEndInterview}
        />
      )}
    </div>
  );
};