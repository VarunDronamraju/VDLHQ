import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import client from './api/client';
import Button from './components/Button';
import Input from './components/Input';
import Card from './components/Card';
import Inquiry from './pages/Inquiry';
import OpsDashboard from './pages/OpsDashboard';
import ClientDashboard from './pages/ClientDashboard';
import Portfolio from './pages/Portfolio';
import Reviews from './pages/Reviews';

const Home = () => (
  <div className="p-20 text-center">
    <h1 className="text-4xl font-bold">LocationHQ</h1>
    <p className="text-gray-500 mt-4">Minimal Production Management</p>
  </div>
);

const Login = () => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState('');

  const handleRoleLogin = async (role) => {
    setLoading(true);
    setError('');
    try {
      const response = await client.post('/api/v1/login', { role });
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('role', role);
      window.location.href = role === 'ops' ? '/ops' : '/client';
    } catch (err) {
      console.error('Login error:', err);
      setError('Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-20">
      <Card className="p-10 space-y-8 text-center border-gray-100 shadow-xl shadow-gray-100/50">
        <div className="space-y-3">
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">Welcome</h1>
          <p className="text-gray-500 text-sm">Select your workspace to continue.</p>
        </div>

        <div className="flex flex-col gap-4">
          <Button 
            onClick={() => handleRoleLogin('ops')} 
            disabled={loading}
            className="w-full h-14 text-sm font-bold tracking-wide transition-all active:scale-[0.98]"
          >
            {loading ? 'Entering...' : 'Login as Admin'}
          </Button>
          
          <Button 
            onClick={() => handleRoleLogin('client')} 
            variant="secondary"
            disabled={loading}
            className="w-full h-14 text-sm font-bold tracking-wide transition-all active:scale-[0.98]"
          >
            {loading ? 'Entering...' : 'Login as Client'}
          </Button>
        </div>

        {error && <p className="text-xs text-red-600 font-medium">{error}</p>}

        <div className="pt-6 border-t border-gray-50">
          <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest leading-relaxed">
            LocationHQ Operational MVP v1.0<br/>
            Role-Based Access Control Enabled
          </p>
        </div>
      </Card>
    </div>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Home />} />
          <Route path="portfolio" element={<Portfolio />} />
          <Route path="reviews" element={<Reviews />} />
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
