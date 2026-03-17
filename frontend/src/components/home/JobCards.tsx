import { useEffect, useState } from 'react';
import { jobsApi } from '../../api/jobsApi';
import './JobCards.scss';

interface JobItem {
  empSeqno?: string;
  empWantedTitle?: string;
  empBusiNm?: string;
  coClcdNm?: string;
  empWantedStdt?: string;
  empWantedEndt?: string;
  empWantedTypeNm?: string;
  regLogImgNm?: string;
  empWantedHomepgDetail?: string;
  empWantedMobileUrl?: string;
}

interface Props {
  jobRole?: string;
  keywords?: string;
}

export const JobCards = ({ jobRole, keywords }: Props) => {
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        setLoading(true);
        const data = await jobsApi.searchJobs({
          startPage: 1,
          display: 20,
          empWantedTitle: keywords || jobRole || undefined
        });
        setJobs(data.items || []);
      } catch (error) {
        console.error('Failed to fetch jobs', error);
      } finally {
        setLoading(false);
      }
    };
    fetchJobs();
  }, [jobRole, keywords]);

  const formatDate = (ds?: string) => {
    if (!ds || ds.length < 8) return ds || '';
    return `${ds.substring(2, 4)}.${ds.substring(4, 6)}.${ds.substring(6, 8)}`;
  };

  if (loading) return <div className="loading-state">채용공고를 불러오는 중입니다...</div>;
  if (!jobs.length) return <div className="empty-state">조회된 맞춤 채용공고가 없습니다.</div>;

  return (
    <div className="job-cards-container">
      {jobs.map((job, idx) => (
        <div key={job.empSeqno || idx} className="job-card">
          <div className="job-card-main">
            {job.regLogImgNm && (
              <img src={job.regLogImgNm} alt="기업 로고" className="job-logo" />
            )}
            <div className="job-info">
              <h4 className="job-title">{job.empBusiNm} — {job.empWantedTitle}</h4>
              <p className="job-meta">{job.coClcdNm || ''}</p>
              <p className="job-meta">{job.empWantedTypeNm || ''}</p>
              <p className="job-date">{formatDate(job.empWantedStdt)} ~ {formatDate(job.empWantedEndt)}</p>
            </div>
          </div>
          <div className="job-card-action">
            <button 
              className="apply-btn" 
              onClick={() => window.open(job.empWantedHomepgDetail || job.empWantedMobileUrl || '#', '_blank')}
            >
              지원하기
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
