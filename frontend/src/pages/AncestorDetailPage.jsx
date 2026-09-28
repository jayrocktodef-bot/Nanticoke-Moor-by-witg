import { useParams, useNavigate, Navigate } from 'react-router-dom';
import PersonProfileView from '../components/PersonProfileView';

export default function AncestorDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  if (!id) {
    return <Navigate to="/ancestors" replace />;
  }

  return (
    <div className="w-full">
      <PersonProfileView
        personId={id}
        onClose={() => navigate(-1)}
        onSelectPerson={(newId) => navigate(`/ancestors/${newId}`)}
      />
    </div>
  );
}
