import { useState, useRef, useEffect } from 'react';
import { Send, Mic } from 'lucide-react';
import { useInferStore } from '../../store/inferStore';
import './ChatWindow.scss';

interface Message {
  text: string;
  sender: 'user' | 'ai';
  score?: number; 
}

interface Props {
  messages: Message[];
  isConnected: boolean;
  onSendMessage: (text: string) => void;
  onToggleAudio?: () => void;
}

export const ChatWindow = ({ messages, isConnected, onSendMessage, onToggleAudio }: Props) => {
  const { method } = useInferStore();
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (inputText.trim() && isConnected) {
      onSendMessage(inputText);
      setInputText('');
    }
  };

  return (
    <div className={`chat-window ${method === 'text' ? 'text-mode' : ''}`}>
      <div className="messages-area">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message-row ${msg.sender}`}>
            {msg.sender === 'ai' && (
              <div className="profile">
                <div className="avatar">👾</div>
                <span className="name">AI 면접관</span>
              </div>
            )}
            
            <div className="bubble-wrapper" style={{ display: 'flex', flexDirection: 'column', alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start' }}>
              <div className="bubble">
                {msg.text.split('\n').map((line, i) => (
                  <p key={i}>{line}</p>
                ))}
              </div>
              
              {/* 유저가 답변을 보낸 후 점수가 매겨지면 여기에 표시됩니다 */}
              {msg.sender === 'user' && msg.score !== undefined && (
                <div style={{ fontSize: '11px', fontWeight: 600, color: '#888', marginTop: '6px', marginRight: '4px' }}>
                  AI 평가 점수: {msg.score.toFixed(1)} / 10
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        {method === 'voice' && onToggleAudio && (
          <button className="audio-toggle-btn" onClick={onToggleAudio}>
            <Mic size={20} />
          </button>
        )}
        <div className="input-box">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSend();
            }}
            placeholder="메시지를 입력하세요"
            disabled={!isConnected}
          />
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!isConnected || !inputText.trim()}
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
};