import { useParams, useNavigate, Navigate } from 'react-router-dom';
import SurnamePortalView from '../components/SurnamePortalView';

export default function SurnameDetailPage() {
  const { surname } = useParams();
  const navigate = useNavigate();

  if (!surname) {
    return <Navigate to="/lineages" replace />;
  }

  return (
    <div className="w-full">
      <SurnamePortalView
        surname={surname}
        onClose={() => navigate('/lineages')}
        onSelectPerson={(id) => navigate(`/ancestors/${id}`)}
        onOpenGraph={(sn) => navigate(`/network?surname=${encodeURIComponent(sn)}`)}
      />
    </div>
  );
}
