import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import ProblemMissionHero from './components/ProblemMissionHero';
import AuthModal from './components/AuthModal';
import Footer from './components/Footer';
import { apiService } from './services/api';

export default function App() {
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'register'
  const [currentUser, setCurrentUser] = useState(null);
  const [backendStatus, setBackendStatus] = useState('checking');

  useEffect(() => {
    // Check backend connection health
    async function checkApi() {
      try {
        const res = await apiService.checkHealth();
        if (res.status === 'ok') {
          setBackendStatus('connected');
        } else {
          setBackendStatus('offline');
        }
      } catch (e) {
        setBackendStatus('offline');
      }
    }
    checkApi();
  }, []);

  const handleOpenLogin = () => {
    setAuthMode('login');
    setAuthModalOpen(true);
  };

  const handleOpenRegister = () => {
    setAuthMode('register');
    setAuthModalOpen(true);
  };

  const handleAuthSuccess = (userData) => {
    setCurrentUser(userData);
  };

  const handleLogout = () => {
    setCurrentUser(null);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Backend connection status indicator */}
      {backendStatus === 'offline' && (
        <div className="bg-amber-600 text-amber-50 text-xs px-4 py-1.5 text-center font-medium">
          Note: Backend service at localhost:8000 is not currently running. Authentication runs in local-preview mode.
        </div>
      )}

      {/* Navigation */}
      <Navbar
        onOpenLogin={handleOpenLogin}
        onOpenRegister={handleOpenRegister}
        user={currentUser}
        onLogout={handleLogout}
      />

      {/* Main Landing Content */}
      <ProblemMissionHero
        onOpenLogin={handleOpenLogin}
        onOpenRegister={handleOpenRegister}
      />

      {/* Authentication Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authMode}
        onAuthSuccess={handleAuthSuccess}
      />

      {/* Footer */}
      <Footer />
    </div>
  );
}
