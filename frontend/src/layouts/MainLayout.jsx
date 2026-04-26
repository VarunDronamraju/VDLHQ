import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from '../components/Navbar';

const MainLayout = () => {
  return (
    <div className="min-h-screen bg-[#FCFCFC]">
      <Navbar />
      <main className="max-w-7xl mx-auto pt-24 pb-16 px-6">
        <Outlet />
      </main>
    </div>
  );
};

export default MainLayout;
