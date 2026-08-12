import React, { useState, useEffect } from 'react';
import HomeScreen from './components/HomeScreen';
import SplashScreen from './components/SplashScreen';

export default function App() {
  const [showSplash, setShowSplash] = useState(true);

  // Optional: Only show splash once per session (commented out to show every load initially, adjust as needed)
  useEffect(() => {
    const hasSeenSplash = sessionStorage.getItem('hasSeenSplash');
    if (hasSeenSplash) {
      setShowSplash(false);
    }
  }, []);

  const handleEnterArchive = () => {
    sessionStorage.setItem('hasSeenSplash', 'true');
    setShowSplash(false);
  };

  if (showSplash) {
    return <SplashScreen onEnter={handleEnterArchive} />;
  }

  return <HomeScreen />;
}
