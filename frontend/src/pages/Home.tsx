import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { GuideChatbot } from '../components/chat/GuideChatbot';
import { Header } from '../components/common/Header';
import { InterviewSetupModal } from '../components/interview/InterviewSetupModal';
import { JobCards } from '../components/home/JobCards';
import { NewsFeed } from '../components/home/NewsFeed';
import { MemoBoard } from '../components/home/MemoBoard';
import { Search, FileText, MessageCircle } from 'lucide-react';
import './Home.scss';

export const Home = () => {
  const { isAuthenticated, user, clearAuth } = useAuthStore();
  const navigate = useNavigate();
  const [isSetupModalOpen, setIsSetupModalOpen] = useState(false);
  
  const [selectedPortal, setSelectedPortal] = useState('사람인');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [activeTab, setActiveTab] = useState<'jobs' | 'news' | 'memos'>('jobs');

  const handleSearch = () => {
    if (!searchKeyword.trim()) {
      alert('검색어를 입력해주세요.');
      return;
    }
    
    let url = '';
    if (selectedPortal === '사람인') {
      url = `https://www.saramin.co.kr/zf_user/search?searchword=${encodeURIComponent(searchKeyword)}`;
    } else if (selectedPortal === '잡코리아') {
      url = `https://www.jobkorea.co.kr/Search/?stext=${encodeURIComponent(searchKeyword)}`;
    } else if (selectedPortal === '워크넷') {
      url = `https://www.work.go.kr/empInfo/empInfoSrch/list/dtlEmpSrchList.do?keyword=${encodeURIComponent(searchKeyword)}`;
    }
    
    if (url) window.open(url, '_blank');
  };

  const handleStartInterview = () => {
    if (!isAuthenticated) {
      alert('로그인이 필요합니다.');
      navigate('/auth');
      return;
    }
    setIsSetupModalOpen(true);
  };

  return (
    <div className="home-layout">
      <Header />
      
      <main className="dashboard-container">
        <div className="dashboard-left">
          <div className="dashboard-card search-card">
            <h2>당신의 커리어를 <span className="highlight">가속화</span>할 기회</h2>
            <div className="search-bar">
              <select className="search-select" value={selectedPortal} onChange={(e) => setSelectedPortal(e.target.value)}>
                <option value="사람인">사람인</option>
                <option value="잡코리아">잡코리아</option>
                <option value="워크넷">워크넷</option>
              </select>
              <div className="search-input-wrapper">
                <Search size={18} color="#999" />
                <input 
                  type="text" 
                  placeholder="직무, 기업명, 키워드로 검색해보세요" 
                  value={searchKeyword}
                  onChange={(e) => setSearchKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                />
              </div>
              <button className="search-btn" onClick={handleSearch}>검색</button>
            </div>
          </div>

          <div className="dashboard-card resume-card">
            <FileText size={32} color="#ccc" className="resume-icon" />
            <h3>스마트 이력서 분석</h3>
            <p>이력서를 업로드하면 AI가 장단점을 분석하고 맞춤형 면접을 준비해 줍니다.</p>
            <div className="progress-dots">
              <span className="dot active"></span>
              <span className="dot"></span>
            </div>
          </div>

          <div className="dashboard-card tabs-card">
            <div className="tabs-header">
              <button className={`tab-btn ${activeTab === 'jobs' ? 'active' : ''}`} onClick={() => setActiveTab('jobs')}>추천 채용</button>
              <button className={`tab-btn ${activeTab === 'news' ? 'active' : ''}`} onClick={() => setActiveTab('news')}>
                {user?.job_role ? `${user.job_role} 트렌드` : '인사이트'}
              </button>
              <button className={`tab-btn ${activeTab === 'memos' ? 'active' : ''}`} onClick={() => setActiveTab('memos')}>게시판</button>
            </div>
            <div className="tabs-content" style={{ padding: '24px 0 0 0' }}>
              {activeTab === 'jobs' && <JobCards jobRole={user?.job_role} />}
              {activeTab === 'news' && <NewsFeed jobRole={user?.job_role} />}
              {activeTab === 'memos' && <MemoBoard />}
            </div>
          </div>
        </div>

        <div className="dashboard-right">
          <div className="dashboard-card profile-card" style={!isAuthenticated ? { alignItems: 'center', textAlign: 'center' } : {}}>
            {isAuthenticated ? (
              <>
                <div className="profile-header">
                  <div className="avatar">
                    {user?.profile_image_url ? (
                      <img src={user.profile_image_url} alt="Profile" />
                    ) : (
                      <div className="avatar-placeholder">🦁</div>
                    )}
                    <span className="online-dot"></span>
                  </div>
                  <div className="profile-info">
                    <div className="name-row">
                      <span className="name">{user?.name}님</span>
                      <span className={`tier-badge ${user?.tier || 'normal'}`}>
                        {(user?.tier || 'NORMAL').toUpperCase()}
                      </span>
                    </div>
                    <span className="email">{user?.email}</span>
                  </div>
                </div>
                
                <div className="profile-actions">
                  <button className="action-btn" onClick={() => navigate('/mypage')}>
                    내 면접 기록
                  </button>
                  <button className="action-btn" onClick={() => navigate('/my_info')}>
                    계정 설정
                  </button>
                  <button className="action-btn logout-btn" onClick={() => { clearAuth(); navigate('/auth'); }} style={{ color: '#ef4444' }}>
                    로그아웃
                  </button>
                </div>

                {user?.role === 'admin' && (
                  <button 
                    className="start-interview-btn admin-btn" 
                    onClick={() => navigate('/admin')}
                    style={{ background: '#333', marginTop: '10px' }}
                  >
                    관리자 대시보드
                  </button>
                )}
                <button className="start-interview-btn" onClick={handleStartInterview} style={user?.role === 'admin' ? { marginTop: '10px' } : {}}>
                  AI 모의 면접 시작하기
                </button>
              </>
            ) : (
              <div className="auth-prompt-container" style={{ width: '100%', padding: '10px 0' }}>
                <p style={{ fontSize: '15px', fontWeight: 600, color: '#222', marginBottom: '20px' }}>
                  AIWORK를 더 안전하고 편리하게 이용하세요
                </p>
                <button 
                  onClick={() => navigate('/auth')}
                  style={{ 
                    width: '100%', padding: '14px', background: '#0176f7', color: '#fff', 
                    border: 'none', borderRadius: '8px', fontSize: '16px', fontWeight: 700, 
                    cursor: 'pointer', marginBottom: '16px', transition: 'background 0.2s'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.background = '#0062d1'}
                  onMouseOut={(e) => e.currentTarget.style.background = '#0176f7'}
                >
                  AIWORK 로그인
                </button>
                <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', fontSize: '13px', color: '#666' }}>
                  <span style={{ cursor: 'pointer' }} onClick={() => navigate('/auth?mode=find')}>아이디/비밀번호 찾기</span>
                  <span style={{ color: '#ddd' }}>|</span>
                  <span style={{ cursor: 'pointer' }} onClick={() => navigate('/auth?mode=signup')}>회원가입</span>
                </div>
              </div>
            )}
          </div>
          
          <div className="dashboard-card dark-card" style={{cursor: 'pointer'}} onClick={() => window.open('https://github.com/SKN23-3rd-1TEAM', '_blank')}>
            <div className="card-icon">🐙</div>
            <div className="card-content">
              <h4>Project Repository</h4>
              <p>오픈소스 코드와 개발 문서를 확인하세요. SKN 1조 팀 프로젝트입니다.</p>
            </div>
          </div>

          <div className="dashboard-card blue-card" style={{cursor: 'pointer'}} onClick={() => alert('Discord 봇 초대 링크로 이동합니다.')}>
            <div className="card-icon"><MessageCircle size={24} color="#fff" fill="#fff" /></div>
            <div className="card-content">
              <h4>Discord 봇 추가</h4>
              <p>디스코드 환경에서도 AI 사자개 챗봇의 조언을 실시간으로 제공받으세요.</p>
            </div>
          </div>
        </div>
      </main>

      <GuideChatbot />

      {isSetupModalOpen && (
        <InterviewSetupModal onClose={() => setIsSetupModalOpen(false)} />
      )}
    </div>
  );
};