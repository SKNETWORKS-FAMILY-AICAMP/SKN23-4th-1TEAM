import { useEffect, useState } from 'react';
import { homeApi } from '../../api/homeApi';
import './NewsFeed.scss';

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
        const query = jobRole ? `latest AI and ${jobRole} trends` : `latest AI and backend trends`;
        const data = await homeApi.getNews(query);
        if (data && data.content) {
          const items = data.content.split('---').map((i: string) => i.trim()).filter(Boolean);
          setNews(items.slice(0, 10));
        }
      } catch (error) {
        console.error('Failed to fetch news', error);
      } finally {
        setLoading(false);
      }
    };
    fetchNews();
  }, [jobRole]);

  if (loading) return <div className="loading-state">Tavily AI로 최신 트렌드를 검색하는 중입니다...</div>;
  if (!news.length) return <div className="empty-state">No news is available right now.</div>;

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
