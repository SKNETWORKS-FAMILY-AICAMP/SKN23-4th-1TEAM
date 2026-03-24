import { useEffect, useState } from "react";
import { homeApi } from "../../api/homeApi";
import type { Memo } from "../../api/homeApi";
import { useAuthStore } from "../../store/authStore";
import { ROUTES } from "../../constants/routes";
import "./MemoBoard.scss";

export const MemoBoard = () => {
  const { user, openLoginModal } = useAuthStore();
  const [memos, setMemos] = useState<Memo[]>([]);
  const [newMemo, setNewMemo] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchMemos = async () => {
    try {
      const data = await homeApi.getMemos();
      setMemos(data.items || []);
    } catch (error) {
      console.error("Failed to fetch memos", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemos();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemo.trim()) return;

    if (!user) {
      openLoginModal();
      return;
    }

    const colors = [
      {
        color: "linear-gradient(135deg, #fffbf0 0%, #ffffff 100%)",
        border: "#fef08a",
        text_color: "#92400e",
      },
      {
        color: "linear-gradient(135deg, #f2fcf5 0%, #ffffff 100%)",
        border: "#d1fae5",
        text_color: "#166534",
      },
      {
        color: "linear-gradient(135deg, #fdf4ff 0%, #ffffff 100%)",
        border: "#fae8ff",
        text_color: "#872a96",
      },
      {
        color: "linear-gradient(135deg, #f0f7ff 0%, #ffffff 100%)",
        border: "#dbeafe",
        text_color: "#0056b3",
      },
    ];
    const picked = colors[Math.floor(Math.random() * colors.length)];

    try {
      await homeApi.createMemo({
        author: user.name || "익명",
        content: newMemo,
        color: picked.color,
        border: picked.border,
        text_color: picked.text_color,
      });
      setNewMemo("");
      fetchMemos();
    } catch (error) {
      alert("저장 실패했습니다.");
    }
  };

  if (loading) {
    return <div className="loading-state">메모를 불러오는 중입니다...</div>;
  }

  return (
    <div className="memo-board-container">

      <form onSubmit={handleSubmit} className="memo-form">
        <p>
          <strong>응원의 한마디 남기기</strong>
        </p>
        <div className="memo-input-row">
          <input
            type="text"
            value={newMemo}
            onChange={(e) => setNewMemo(e.target.value)}
            placeholder="자유롭게 응원의 메시지나 팁을 남겨보세요!"
          />
          <button type="submit">보내기</button>
        </div>
      </form>

      <div className="memos-grid">
        {memos.map((memo, idx) => (
          <div
            key={memo.id || idx}
            className="memo-card"
            style={{
              background: memo.color,
              border: `1px solid ${memo.border}`,
              color: memo.text_color,
            }}
          >
            <div className="memo-author">
              <span>{memo.author}</span>
            </div>
            <div className="memo-content">{memo.content}</div>
          </div>
        ))}
      </div>
    </div>
  );
};
