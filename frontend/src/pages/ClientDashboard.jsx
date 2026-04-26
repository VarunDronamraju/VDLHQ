import React, { useEffect, useState } from 'react';
import client from '../api/client';
import Card from '../components/Card';
import Button from '../components/Button';

const ClientDashboard = () => {
  const [dashboardData, setDashboardData] = useState({ leads: [], bookings: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedLead, setSelectedLead] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchDashboard = async () => {
    try {
      const response = await client.get('/api/v1/client/dashboard');
      setDashboardData(response.data);
    } catch (err) {
      console.error('Fetch dashboard error:', err);
      setError(err.response?.data?.detail || 'Failed to load dashboard. Ensure you are logged in as a client.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const openLeadDetail = async (leadId) => {
    setDetailLoading(true);
    try {
      const response = await client.get(`/api/v1/client/leads/${leadId}`);
      setSelectedLead(response.data);
    } catch (error) {
      console.error('Fetch lead detail error:', error);
    } finally {
      setDetailLoading(false);
    }
  };

  if (loading) return <div className="p-20 text-center text-gray-400 text-[10px] font-black uppercase tracking-[0.3em] animate-pulse">Syncing Portfolio State...</div>;
  
  if (error) {
    return (
      <div className="max-w-xl mx-auto mt-20 p-10 bg-red-50 text-red-700 rounded-[32px] border border-red-100 text-center space-y-4">
        <h2 className="text-sm font-black uppercase tracking-widest">Authentication Error</h2>
        <p className="text-xs leading-relaxed">{error}</p>
        <Button onClick={() => window.location.href = '/login'} variant="secondary" className="mt-4">Return to Login</Button>
      </div>
    );
  }

  const getStatusConfig = (status) => {
    const configs = {
      new: { label: 'Submitted', color: 'border-blue-400', bg: 'bg-blue-50', text: 'text-blue-700' },
      needs_info: { label: 'Action Required', color: 'border-yellow-400', bg: 'bg-yellow-50', text: 'text-yellow-700' },
      ready: { label: 'Production Ready', color: 'border-green-400', bg: 'bg-green-50', text: 'text-green-700' },
      matched: { label: 'Location Matched', color: 'border-teal-400', bg: 'bg-teal-50', text: 'text-teal-700' },
      booked: { label: 'Confirmed', color: 'border-indigo-500', bg: 'bg-indigo-50', text: 'text-indigo-700' },
      default: { label: status, color: 'border-gray-200', bg: 'bg-gray-50', text: 'text-gray-700' },
    };
    return configs[status] || configs.default;
  };

  const latestInquiry = dashboardData.leads[0];
  const contact = latestInquiry?.intake_data?.contact || {};

  return (
    <div className="max-w-[1400px] mx-auto px-6 md:px-10 py-12">
      <div className="relative min-h-[calc(100vh-12rem)] space-y-16">
        
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 border-b border-gray-100 pb-12">
          <div className="space-y-2">
            <h1 className="text-4xl font-black text-gray-900 tracking-tight uppercase">Dashboard</h1>
            <p className="text-[10px] text-gray-400 font-black uppercase tracking-[0.3em]">Client Project & Production Intelligence</p>
          </div>
          
          {latestInquiry && (
            <div className="flex items-center gap-5 bg-white px-8 py-5 rounded-[32px] shadow-sm border border-gray-100">
              <div className="w-12 h-12 rounded-full bg-primary/5 border border-primary/10 flex items-center justify-center text-primary font-black text-sm uppercase tracking-widest">
                {contact.name?.charAt(0) || 'U'}
              </div>
              <div className="space-y-1">
                <p className="text-xs font-black text-gray-900 uppercase tracking-[0.15em]">{contact.name}</p>
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  <p className="text-[9px] font-bold text-gray-400 uppercase tracking-widest">Active Partner</p>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
          {/* Active Inquiries */}
          <section className="space-y-8">
            <div className="flex justify-between items-center px-2">
              <h2 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.3em]">Active Inquiries</h2>
              <span className="bg-gray-50 border border-gray-100 text-gray-400 text-[9px] font-black px-2.5 py-1 rounded-full">
                {dashboardData.leads.length} VOLUME
              </span>
            </div>
            
            <div className="grid grid-cols-1 gap-6">
              {dashboardData.leads.map((lead) => {
                const config = getStatusConfig(lead.status);
                return (
                  <div key={lead.id} onClick={() => openLeadDetail(lead.id)} className="cursor-pointer group">
                    <Card className={`!p-6 border-l-[4px] ${config.color} hover:bg-white hover:shadow-xl hover:shadow-gray-200/50 transition-all duration-300 shadow-sm border border-gray-100 bg-white/50`}>
                      <div className="flex justify-between items-start gap-8">
                        <div className="space-y-4">
                          <div className="space-y-1.5">
                            <h3 className="font-black text-gray-900 text-sm uppercase tracking-tight leading-tight">
                              {lead.intake_data?.shoot_type || 'Production'}
                            </h3>
                            <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest line-clamp-1">
                              {lead.intake_data?.requirements || 'Brief analysis pending...'}
                            </p>
                          </div>
                          <div className="flex items-center gap-4 text-[9px] text-gray-300 font-black uppercase tracking-widest">
                            <div className="flex items-center gap-1.5">
                              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                              {new Date(lead.created_at).toLocaleDateString('en-GB')}
                            </div>
                            <div className="flex items-center gap-1.5">
                              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                              Verified ID: {lead.id.slice(0, 4)}
                            </div>
                          </div>
                        </div>
                        <div className={`${config.bg} ${config.text} px-3 py-1.5 rounded-full text-[8px] font-black uppercase tracking-widest border border-current opacity-70`}>
                          {config.label}
                        </div>
                      </div>
                    </Card>
                  </div>
                );
              })}
              {dashboardData.leads.length === 0 && (
                <div className="p-20 text-center border-2 border-dashed border-gray-100 rounded-[32px] text-gray-200 text-[10px] font-black uppercase tracking-widest bg-gray-50/20">
                  Empty Inquiry Queue
                </div>
              )}
            </div>
          </section>

          {/* Bookings Section */}
          <section className="space-y-8">
            <div className="flex justify-between items-center px-2">
              <h2 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.3em]">Confirmed Bookings</h2>
              <span className="bg-indigo-50 border border-indigo-100 text-indigo-400 text-[9px] font-black px-2.5 py-1 rounded-full">
                {dashboardData.bookings.length} LOCKED
              </span>
            </div>

            <div className="grid grid-cols-1 gap-6">
              {dashboardData.bookings.map((booking) => (
                <Card key={booking.id} className="!p-6 border-l-[4px] border-l-indigo-500 hover:shadow-xl hover:shadow-indigo-200/30 transition-all duration-300 shadow-sm border border-gray-100 bg-white">
                  <div className="space-y-5">
                    <div className="flex justify-between items-start">
                      <div className="space-y-1">
                        <h3 className="font-black text-indigo-950 text-sm uppercase tracking-tight">
                          {booking.location_name || 'Location Reserved'}
                        </h3>
                        <p className="text-[9px] font-black text-indigo-400/60 uppercase tracking-widest">Confirmed Schedule</p>
                      </div>
                      <div className="bg-indigo-50 text-indigo-600 text-[8px] font-black px-3 py-1.5 rounded-full uppercase tracking-widest border border-indigo-200">
                        {booking.status}
                      </div>
                    </div>
                    <div className="flex items-center gap-6">
                      <div className="flex items-center gap-2.5 text-[10px] text-indigo-900 font-black uppercase tracking-widest bg-indigo-50/50 px-4 py-2 rounded-full border border-indigo-100">
                        <svg className="w-3.5 h-3.5 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        {booking.shoot_date ? new Date(booking.shoot_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'long', year: 'numeric' }) : 'Schedule Pending'}
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
              {dashboardData.bookings.length === 0 && (
                <div className="p-20 text-center border-2 border-dashed border-gray-100 rounded-[32px] text-gray-200 text-[10px] font-black uppercase tracking-widest bg-gray-50/20">
                  Zero Confirmed Sets
                </div>
              )}
            </div>
          </section>
        </div>
      </div>

      {/* Side Panel Detail View */}
      {selectedLead && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/20 backdrop-blur-[2px] transition-all" onClick={() => setSelectedLead(null)} />
          <div className="relative w-full max-w-xl bg-white h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-500 ease-in-out">
            <div className="p-8 border-b border-gray-100 flex justify-between items-center bg-white">
              <div className="space-y-1">
                <h2 className="text-xl font-black text-gray-900 uppercase tracking-tight">{selectedLead.intake_data?.shoot_type || 'Production'}</h2>
                <p className="text-[10px] font-black text-primary uppercase tracking-[0.3em]">Project Manifest: {selectedLead.id.slice(0, 8)}</p>
              </div>
              <button onClick={() => setSelectedLead(null)} className="w-10 h-10 flex items-center justify-center bg-gray-50 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-900 transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-10 space-y-12">
              {/* Project Status */}
              <div className="space-y-6">
                <label className="text-[11px] font-black text-gray-400 uppercase tracking-[0.3em] border-b border-gray-50 pb-3 block">Real-time Status</label>
                <div className="p-6 bg-slate-50 rounded-3xl border border-slate-100 flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Current Pipeline Stage</p>
                    <p className="text-sm font-black text-slate-900 uppercase">{selectedLead.status.replace(/_/g, ' ')}</p>
                  </div>
                  <div className="w-10 h-10 rounded-full bg-white border border-slate-200 flex items-center justify-center shadow-sm">
                    <div className="w-3 h-3 rounded-full bg-primary animate-pulse" />
                  </div>
                </div>
              </div>

              {/* Requirements */}
              <div className="space-y-8">
                <label className="text-[11px] font-black text-gray-400 uppercase tracking-[0.3em] border-b border-gray-50 pb-3 block">Production Specs</label>
                <div className="space-y-6">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Requirements Brief</label>
                    <div className="p-6 bg-gray-50 rounded-2xl text-sm text-gray-700 leading-relaxed italic border border-gray-100 font-serif">
                      "{selectedLead.intake_data?.requirements}"
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-8">
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Budget Bracket</label>
                      <p className="text-sm font-bold text-gray-900">{selectedLead.intake_data?.budget || 'Custom Quote'}</p>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Target Crew</label>
                      <p className="text-sm font-bold text-gray-900">{selectedLead.intake_data?.crew_size || 'Scalable'}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* System History */}
              <div className="space-y-8">
                <label className="text-[11px] font-black text-gray-400 uppercase tracking-[0.3em] border-b border-gray-50 pb-3 block">Lifecycle History</label>
                <div className="space-y-6">
                  {selectedLead.workflow_history?.map((step, i) => (
                    <div key={i} className="flex gap-5 items-start relative">
                      {i < selectedLead.workflow_history.length - 1 && (
                        <div className="absolute left-[7px] top-4 bottom-[-24px] w-[1px] bg-gray-100" />
                      )}
                      <div className="mt-1.5 w-[15px] h-[15px] rounded-full border-2 border-primary bg-white flex-shrink-0 z-10" />
                      <div className="space-y-1">
                        <p className="text-xs font-black text-gray-900 uppercase tracking-tight">
                          {step.new_state.replace(/_/g, ' ')}
                        </p>
                        <p className="text-[10px] text-gray-500 font-bold uppercase tracking-tighter">
                          {new Date(step.created_at).toLocaleDateString('en-GB')} • {new Date(step.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="p-8 border-t border-gray-100 bg-gray-50/30">
              <p className="text-[10px] text-center text-gray-400 font-bold uppercase tracking-[0.2em]">Automated Intelligence in Progress</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ClientDashboard;
