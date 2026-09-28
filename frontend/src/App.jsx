import React, { useState, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import SplashScreen from './components/SplashScreen';

// Lazy-loaded page chunks for fast initial load & route-level code splitting
const LineagesPage = React.lazy(() => import('./pages/LineagesPage'));
const SurnameDetailPage = React.lazy(() => import('./pages/SurnameDetailPage'));
const AncestorsPage = React.lazy(() => import('./pages/AncestorsPage'));
const AncestorDetailPage = React.lazy(() => import('./pages/AncestorDetailPage'));
const NetworkPage = React.lazy(() => import('./pages/NetworkPage'));
const AtlasPage = React.lazy(() => import('./pages/AtlasPage'));
const RecordsPage = React.lazy(() => import('./pages/RecordsPage'));
const RecordDetailPage = React.lazy(() => import('./pages/RecordDetailPage'));
const ObituariesPage = React.lazy(() => import('./pages/ObituariesPage'));
const InterconnectionsPage = React.lazy(() => import('./pages/InterconnectionsPage'));
const OralHistoriesPage = React.lazy(() => import('./pages/OralHistoriesPage'));
const SourcesPage = React.lazy(() => import('./pages/SourcesPage'));

function RouteLoadingFallback() {
  return (
    <div className="py-24 flex flex-col items-center justify-center space-y-3">
      <div className="w-8 h-8 rounded-full border-2 border-[#C68B59]/30 border-t-[#C68B59] animate-spin" />
      <span className="text-xs font-mono text-[#A8A096]">Accessing Archival Vault...</span>
    </div>
  );
}

export default function App() {
  const [showSplash, setShowSplash] = useState(() => {
    if (typeof window !== 'undefined') {
      const hasSeen = sessionStorage.getItem('hasSeenSplash');
      const isDeepLink = window.location.pathname !== '/' && window.location.pathname !== '';
      return !hasSeen && !isDeepLink;
    }
    return true;
  });

  const handleEnterArchive = () => {
    sessionStorage.setItem('hasSeenSplash', 'true');
    setShowSplash(false);
  };

  if (showSplash) {
    return <SplashScreen onEnter={handleEnterArchive} />;
  }

  return (
    <BrowserRouter>
      <Suspense fallback={<RouteLoadingFallback />}>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<LineagesPage />} />
            <Route path="lineages" element={<LineagesPage />} />
            <Route path="lineages/:surname" element={<SurnameDetailPage />} />
            
            <Route path="ancestors" element={<AncestorsPage />} />
            <Route path="ancestors/:id" element={<AncestorDetailPage />} />
            
            <Route path="network" element={<NetworkPage />} />
            <Route path="atlas" element={<AtlasPage />} />
            
            <Route path="records" element={<RecordsPage />} />
            <Route path="records/:id" element={<RecordDetailPage />} />
            
            <Route path="obituaries" element={<ObituariesPage />} />
            <Route path="interconnections" element={<InterconnectionsPage />} />
            <Route path="oral-histories" element={<OralHistoriesPage />} />
            <Route path="sources" element={<SourcesPage />} />

            {/* Catch-all redirect to lineages */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
