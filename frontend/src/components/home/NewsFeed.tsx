import { useEffect, useState } from "react";
import { homeApi } from "../../api/homeApi";
import "./NewsFeed.scss";

interface Props {
  jobRole?: string;
}

export const NewsFeed = ({ jobRole }: Props) => {
  const [news, setNews] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNews = async () => {
      try {
        setLoading(true);
        
        // 이력서 직무값이 전달되었다면 그 값을 사용, 이력서가 하나도 없다면 기본 범용 키워드 사용
        const targetRole = jobRole ? jobRole : "소프트웨어 엔지니어링";
        const query = `2026 latest core technology and ecosystem trends for ${targetRole}`;
          
        const data = await homeApi.getNews(query);
        if (data && data.content) {
          const items = data.content
            .split("---")
            .map((i: string) => i.trim())
            .filter(Boolean);
          setNews(items.slice(0, 10));
        }
      } catch (error) {
        console.error("Failed to fetch news", error);
      } finally {
        setLoading(false);
      }
    };
    
    // 이력서 데이터가 확실하게 준비된 상태에서만 검색 실행
    fetchNews();
  }, [jobRole]);

  if (loading)
    return (
      <div className="loading-state">
        Tavily AI로 최신 트렌드를 검색하는 중입니다...
      </div>
    );
  if (!news.length)
    return <div className="empty-state">No news is available right now.</div>;

  return (
    <div className="news-feed-container">
      {news.map((item, idx) => (
        <div key={idx} className="news-item">
          <div className="news-header">
            <span className="news-badge">NEWS {idx + 1}</span>
          </div>
          <p className="news-content">{item}</p>
        </div>
      ))}
      <p className="news-footer">Powered by Tavily Search Engine</p>
    </div>
  );
};