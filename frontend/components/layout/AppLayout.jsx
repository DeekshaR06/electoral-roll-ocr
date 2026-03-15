import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './NavBar';
import Footer from './Footer';

export default function AppLayout() {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#f5f7fa' }}>
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}