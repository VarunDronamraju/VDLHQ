import React from 'react';
import { BrowserRouter, Routes, Route, Link, Outlet } from 'react-router-dom';
import { ALL_LOCATIONS, PRODUCTIONS } from './api/data';
import Navbar from './components/Navbar';
import ShowcaseCard from './components/ShowcaseCard';
import Card from './components/Card';
import Button from './components/Button';
import OpsDashboard from './pages/OpsDashboard';
import ClientDashboard from './pages/ClientDashboard';
import Inquiry from './pages/Inquiry';
import Portfolio from './pages/Portfolio';
import Reviews from './pages/Reviews';
import Blueprint from './pages/Blueprint';
import client from './api/client';

const MainLayout = () => (
  <div className="min-h-screen bg-white selection:bg-primary/10 selection:text-primary">
    <Navbar />
    <main className="pt-20">
      <Outlet />
    </main>
    <footer className="py-20 border-t border-gray-50 text-center space-y-4">
      <div className="space-y-1">
        <p className="text-[10px] font-black text-gray-300 uppercase tracking-[0.4em]">LocationHQ Global Operational Network</p>
        <p className="text-[9px] font-black text-primary/40 uppercase tracking-[0.2em]">Work by Varun Dronamraju</p>
      </div>
      <div className="flex justify-center gap-8">
        <Link to="/" className="text-[10px] font-bold text-gray-400 uppercase tracking-widest hover:text-gray-900 transition-colors">London</Link>
        <Link to="/" className="text-[10px] font-bold text-gray-400 uppercase tracking-widest hover:text-gray-900 transition-colors">Paris</Link>
        <Link to="/" className="text-[10px] font-bold text-gray-400 uppercase tracking-widest hover:text-gray-900 transition-colors">New York</Link>
      </div>
    </footer>
  </div>
);

const Home = () => (
  <div className="bg-white">
    {/* Hero Section */}
    <div className="relative min-h-screen flex flex-col items-center justify-start pt-32 overflow-hidden">
      <div className="absolute inset-0 z-0">
        <img 
          src="/src/assets/mansion.png" 
          alt="Classical Mansion" 
          className="w-full h-full object-cover object-center opacity-40 grayscale-[20%]"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-white/40 to-white" />
      </div>

      <div className="relative z-10 max-w-4xl mx-auto text-center space-y-8 px-6">
        <div className="inline-flex items-center gap-3 px-4 py-1 bg-black/5 backdrop-blur-md border border-black/5 rounded-full">
          <div className="w-1.5 h-1.5 rounded-full bg-primary" />
          <span className="text-[10px] font-black text-gray-400 uppercase tracking-[0.3em]">Intelligence Driven Scouting</span>
        </div>

        <h1 className="text-6xl md:text-8xl font-serif text-gray-900 leading-[1.1] tracking-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
          The world's most<br />
          <span className="italic text-primary">iconic</span> sets.
        </h1>

        <div className="max-w-lg mx-auto">
          <p className="text-sm md:text-base text-gray-500 font-medium leading-relaxed tracking-tight">
            Trusted by the industry's elite. From Marvel masterpieces to<br className="hidden md:block" />
            boutique campaigns, we find the unfindable.
          </p>
        </div>

        <div className="pt-4 flex flex-col md:flex-row items-center justify-center gap-4">
          <Link 
            to="/inquiry" 
            className="inline-flex items-center gap-3 px-8 py-4 bg-gray-900 text-white text-xs font-black uppercase tracking-[0.2em] rounded-full hover:bg-primary transition-all hover:scale-105 active:scale-95 shadow-2xl shadow-gray-200"
          >
            Start Discovery
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </Link>
          <Link to="/portfolio" className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-400 hover:text-gray-900 transition-colors">
            View Showcase
          </Link>
        </div>
      </div>
    </div>

    {/* Featured Locations */}
    <div className="max-w-7xl mx-auto px-8 py-32 space-y-16">
      <div className="space-y-2">
        <h2 className="text-4xl font-serif text-gray-900" style={{ fontFamily: "'Playfair Display', serif" }}>Production Spaces</h2>
        <p className="text-gray-400 text-xs font-bold uppercase tracking-[0.3em]">Curated High-End Studios & Lofts</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {ALL_LOCATIONS.slice(0, 3).map((loc) => (
          <ShowcaseCard 
            key={loc.id}
            image={loc.image}
            label={loc.category}
            title={loc.name}
            meta={`${loc.area} • ${loc.crew_capacity} PAX`}
            data={loc}
            type="location"
          />
        ))}
      </div>
    </div>

    {/* Previous Productions */}
    <div className="bg-gray-50 py-32">
      <div className="max-w-7xl mx-auto px-8 space-y-16">
        <div className="flex justify-between items-end">
          <div className="space-y-2">
            <h2 className="text-4xl font-serif text-gray-900" style={{ fontFamily: "'Playfair Display', serif" }}>Recent Productions</h2>
            <p className="text-gray-400 text-xs font-bold uppercase tracking-[0.3em]">Global Campaigns & Feature Films</p>
          </div>
          <Link to="/portfolio" className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">View Full Archive</Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {PRODUCTIONS.slice(0, 2).map((prod) => (
            <ShowcaseCard 
              key={prod.id}
              image={prod.image}
              label={prod.house}
              title={prod.name}
              meta={`${prod.year} • Reference Clip`}
              className="aspect-video"
              data={prod}
              type="production_reference"
            />
          ))}
        </div>
      </div>
    </div>

    {/* Final CTA */}
    <div className="py-32 text-center space-y-8">
      <h2 className="text-5xl font-serif text-gray-900 max-w-2xl mx-auto leading-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
        Ready to find your<br />next location?
      </h2>
      <Link 
        to="/inquiry" 
        className="inline-flex items-center gap-3 px-10 py-5 bg-primary text-white text-xs font-black uppercase tracking-[0.2em] rounded-full hover:bg-gray-900 transition-all hover:scale-105 active:scale-95 shadow-2xl shadow-primary/20"
      >
        Open Inquiry Studio
      </Link>
    </div>
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
          <Route path="blueprint" element={<Blueprint />} />
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
