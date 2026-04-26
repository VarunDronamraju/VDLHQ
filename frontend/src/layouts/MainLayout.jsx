import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import Navbar from '../components/Navbar';

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

export default MainLayout;
