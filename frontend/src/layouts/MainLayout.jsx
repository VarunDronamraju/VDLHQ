import React from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';

const MainLayout = () => {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/inquiry');
  };

  return (
    <div className="min-h-screen bg-neutral-bg">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <span className="text-xl font-bold text-primary">LocationHQ</span>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link to="/inquiry" className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900">
                  New Inquiry
                </Link>
                {token && (
                  <>
                    <Link to="/ops" className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-gray-700">
                      Ops Dashboard
                    </Link>
                    <Link to="/client" className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-gray-700">
                      Client Dashboard
                    </Link>
                  </>
                )}
              </div>
            </div>
            <div className="flex items-center">
              {token ? (
                <button
                  onClick={handleLogout}
                  className="text-sm font-medium text-gray-500 hover:text-gray-700"
                >
                  Logout
                </button>
              ) : (
                <Link to="/login" className="text-sm font-medium text-primary hover:text-primary-hover">
                  Login
                </Link>
              )}
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-10 px-4 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
};

export default MainLayout;
