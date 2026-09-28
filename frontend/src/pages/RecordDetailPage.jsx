import { useParams, useNavigate, Navigate } from 'react-router-dom';
import TranscribedDocumentView from '../components/TranscribedDocumentView';

export default function RecordDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  if (!id) {
    return <Navigate to="/records" replace />;
  }

  return (
    <div className="w-full">
      <TranscribedDocumentView
        identifier={id}
        onClose={() => navigate('/records')}
        onSelectPerson={(personId) => navigate(`/ancestors/${personId}`)}
      />
    </div>
  );
}
