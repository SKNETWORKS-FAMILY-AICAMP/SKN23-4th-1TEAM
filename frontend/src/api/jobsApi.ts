import { axiosClient } from './axiosClient';

export interface JobsQuery {
  startPage: number;
  display: number;
  job_role?: string;
  keywords?: string;
  [key: string]: any;
}

export const jobsApi = {
  searchJobs: async (query: JobsQuery) => {
    const response = await axiosClient.post('/jobs/search', query);
    return response.data;
  }
};
