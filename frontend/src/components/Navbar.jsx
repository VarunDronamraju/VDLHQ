import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const token = localStorage.getItem('token');
  const role = localStorage.getItem('role');

  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, []);

  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    navigate('/login');
  };

  const primaryLinks = [
    { name: 'Discovery', path: '/' },
    { name: 'Portfolio', path: '/portfolio' },
    { name: 'Reviews', path: '/reviews' },
    { name: 'Inquiry', path: '/inquiry' },
    { name: 'Blueprint', path: '/blueprint' },
  ];

  return (
    <>
      {/* Top Bar */}
      <nav className="fixed top-0 left-0 right-0 h-20 z-40 flex items-center px-8 justify-between">
        {/* Left: Menu Toggle */}
        <div className="flex-1 flex items-center">
          <button 
            onClick={() => setIsOpen(true)}
            className="p-2 -ml-2 text-gray-900 transition-colors focus:outline-none"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M4 8h12M4 16h12" />
            </svg>
          </button>
        </div>
        
        {/* Center: Logo */}
        <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary" />
          <Link to="/" className="text-lg font-serif tracking-tight text-gray-900" style={{ fontFamily: "'Playfair Display', serif" }}>
            Location HQ
          </Link>
        </div>

        {/* Right: Quick Actions */}
        <div className="flex-1 flex items-center justify-end gap-6">
          <Link to="/blueprint" className="hidden md:block bg-black text-white px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-[0.2em] hover:bg-primary transition-all">
            Blueprint
          </Link>
          
          <Link to={token ? (role === 'ops' ? '/ops' : '/client') : '/login'} className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-full bg-black/5 flex items-center justify-center group-hover:bg-black group-hover:text-white transition-all">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <span className="hidden md:block text-[9px] font-black uppercase tracking-[0.2em] text-gray-900">
              {token ? 'Account' : 'Login'}
            </span>
          </Link>
        </div>
      </nav>

      {/* Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-white/10 backdrop-blur-sm z-50 animate-in fade-in duration-500"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Floating Glass Sidebar */}
      <aside 
        className={`fixed top-4 left-4 bottom-4 w-[320px] bg-white/40 backdrop-blur-3xl border border-white/50 z-[60] rounded-[48px] transform transition-all duration-700 cubic-bezier(0.16, 1, 0.3, 1) shadow-2xl ${
          isOpen ? 'translate-x-0 opacity-100' : '-translate-x-full opacity-0'
        }`}
      >
        <div className="flex flex-col h-full p-10">
          <button 
            onClick={() => setIsOpen(false)}
            className="w-10 h-10 flex items-center justify-center bg-black/5 hover:bg-black/10 rounded-full transition-colors mb-16"
          >
            <svg className="w-5 h-5 text-gray-800" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          <nav className="flex flex-col gap-6">
            {primaryLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={`text-[32px] font-serif leading-tight transition-all duration-300 ${
                  location.pathname === link.path 
                    ? 'text-primary translate-x-2' 
                    : 'text-gray-600 hover:text-gray-900 hover:translate-x-1'
                }`}
                style={{ fontFamily: "'Playfair Display', serif" }}
              >
                {link.name}
              </Link>
            ))}
          </nav>

          <div className="mt-auto space-y-8">
            <div className="space-y-4">
              <div className="space-y-1">
                <p className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]">Studio Intelligence</p>
                <Link to="/inquiry" className="group flex items-center gap-2 text-xs font-bold text-gray-900 uppercase tracking-widest">
                  Inquiry Studio 
                  <span className="group-hover:translate-x-1 transition-transform">→</span>
                </Link>
              </div>

              <div className="space-y-1">
                <p className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]">System Architecture</p>
                <Link to="/blueprint" className="group flex items-center gap-2 text-xs font-bold text-primary uppercase tracking-widest">
                  System Blueprint
                  <span className="group-hover:translate-x-1 transition-transform">→</span>
                </Link>
              </div>
            </div>

            <div className="pt-6 border-t border-black/5 flex flex-col gap-4">
              {token ? (
                <div className="flex flex-col gap-2">
                  <Link 
                    to={role === 'ops' ? '/ops' : '/client'}
                    className="text-[10px] font-black text-gray-900 uppercase tracking-[0.2em] hover:text-primary transition-colors"
                  >
                    {role === 'ops' ? 'Access Admin Control' : 'View Client Dashboard'}
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="text-left text-[10px] font-black text-red-500 uppercase tracking-[0.2em] hover:opacity-70 transition-opacity"
                  >
                    Logout System
                  </button>
                </div>
              ) : (
                <Link
                  to="/login"
                  className="text-[10px] font-black text-gray-900 uppercase tracking-[0.2em] hover:text-primary transition-colors"
                >
                  System Authentication
                </Link>
              )}
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Navbar;
