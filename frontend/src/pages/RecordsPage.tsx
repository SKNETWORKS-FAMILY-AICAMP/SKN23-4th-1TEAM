import { Header } from '../components/common/Header';
import './RecordsPage.scss';

export const RecordsPage = () => {
  return (
    <div className="page-layout">
      <Header />
      <main className="records-main">
        <div className="records-page-card">
          <h1>🎙 내 면접 기록</h1>
          <p className="sub">지금까지 진행한 AI 면접 결과와 피드백을 확인하세요.</p>
          <div className="empty-records">
            <div className="empty-icon">📋</div>
            <h3>아직 면접 기록이 없습니다</h3>
            <p>홈 화면에서 AI 모의 면접을 시작해 첫 번째 기록을 만들어보세요!</p>
          </div>
        </div>
      </main>
    </div>
  );
};
