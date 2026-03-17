import { useState, useRef, useEffect, Fragment } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Paperclip, ArrowUp, Database } from 'lucide-react';
import { useInferStore } from '../../store/inferStore';
import { inferApi } from '../../api/inferApi';
import { ROUTES } from '../../constants/routes';
import { homeApi } from '../../api/homeApi';
import { useAuthStore } from '../../store/authStore';
import { resumeApi } from '../../api/resumeApi';
import './GuideChatbot.scss';

interface Message {
  id: string;
  type: 'user' | 'bot';
  content: string;
  downloadContent?: string;
  downloadFilename?: string;
}

interface SavedResume {
  id: string;
  title: string;
}

interface Props {
  onOpenSetup?: () => void;
}

export const GuideChatbot = ({ onOpenSetup }: Props) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'bot',
      content: '안녕하세요! AIWORK 수석 어드바이저 사자개입니다.\n\n플랫폼 사용법, 취업 트렌드, 직무 고민 등 무엇이든 물어보세요. 실시간 웹 검색으로 2026년 최신 데이터를 기반으로 답변드립니다.',
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  
  const [showMentionMenu, setShowMentionMenu] = useState(false);
  const [selectedDbResume, setSelectedDbResume] = useState<SavedResume | null>(null);

  const [savedResumes, setSavedResumes] = useState<SavedResume[]>([]);

  const { user } = useAuthStore();

  useEffect(() => {
    const loadResumes = async () => {
      if (!user?.id) return;

      try {
        // homeApi 대신 검증된 resumeApi 사용
        const data = await resumeApi.listResumes(Number(user.id));
        
        if (data && data.items) {
          const formattedData = data.items.map((item) => ({
            id: item.id.toString(),
            title: item.title,
          }));
          setSavedResumes(formattedData);
        }
      } catch (error) {
        console.error('이력서 목록 로딩 실패:', error);
      }
    };

    if (isOpen) loadResumes();
  }, [isOpen, user?.id]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const navigate = useNavigate();
  const { setInferSettings, setResumeUsed } = useInferStore();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, selectedFile, selectedDbResume]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setSelectedDbResume(null); 
    }
  };

  const removeFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeDbResume = () => {
    setSelectedDbResume(null);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInput(value);

    const words = value.split(' ');
    const lastWord = words[words.length - 1];
    
    if (lastWord.startsWith('@')) {
      setShowMentionMenu(true);
    } else {
      setShowMentionMenu(false);
    }
  };

  const handleSelectMention = (resume: SavedResume) => {
    setSelectedDbResume(resume);
    setSelectedFile(null); 
    
    const words = input.split(' ');
    words.pop();
    setInput(words.join(' ').trim());
    
    setShowMentionMenu(false);
    inputRef.current?.focus();
  };

  const handleQuickReply = (type: string) => {
    let aiResponse = '';

    switch (type) {
      case 'zero-click':
        aiResponse = "Zero-click 사용법은 메인화면에서 챗봇에게\n**'나 내일 파이썬 백엔드 면접인데 빡세게 준비하게 해 줘'\n라고 치면? AI가 바로 사용자님을 맞춤형 면접장으로 이동시켜줍니다.\n(만약 원하는 세팅을 하지 않으면 기본 값으로 설정됩니다.)";
        break;
      case 'manual':
        aiResponse = "AIWORK는 맞춤형 모의면접 플랫폼입니다.\n**내 이력서를 등록하고 직무와 난이도를 선택하면\n깐깐한 기술팀장이나 부드러운 인사담당자 등 원하는 페르소나의 AI와 실제처럼 면접을 볼 수 있습니다.";
        break;
      case 'resume':
        aiResponse = "이력서 분석 기능은 업로드하신 PDF나 텍스트 이력서를 벡터 DB에 저장하여,\n**지원자님의 실제 경험을 바탕으로 한 날카로운 꼬리질문을 생성하는\nAIWORK의 핵심 기술입니다.";
        break;
      default:
        return;
    }

    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        type: 'bot',
        content: aiResponse,
      },
    ]);
  };

  const handleSend = async () => {
    if (!input.trim() && !selectedFile && !selectedDbResume) return;

    let attachedText = '';
    if (selectedFile) attachedText = `\n(첨부파일: ${selectedFile.name})`;
    else if (selectedDbResume) attachedText = `\n(저장된 이력서: ${selectedDbResume.title})`;

    const userMessageContent = input.trim() ? `${input}${attachedText}` : attachedText.trim();

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: userMessageContent.trim(),
    };
    
    setMessages((prev) => [...prev, userMessage]);
    
    const fileToUpload = selectedFile;
    const dbResumeToUse = selectedDbResume;
    const currentInput = input.trim();
    
    setInput('');
    removeFile();
    removeDbResume();
    setShowMentionMenu(false);
    setIsTyping(true);

    try {
      if (fileToUpload || dbResumeToUse) {
        const loadingId = Date.now().toString() + '_loading';
        
        if (currentInput.includes('첨삭')) {
          setMessages((prev) => [...prev, {
            id: loadingId,
            type: 'bot',
            content: '문서를 분석하고 첨삭을 진행 중입니다. 잠시만 기다려주세요.',
          }]);

          const documentType = currentInput.includes('자소서') ? 'cover_letter' : 'resume';
          
          let feedbackContent = '';
          if (fileToUpload) {
            const response = await homeApi.proofreadFile(fileToUpload, documentType);
            feedbackContent = response.feedback;
          } else if (dbResumeToUse) {
            feedbackContent = `[DB 이력서 첨삭 결과 테스트]\n${dbResumeToUse.title} 문서의 첨삭이 완료되었습니다. (백엔드 연동 전 가짜 데이터)`;
          }
          
          setMessages((prev) => prev.filter(m => m.id !== loadingId));
          setMessages((prev) => [...prev, {
            id: Date.now().toString(),
            type: 'bot',
            content: '첨삭이 완료되었습니다. 결과는 아래 다운로드 버튼을 통해 확인하세요.',
            downloadContent: feedbackContent,
            downloadFilename: `AIWORK_첨삭결과_${Date.now()}.txt`
          }]);
        } 
        else {
          setMessages((prev) => [...prev, {
            id: loadingId,
            type: 'bot',
            content: '스마트 이력서 분석 중입니다. 잠시만 기다려주세요.',
          }]);

          if (fileToUpload) {
            await inferApi.ingestResume(fileToUpload, `session_${Date.now()}`);
          } else if (dbResumeToUse) {
            await new Promise(r => setTimeout(r, 1000));
          }
          
          setMessages((prev) => prev.filter(m => m.id !== loadingId));
          setResumeUsed(true);

          setMessages((prev) => [...prev, {
            id: Date.now().toString(),
            type: 'bot',
            content: '이력서 분석이 완료되었습니다. 대시보드에서 분석 결과를 확인하시거나 모의면접을 시작할 수 있습니다.\n구체적인 첨삭을 원하시면 "이력서 첨삭해줘"라고 말씀해 주세요.',
          }]);
        }
        
        setIsTyping(false);
        return;
      }

      if (currentInput.includes('내 정보') || currentInput.includes('계정 설정')) {
        setMessages(prev => [...prev, { id: Date.now().toString(), type: 'bot', content: '내 정보(MyPage)로 즉시 이동합니다.' }]);
        setTimeout(() => { setIsOpen(false); navigate(ROUTES.MY_INFO); }, 1000);
        setIsTyping(false);
        return;
      }

      if (currentInput.includes('이력서')) {
        setMessages(prev => [...prev, { id: Date.now().toString(), type: 'bot', content: '이력서 관리 페이지로 이동합니다. 파일을 업로드해주세요.' }]);
        setTimeout(() => { setIsOpen(false); navigate('/resume'); }, 1000);
        setIsTyping(false);
        return;
      }

      if (currentInput.includes('면접') || currentInput.includes('세팅') || currentInput.includes('준비')) {
        const mockExtractedData = {
            jobRole: currentInput.includes('프론트') ? 'Frontend 개발자' : 'Python 백엔드 개발자',
            difficulty: '중',
        };
        
        setMessages(prev => [...prev, { 
          id: Date.now().toString(), 
          type: 'bot', 
          content: `${mockExtractedData.jobRole}, 난이도 ${mockExtractedData.difficulty}로 세팅되었습니다! 면접장으로 즉시 이동합니다.` 
        }]);
        
        setInferSettings(
          mockExtractedData.jobRole, 
          mockExtractedData.difficulty, 
          { 
            method: 'text', 
            persona: '깐깐한 기술팀장', 
            questionCount: 5, 
            resumeType: 'direct', 
            experienceText: '',
            questions: []
          }, 
          false
        );

        setTimeout(() => {
          setIsOpen(false);
          if (onOpenSetup) {
            onOpenSetup();
          } else {
            navigate(ROUTES.INTERVIEW);
          }
        }, 1500);
        setIsTyping(false);
        return;
      }

      const data = await homeApi.getGuide(currentInput, true);

      setMessages((prev) => [...prev, {
        id: Date.now().toString(),
        type: 'bot',
        content: data.content,
      }]);

    } catch (error) {
      console.error('Failed to process request:', error);
      setMessages((prev) => prev.filter(m => !m.id.endsWith('_loading')));
      setMessages((prev) => [...prev, {
        id: Date.now().toString(),
        type: 'bot',
        content: '요청을 처리하는 도중 서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="chatbot-wrapper">
      {isOpen && (
        <div className="chatbot-window">
          <div className="chat-header">
            <div className="header-info">
              <div className="bot-avatar">🦁</div>
              <div className="bot-title">
                <h3>AIWORK 가이드 봇</h3>
                <span><span className="dot"></span> 온라인 &middot; 실시간 탐색 연동</span>
              </div>
            </div>
            <button className="close-btn" onClick={() => setIsOpen(false)}>
              <X size={20} />
            </button>
          </div>

          <div className="chat-body">
            {messages.map((msg, index) => (
              <div key={msg.id} className={`message-row ${msg.type}`}>
                {msg.type === 'bot' && (
                  <div className="msg-avatar">🦁</div>
                )}
                
                <div className="message-content">
                  <div className="message-bubble">
                    {msg.content.split('\n').map((line, i) => (
                      <Fragment key={i}>
                        {line.startsWith('**') ? <strong>{line.replace(/\*\*/g, '')}</strong> : line.startsWith('###') ? <h4 style={{margin: '8px 0'}}>{line.replace('###', '')}</h4> : line}
                        <br />
                      </Fragment>
                    ))}
                    {msg.downloadContent && (
                      <div className="download-action">
                        <button 
                          className="download-btn"
                          onClick={() => {
                            const blob = new Blob([msg.downloadContent!], { type: 'text/plain' });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = msg.downloadFilename || 'feedback.txt';
                            a.click();
                            URL.revokeObjectURL(url);
                          }}
                        >
                          <Paperclip size={14} /> 첨삭 결과 다운로드 (TXT)
                        </button>
                      </div>
                    )}
                    {index === 0 && msg.type === 'bot' && (
                      <div className="quick-actions">
                        <button onClick={() => handleQuickReply('zero-click')}>Zero-Click 사용법</button>
                        <button onClick={() => handleQuickReply('manual')}>AIWORK 사용법</button>
                        <button onClick={() => handleQuickReply('resume')}>이력서 분석</button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            
            {isTyping && (
              <div className="message-row bot">
                <div className="msg-avatar">🦁</div>
                <div className="message-bubble loading">
                  <div className="loading-dots">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-container">
            {showMentionMenu && (
              <div className="mention-menu">
                <div className="mention-header">내 이력서 불러오기</div>
                <ul className="mention-list">
                  {savedResumes.map((resume) => (
                    <li key={resume.id} onClick={() => handleSelectMention(resume)}>
                      <div className="icon-wrapper">
                        <Database size={18} />
                      </div>
                      <span className="resume-title">{resume.title}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept=".pdf,.txt,.doc,.docx"
              onChange={handleFileSelect}
            />
            
            {(selectedFile || selectedDbResume) && (
              <div className="file-preview-chip">
                {selectedFile ? <Paperclip size={14} /> : <Database size={14} />}
                <span className="file-name">{selectedFile ? selectedFile.name : selectedDbResume?.title}</span>
                <button type="button" onClick={selectedFile ? removeFile : removeDbResume}>
                  <X size={14} />
                </button>
              </div>
            )}

            <div className="chat-input-pill">
              <button 
                type="button"
                className="clip-btn" 
                onClick={() => fileInputRef.current?.click()}
                title="이력서 첨부"
              >
                <Paperclip size={20} />
              </button>
              
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={handleInputChange}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="질문을 입력하거나 @를 눌러 이력서를 불러오세요..."
                disabled={isTyping}
              />
              
              <button 
                className={`send-btn ${input.trim() || selectedFile || selectedDbResume ? 'active' : ''}`}
                onClick={handleSend} 
                disabled={(!input.trim() && !selectedFile && !selectedDbResume) || isTyping}
              >
                <ArrowUp size={18} strokeWidth={3} />
              </button>
            </div>
          </div>
        </div>
      )}

      {!isOpen && (
        <button className="chatbot-toggle" onClick={() => setIsOpen(true)}>
          <div className="toggle-avatar">🦁</div>
        </button>
      )}
    </div>
  );
};