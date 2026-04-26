import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const token = localStorage.getItem('token');

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    navigate('/login');
  };

  const navLinks = [
    { name: 'Home', path: '/' },
    { name: 'Portfolio', path: '/portfolio' },
    { name: 'Reviews', path: '/reviews' },
    { name: 'Inquiry', path: '/inquiry' },
  ];

  const role = localStorage.getItem('role');

  return (
    <nav className="fixed top-0 left-0 right-0 h-16 bg-white border-b border-gray-100 z-50 flex items-center">
      <div className="max-w-7xl mx-auto px-6 w-full flex justify-between items-center">
        <div className="flex items-center gap-12">
          <Link to="/" className="text-xl font-bold tracking-tight text-[#0D7C66]">
            LocationHQ
          </Link>
          
          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={`text-sm font-medium hover:text-[#0D7C66] transition-colors ${
                  location.pathname === link.path ? 'text-[#0D7C66]' : 'text-gray-500'
                }`}
              >
                {link.name}
              </Link>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-6">
          {token ? (
            <>
              {role === 'ops' ? (
                <Link 
                  to="/ops" 
                  className={`text-sm font-medium ${location.pathname === '/ops' ? 'text-[#0D7C66]' : 'text-gray-500'}`}
                >
                  Ops Pipeline
                </Link>
              ) : (
                <Link 
                  to="/client" 
                  className={`text-sm font-medium ${location.pathname === '/client' ? 'text-[#0D7C66]' : 'text-gray-500'}`}
                >
                  My Dashboard
                </Link>
              )}
              <button
                onClick={handleLogout}
                className="text-sm font-medium text-gray-500 hover:text-red-600 transition-colors"
              >
                Logout
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="text-sm font-medium text-gray-500 hover:text-[#0D7C66] transition-colors"
            >
              Login
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
