import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInferStore } from '../store/inferStore';
import { axiosClient } from '../api/axiosClient';

import { TextInterview } from '../components/interview/TextInterview';
import { VoiceInterview } from '../components/interview/VoiceInterview';
import { InterviewSetupModal } from '../components/interview/InterviewSetupModal';
import './Interview.scss';

export const Interview = () => {
  const { jobRole, difficulty, method, persona, questionCount, clearInferSettings } = useInferStore();
  const navigate = useNavigate();

  const [isSetupModalOpen, setIsSetupModalOpen] = useState(true);
  const [showEndModal, setShowEndModal] = useState(false);

  useEffect(() => {
    // 페이지 진입 시 무조건 기존 세션 찌꺼기 날리고 초기화
    localStorage.removeItem('current_session_id');
    clearInferSettings();
    setIsSetupModalOpen(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const confirmEndInterview = async () => {
    try {
      const sessionId = localStorage.getItem('current_session_id'); 
      if (sessionId) {
        await axiosClient.put(`/api/interview/sessions/${sessionId}`, { 
          status: 'COMPLETED'
        });
        localStorage.removeItem('current_session_id'); 
      }
      setShowEndModal(false);
      clearInferSettings();
      navigate('/records');
    } catch (error) {
      console.error('면접 종료 처리 중 오류:', error);
      navigate('/');
    }
  };

  return (
    <div className="interview-page-container">
      <header className="unified-interview-header">
        <div className="header-left">
          <div className="ai-icon-box">👾</div>
          <div className="title-area">
            <h1>AI 면접관 <span className="badge-persona">{persona || '깐깐한 기술팀장'}</span></h1>
            <p className="meta-info">
              {jobRole || '기본 직무'} · 난이도 {difficulty || '중'} · 총 {questionCount || 5}문항
            </p>
          </div>
        </div>
        <button className="btn-end-interview" onClick={() => setShowEndModal(true)}>
          면접 종료 및 저장
        </button>
      </header>

      <main className="interview-main-content">
        {!isSetupModalOpen && (
          method === 'voice' 
            ? <VoiceInterview /> 
            : <TextInterview /> 
        )}
      </main>

      {isSetupModalOpen && (
        <InterviewSetupModal onClose={() => setIsSetupModalOpen(false)} />
      )}

      {showEndModal && (
        <div className="modal-overlay">
          <div className="custom-modal-content" style={{background: 'white', padding: '30px', borderRadius: '16px', maxWidth: '400px'}}>
            <h3 style={{marginTop: 0}}>면접 최종 종료</h3>
            <p style={{color: '#666', lineHeight: 1.5, marginBottom: '24px'}}>
              면접을 종료하시겠습니까?<br/>최종 제출 시 점수 평가가 진행됩니다.
            </p>
            <div style={{display: 'flex', flexDirection: 'column', gap: '10px'}}>
              <button 
                onClick={confirmEndInterview}
                style={{padding: '12px', background: '#ef4444', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer', color: 'white'}}
              >
                최종 제출하고 완전 종료
              </button>
              <button 
                onClick={() => setShowEndModal(false)}
                style={{padding: '12px', background: 'transparent', border: '1px solid #cbd5e1', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer', marginTop: '8px'}}
              >
                취소 (계속 진행)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};