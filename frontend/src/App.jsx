import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Inquiry from './pages/Inquiry';
import OpsDashboard from './pages/OpsDashboard';
import ClientDashboard from './pages/ClientDashboard';

// Simple login page component
const Login = () => {
  const handleLogin = () => {
    // For demo purposes, we'll just set a dummy token
    localStorage.setItem('token', 'demo-token');
    window.location.href = '/ops';
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <h1 className="text-2xl font-bold">Internal Login</h1>
      <button 
        onClick={handleLogin}
        className="bg-primary text-white px-6 py-2 rounded-md"
      >
        Login as Staff
      </button>
    </div>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/inquiry" replace />} />
          <Route path="inquiry" element={<Inquiry />} />
          <Route path="login" element={<Login />} />
          <Route path="ops" element={<OpsDashboard />} />
          <Route path="client" element={<ClientDashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
