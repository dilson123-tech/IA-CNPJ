import { Navigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { isAuthenticated } from '../../services/auth';

type ProtectedRouteProps = {
  children: ReactNode;
};

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation();

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <>{children}</>;
}
