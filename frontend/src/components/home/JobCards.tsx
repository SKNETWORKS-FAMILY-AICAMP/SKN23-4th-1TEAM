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

        let searchTitle = keywords || jobRole;

        // props로 검색어가 없고 로그인된 사용자라면, 최신 이력서에서 분석된 키워드와 직무를 가져옵니다.
        if (!searchTitle && user?.id) {
          try {
            const latestResume = await resumeApi.getLatestResume(
              Number(user.id),
            );
            if (latestResume) {
              const extractedKeywords =
                latestResume.analysis_result?.keywords?.join(" ") || "";
              searchTitle = extractedKeywords || latestResume.job_role;
            }
          } catch (e) {
            // 이력서를 찾을 수 없는 경우 무시 (fallback 사용)
          }
        }

        const finalTitle = searchTitle || "채용";

        // 1차 검색: 유저 맞춤형 키워드 혹은 "채용"으로 검색 (최대 100건 출력)
        let data = await jobsApi.searchJobs({
          startPage: 1,
          display: 100,
          empWantedTitle: finalTitle,
        });

        // 2차 폴백: 분석된 키워드가 너무 구체적이라 0건일 경우 "채용"으로 재검색
        if ((!data.items || data.items.length === 0) && finalTitle !== "채용") {
          data = await jobsApi.searchJobs({
            startPage: 1,
            display: 100,
            empWantedTitle: "채용",
          });
        }

        // 3차 폴백: 그래도 0건이면 아예 키워드 없이 전체 채용공고 출력 (빈 화면 방지)
        if (!data.items || data.items.length === 0) {
          data = await jobsApi.searchJobs({
            startPage: 1,
            display: 100,
          });
        }

        setJobs(data.items || []);
      } catch (error) {
        console.error("Failed to fetch jobs", error);
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

  if (loading)
    return <div className="loading-state">채용공고를 불러오는 중입니다...</div>;
  if (!jobs.length)
    return <div className="empty-state">조회된 맞춤 채용공고가 없습니다.</div>;

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
