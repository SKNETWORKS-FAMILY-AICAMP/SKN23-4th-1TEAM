
import { Routes, Route } from 'react-router-dom';
import { ROUTES } from '../constants/routes';
import { Home, Auth, Interview, MyPage, ResumePage, RecordsPage, BoardPage, AdminPage } from '../pages';
import { ProtectedRoute } from '../components/common/ProtectedRoute';

export const AppRouter = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path={ROUTES.HOME} element={<Home />} />
      <Route path={ROUTES.AUTH} element={<Auth />} />

      {/* Protected Routes (Require Login) */}
      <Route element={<ProtectedRoute />}>
        <Route path={ROUTES.INTERVIEW} element={<Interview />} />
        <Route path={ROUTES.MY_INFO} element={<MyPage />} />
        <Route path={ROUTES.RECORDS} element={<RecordsPage />} />
        <Route path={ROUTES.RESUME} element={<ResumePage />} />
        <Route path={ROUTES.BOARD} element={<BoardPage />} />
        
        <Route path={ROUTES.ADMIN} element={<AdminPage />} />
      </Route>

      
      {/* Catch-all */}
      <Route path="*" element={<Home />} />
    </Routes>
  );
};
