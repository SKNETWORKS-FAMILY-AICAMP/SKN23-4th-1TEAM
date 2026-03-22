import { useEffect, useState } from "react";
import { jobsApi } from "../../api/jobsApi";
import { resumeApi } from "../../api/resumeApi";
import { useAuthStore } from "../../store/authStore";
import "./JobCards.scss";

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
  const { user } = useAuthStore();
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        setLoading(true);

        let resolvedJobRole = jobRole || "";

        if (user?.id && !resolvedJobRole) {
          try {
            const latestResume = await resumeApi.getLatestResume(
              Number(user.id),
            );

            if (latestResume) {
              if (!resolvedJobRole) {
                resolvedJobRole = latestResume.job_role || "";
              }
            }
          } catch (e) {
            // 최신 이력서 조회 실패 시 무시
          }
        }

        const primaryTitle = resolvedJobRole || "채용";

        // 키워드/직무 기반 검색
        let data = await jobsApi.searchJobs({
          startPage: 1,
          display: 100,
          empWantedTitle: primaryTitle,
          jobRole: resolvedJobRole,
        });

        // 그래도 없으면 완전 기본 검색
        if (!data.items || data.items.length === 0) {
          data = await jobsApi.searchJobs({
            startPage: 1,
            display: 100,
          });
        }

        setJobs(data.items || []);
      } catch (error) {
        console.error("Failed to fetch jobs", error);
        setJobs([]);
      } finally {
        setLoading(false);
      }
    };

    fetchJobs();
  }, [jobRole, keywords, user?.id]);

  const formatDate = (ds?: string) => {
    if (!ds || ds.length < 8) return ds || "";
    return `${ds.substring(2, 4)}.${ds.substring(4, 6)}.${ds.substring(6, 8)}`;
  };

  if (loading) {
    return <div className="loading-state">채용공고를 불러오는 중입니다...</div>;
  }

  if (!jobs.length) {
    return <div className="empty-state">조회된 맞춤 채용공고가 없습니다.</div>;
  }

  return (
    <div className="job-cards-container">
      {jobs.map((job, idx) => (
        <div key={job.empSeqno || idx} className="job-card">
          <div className="job-card-main">
            {job.regLogImgNm && (
              <img src={job.regLogImgNm} alt="기업 로고" className="job-logo" />
            )}

            <div className="job-info">
              <h4 className="job-title">
                {job.empBusiNm} — {job.empWantedTitle}
              </h4>
              <p className="job-meta">{job.coClcdNm || ""}</p>
              <p className="job-meta">{job.empWantedTypeNm || ""}</p>
              <p className="job-date">
                {formatDate(job.empWantedStdt)} ~{" "}
                {formatDate(job.empWantedEndt)}
              </p>
            </div>
          </div>

          <div className="job-card-action">
            <button
              className="apply-btn"
              onClick={() =>
                window.open(
                  job.empWantedHomepgDetail || job.empWantedMobileUrl || "#",
                  "_blank",
                )
              }
            >
              지원하기
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
