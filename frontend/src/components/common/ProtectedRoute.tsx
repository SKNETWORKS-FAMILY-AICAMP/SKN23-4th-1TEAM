
import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { ROUTES } from '../../constants/routes';

interface ProtectedRouteProps {
  requiredTier?: 'guest' | 'normal' | 'premium';
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ requiredTier }) => {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.AUTH} replace />;
  }

  // Example logic for tier guarding
  if (requiredTier && user?.tier) {
    const tiers = ['guest', 'normal', 'premium'];
    const currentTierIndex = tiers.indexOf(user.tier);
    const requiredTierIndex = tiers.indexOf(requiredTier);

    if (currentTierIndex < requiredTierIndex) {
      // Not enough permissions
      return <Navigate to={ROUTES.HOME} replace />;
    }
  }

  return <Outlet />;
};
