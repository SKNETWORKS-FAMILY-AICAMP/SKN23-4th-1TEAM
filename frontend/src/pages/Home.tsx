import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, MessageCircle, ChevronLeft, ChevronRight, Github } from "lucide-react";
import { useAuthStore } from "../store/authStore";
import { GuideChatbot } from "../components/chat/GuideChatbot";
import { CustomAlert } from "../components/common/CustomAlert";
import { Header } from "../components/common/Header";
import { InterviewSetupModal } from "../components/interview/InterviewSetupModal";
import { JobCards } from "../components/home/JobCards";
import { NewsFeed } from "../components/home/NewsFeed";
import { MemoBoard } from "../components/home/MemoBoard";
import { resumeApi } from "../api/resumeApi";
import { homeApi } from "../api/homeApi";
import { authApi } from "../api/authApi";
import "./Home.scss";

type TabKey = "jobs" | "news" | "memos";

export const Home = () => {
  // 💡 openLoginModal 전역 함수 가져오기
  const { isAuthenticated, user, clearAuth, setUser, openLoginModal } = useAuthStore();
  const navigate = useNavigate();

  const [isSetupModalOpen, setIsSetupModalOpen] = useState(false);
  const [selectedPortal, setSelectedPortal] = useState("사람인");
  const [searchKeyword, setSearchKeyword] = useState("");
  const [activeTab, setActiveTab] = useState<TabKey>("jobs");
  const [resumeSlideIndex, setResumeSlideIndex] = useState(0);

  const [latestJobRole, setLatestJobRole] = useState<string | undefined>(undefined);
  const [isResumeChecked, setIsResumeChecked] = useState(false);

  const [isEditingGithub, setIsEditingGithub] = useState(false);
  const [githubInput, setGithubInput] = useState(user?.github_url || "");
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  const resumeSlides = [
    {
      image: "/images/home/guide-bot.svg",
      title: "AIWORK 가이드 봇",
      description: "채팅으로 요청하면 필요한 기능을 바로 실행해주고, 상황에 맞는 다음 작업까지 에이전트처럼 이어서 처리해줍니다.",
      badge: "Agent Mode",
    },
    {
      image: "/images/home/resume-analysis.svg",
      title: "스마트 이력서 분석",
      description: "이력서를 업로드하면 AI가 장단점을 분석하고 맞춤형 면접을 준비해 줍니다.",
      badge: "Resume Insight",
    },
    {
      image: "/images/home/auto-flow.svg",
      title: "맞춤 질문 자동 생성",
      description: "지원 직무와 이력서 내용을 바탕으로 실제 면접 같은 질문을 자동으로 구성합니다.",
      badge: "Auto Flow",
    },
  ];

  const currentSlide = resumeSlides[resumeSlideIndex];

  const handleResumeSlide = (direction: "prev" | "next") => {
    setResumeSlideIndex((prev) => {
      if (direction === "prev") {
        return prev === 0 ? resumeSlides.length - 1 : prev - 1;
      }
      return prev === resumeSlides.length - 1 ? 0 : prev + 1;
    });
  };

  const handleGithubSave = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!user?.id) return;
    if (!githubInput.trim()) {
      alert("주소를 입력해주세요.");
      return;
    }
    
    let formattedUrl = githubInput.trim();
    if (!/^https?:\/\//i.test(formattedUrl)) {
      formattedUrl = `https://${formattedUrl}`;
    }

    try {
      await homeApi.updateUserProfile(user.id, { github_url: formattedUrl });
      setUser({ ...user, github_url: formattedUrl });
      alert("깃허브 주소가 저장되었습니다.");
      setIsEditingGithub(false);
    } catch (error) {
      console.error(error);
      alert("저장에 실패했습니다.");
    }
  };

  const executeLogout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error(error);
    } finally {
      setShowLogoutConfirm(false);
      clearAuth();
      navigate("/auth");
    }
  };

  useEffect(() => {
    const timer = window.setInterval(() => {
      setResumeSlideIndex((prev) =>
        prev === resumeSlides.length - 1 ? 0 : prev + 1,
      );
    }, 5000);

    return () => window.clearInterval(timer);
  }, [resumeSlides.length]);

  useEffect(() => {
    const fetchLatestResumeRole = async () => {
      if (!user?.id) {
        setIsResumeChecked(true);
        return;
      }
      try {
        const data = await resumeApi.listResumes(Number(user.id));
        if (data && data.items && data.items.length > 0) {
          const latestResume = data.items.reduce((prev: any, current: any) => 
            prev.id > current.id ? prev : current
          );
          if (latestResume.job_role) {
            setLatestJobRole(latestResume.job_role);
          }
        }
      } catch (error) {
        console.error(error);
      } finally {
        setIsResumeChecked(true);
      }
    };
    fetchLatestResumeRole();
  }, [user?.id]);

  const handleSearch = () => {
    if (!searchKeyword.trim()) {
      alert("검색어를 입력해주세요.");
      return;
    }
    let url = "";
    if (selectedPortal === "사람인") {
      url = `https://www.saramin.co.kr/zf_user/search?searchword=${encodeURIComponent(searchKeyword)}`;
    } else if (selectedPortal === "잡코리아") {
      url = `https://www.jobkorea.co.kr/Search/?stext=${encodeURIComponent(searchKeyword)}`;
    } else if (selectedPortal === "워크넷") {
      url = `https://www.work.go.kr/empInfo/empInfoSrch/list/dtlEmpSrchList.do?keyword=${encodeURIComponent(searchKeyword)}`;
    }
    if (url) window.open(url, "_blank");
  };

  const handleStartInterview = () => {
    if (!isAuthenticated) {
      openLoginModal(); // 💡 전역 모달 열기 호출
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
              <select
                className="search-select"
                value={selectedPortal}
                onChange={(e) => setSelectedPortal(e.target.value)}
              >
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
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
              </div>
              <button className="search-btn" onClick={handleSearch}>검색</button>
            </div>
          </div>

          <div className="dashboard-card resume-card">
            <button type="button" className="resume-nav-btn side left" onClick={() => handleResumeSlide("prev")} aria-label="이전 카드"><ChevronLeft size={18} /></button>
            <button type="button" className="resume-nav-btn side right" onClick={() => handleResumeSlide("next")} aria-label="다음 카드"><ChevronRight size={18} /></button>
            <div className="resume-visual-glow"></div>
            <div className="resume-card-shell">
              <div className="resume-illustration"><img src={currentSlide.image} alt={currentSlide.title} /></div>
              <div className="resume-copy">
                <span className="resume-badge">{currentSlide.badge}</span>
                <h3>{currentSlide.title}</h3>
                <p>{currentSlide.description}</p>
              </div>
              <div className="resume-status-spacer"></div>
            </div>
            <div className="progress-dots">
              {resumeSlides.map((_, index) => (
                <span key={index} className={`dot ${resumeSlideIndex === index ? "active" : ""}`}></span>
              ))}
            </div>
          </div>

          <div className="dashboard-card tabs-card">
            <div className="tabs-header">
              <button className={`tab-btn ${activeTab === "jobs" ? "active" : ""}`} onClick={() => setActiveTab("jobs")}>추천 채용</button>
              <button className={`tab-btn ${activeTab === "news" ? "active" : ""}`} onClick={() => setActiveTab("news")}>{latestJobRole ? `${latestJobRole} 트렌드` : "인사이트"}</button>
              <button className={`tab-btn ${activeTab === "memos" ? "active" : ""}`} onClick={() => setActiveTab("memos")}>메모장</button>
            </div>
            <div className="tabs-content">
              <div className={`tab-panel ${activeTab === "jobs" ? "active" : ""}`}><JobCards jobRole={latestJobRole} /></div>
              <div className={`tab-panel ${activeTab === "news" ? "active" : ""}`}>
                {isResumeChecked ? <NewsFeed jobRole={latestJobRole} /> : <div style={{ textAlign: "center", padding: "40px 0", color: "#666" }}>준비 중...</div>}
              </div>
              <div className={`tab-panel ${activeTab === "memos" ? "active" : ""}`}><MemoBoard /></div>
            </div>
          </div>
        </div>

        <div className="dashboard-right">
          <div className={`dashboard-card profile-card ${isAuthenticated ? "member-card" : "guest-card"}`} style={!isAuthenticated ? { alignItems: "center", textAlign: "center" } : {}}>
            {isAuthenticated ? (
              <>
                <div className="profile-header">
                  <div className="avatar">
                    {user?.profile_image_url ? (
                      <img src={user.profile_image_url} alt="Profile" />
                    ) : (
                      <img src="/images/default-profile.png" alt="Default Profile" /> 
                    )}
                    <span className="online-dot"></span>
                  </div>
                  <div className="profile-info">
                    <div className="name-row">
                      <span className="name">{user?.name}님</span>
                      <span className={`tier-badge ${user?.tier || "normal"}`}>{(user?.tier || "NORMAL").toUpperCase()}</span>
                    </div>
                    <span className="email">{user?.email}</span>
                  </div>
                </div>
                <div className="profile-actions">
                  <button className="action-btn" onClick={() => navigate("/mypage")}>내 면접 기록</button>
                  <button className="action-btn" onClick={() => navigate("/my_info")}>계정 설정</button>
                  <button className="action-btn logout-btn" onClick={() => setShowLogoutConfirm(true)} style={{ color: "#ef4444" }}>로그아웃</button>
                </div>
                <button className="start-interview-btn" onClick={handleStartInterview}>AI 모의 면접 시작하기</button>
              </>
            ) : (
              <div className="auth-prompt-container" style={{ width: "100%", padding: "10px 0" }}>
                <p style={{ fontSize: "15px", fontWeight: 600, color: "#222", marginBottom: "20px" }}>AIWORK를 더 편리하게 이용해보세요</p>
                <button onClick={() => navigate("/auth")} style={{ width: "100%", padding: "14px", background: "#0176f7", color: "#fff", border: "none", borderRadius: "8px", fontSize: "16px", fontWeight: 700, cursor: "pointer", marginBottom: "16px" }}>AIWORK 로그인</button>
                <div style={{ display: "flex", justifyContent: "center", gap: "12px", fontSize: "13px", color: "#666" }}>
                  <span style={{ cursor: "pointer" }} onClick={() => navigate("/auth?mode=find")}>아이디/비밀번호 찾기</span>
                  <span style={{ color: "#ddd" }}>|</span>
                  <span style={{ cursor: "pointer" }} onClick={() => navigate("/auth?mode=signup")}>회원가입</span>
                </div>
              </div>
            )}
          </div>

          <div
              className="dashboard-card dark-card"
              style={{ cursor: user?.github_url && !isEditingGithub ? "pointer" : "default" }}
              onClick={() => {
                if (user?.github_url && !isEditingGithub) {
                  window.open(user.github_url, "_blank");
                }
              }}
            >
            <div className="card-icon"><Github size={24} color="#fff" /></div>
            <div className="card-content">
              <h4>My GitHub Repository</h4>
              {isEditingGithub ? (
                <div className="github-input-row" style={{ display: "flex", gap: "8px", marginTop: "8px" }} onClick={(e) => e.stopPropagation()}>
                  <input type="text" value={githubInput} onChange={(e) => setGithubInput(e.target.value)} placeholder="https://github.com/아이디" style={{ flex: 1, padding: "8px", borderRadius: "6px", border: "none", color: "#000", fontSize: "13px" }} />
                  <button onClick={handleGithubSave} style={{ padding: "8px 12px", background: "#0176f7", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontWeight: 600 }}>저장</button>
                </div>
              ) : (
                <>
                  <p style={{ marginBottom: "8px" }}>{user?.github_url ? "등록된 깃허브로 이동하여 포트폴리오를 확인합니다." : "아직 깃허브가 연결되지 않았습니다."}</p>
                  <button onClick={(e) => { e.stopPropagation(); setIsEditingGithub(true); }} style={{ padding: "6px 12px", background: "rgba(255,255,255,0.2)", border: "none", color: "#fff", borderRadius: "4px", cursor: "pointer", fontSize: "12px", fontWeight: 600 }}>{user?.github_url ? "수정하기" : "URL 등록하기"}</button>
                </>
              )}
            </div>
          </div>

          <div className="dashboard-card blue-card" style={{ cursor: "pointer" }} onClick={() => window.open("https://discord.com/oauth2/authorize?client_id=1465155158022426675&permissions=4279296&integration_type=0&scope=bot", "_blank")}>
            <div className="card-icon"><MessageCircle size={24} color="#fff" fill="#fff" /></div>
            <div className="card-content">
              <h4>Discord 봇 추가</h4>
              <p>디스코드 환경에서도 AI 사자개가 채용 조언을 실시간으로 제공해줍니다.</p>
            </div>
          </div>
        </div>
      </main>
      <GuideChatbot />
      <CustomAlert
        open={showLogoutConfirm}
        title={"로그아웃 하시겠습니까?"}
        message={"로그아웃 후 로그인 화면으로 이동합니다."}
        confirmText={"확인"}
        cancelText={"취소"}
        onConfirm={executeLogout}
        onCancel={() => setShowLogoutConfirm(false)}
      />
      {isSetupModalOpen && <InterviewSetupModal onClose={() => setIsSetupModalOpen(false)} />}
    </div>
  );
};
