import React, { useEffect, useState } from 'react';
import client from '../api/client';
import Card from '../components/Card';
import Button from '../components/Button';

const OpsDashboard = () => {
  const [pipeline, setPipeline] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedLead, setSelectedLead] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchPipeline = async () => {
    try {
      const response = await client.get('/api/v1/ops/pipeline');
      setPipeline(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Fetch pipeline error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPipeline();
  }, []);

  const handleAction = async (e, leadId, targetState) => {
    e.stopPropagation(); // Don't trigger card click
    try {
      const payload = {
        target_state: targetState,
        trigger: "manual_ops_action",
        actor: "ops"
      };

      if (targetState === 'booked') {
        payload.metadata = { location_id: "00000000-0000-0000-0000-000000000001" }; 
      }

      await client.post(`/api/v1/ops/leads/${leadId}/action`, payload);
      fetchPipeline();
      if (selectedLead?.id === leadId) setSelectedLead(null);
    } catch (error) {
      console.error('Action error:', error);
      alert(`Error: ${error.response?.data?.detail || 'Transition failed'}`);
    }
  };

  const openLeadDetail = async (leadId) => {
    setDetailLoading(true);
    try {
      const response = await client.get(`/api/v1/ops/leads/${leadId}`);
      setSelectedLead(response.data);
    } catch (error) {
      console.error('Fetch lead detail error:', error);
    } finally {
      setDetailLoading(false);
    }
  };

  if (loading) return <div className="p-20 text-center text-gray-400 text-[10px] font-black uppercase tracking-[0.3em] animate-pulse">Synchronizing Pipeline...</div>;

  const ALLOWED_TRANSITIONS = {
    "new": ["needs_info", "ready"],
    "needs_info": ["ready", "inactive"],
    "ready": ["matching_in_progress"],
    "matching_in_progress": ["needs_clarification", "matched", "manual_review"],
    "needs_clarification": ["matching_in_progress"],
    "matched": ["ready", "booked", "inactive"],
    "booked": ["permit_pending"],
    "permit_pending": ["permit_submitted"],
    "permit_submitted": ["permit_in_review"],
    "permit_in_review": ["permit_approved", "permit_rejected"],
    "permit_rejected": ["permit_pending"],
    "permit_approved": ["coordination"],
    "coordination": ["closed"],
    "inactive": ["needs_info", "archived"],
    "manual_review": ["ready"],
    "archived": [],
    "closed": [],
  };

  const STATUS_CONFIG = {
    new: { label: 'New', color: 'border-gray-300', bg: 'bg-gray-50', text: 'text-gray-500' },
    needs_info: { label: 'Needs Info', color: 'border-yellow-400', bg: 'bg-yellow-50', text: 'text-yellow-700' },
    ready: { label: 'Ready', color: 'border-blue-400', bg: 'bg-blue-50', text: 'text-blue-700' },
    matching_in_progress: { label: 'Matching', color: 'border-purple-400', bg: 'bg-purple-50', text: 'text-purple-700' },
    matched: { label: 'Matched', color: 'border-green-400', bg: 'bg-green-50', text: 'text-green-700' },
    booked: { label: 'Booked', color: 'border-emerald-600', bg: 'bg-emerald-50', text: 'text-emerald-800' },
    permit_pending: { label: 'Permit', color: 'border-orange-400', bg: 'bg-orange-50', text: 'text-orange-700' },
    permit_submitted: { label: 'Submitted', color: 'border-orange-500', bg: 'bg-orange-100', text: 'text-orange-800' },
    permit_approved: { label: 'Approved', color: 'border-teal-500', bg: 'bg-teal-50', text: 'text-teal-700' },
    coordination: { label: 'Coord', color: 'border-indigo-400', bg: 'bg-indigo-50', text: 'text-indigo-700' },
    closed: { label: 'Closed', color: 'border-gray-200', bg: 'bg-gray-50', text: 'text-gray-400' },
    inactive: { label: 'Inactive', color: 'border-red-200', bg: 'bg-red-50', text: 'text-red-400' },
  };

  const groupedLeads = pipeline.reduce((acc, lead) => {
    const status = lead.status || 'unknown';
    if (!acc[status]) acc[status] = [];
    acc[status].push(lead);
    return acc;
  }, {});

  const STATUS_ORDER = [
    "new", "needs_info", "ready", "matching_in_progress", "matched", 
    "booked", "permit_pending", "permit_submitted", "permit_approved", 
    "coordination", "closed", "inactive"
  ];

  return (
    <div className="max-w-[1400px] mx-auto px-6 md:px-10 py-12">
      <div className="relative min-h-[calc(100vh-12rem)]">
        <div className="space-y-12 pb-20">
          <div className="flex justify-between items-end border-b border-gray-100 pb-8">
            <div className="space-y-1">
              <h1 className="text-3xl font-black text-gray-900 tracking-tight uppercase">Ops Pipeline</h1>
              <p className="text-gray-400 text-[10px] font-black uppercase tracking-[0.3em]">High Density Operational Queue</p>
            </div>
            <Button onClick={fetchPipeline} variant="secondary" className="text-[9px] font-black px-4 py-2 uppercase tracking-widest bg-gray-50 hover:bg-gray-100 border-none shadow-none text-gray-600">
              Refresh Feed
            </Button>
          </div>
          
          <div className="space-y-10">
            {STATUS_ORDER.map((statusKey) => {
              const leads = groupedLeads[statusKey] || [];
              const config = STATUS_CONFIG[statusKey] || { label: statusKey, color: 'border-gray-200', bg: 'bg-gray-50', text: 'text-gray-500' };
              
              return (
                <section key={statusKey} className="space-y-4">
                  <div className="flex items-center gap-3 px-1">
                    <h2 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.25em]">
                      {config.label}
                    </h2>
                    <span className={`${config.bg} ${config.text} text-[9px] font-black px-2 py-0.5 rounded-full border border-current opacity-60`}>
                      {leads.length}
                    </span>
                  </div>

                  <div className="flex gap-4 overflow-x-auto pb-4 no-scrollbar">
                    {leads.map((lead) => {
                      const validTransitions = ALLOWED_TRANSITIONS[lead.status] || [];
                      const contact = lead.intake_data?.contact || {};
                      const profile = lead.intake_data?.client_profile || {};

                      return (
                        <div 
                          key={lead.id} 
                          onClick={() => openLeadDetail(lead.id)}
                          className="flex-shrink-0 w-80 group cursor-pointer"
                        >
                          <Card className={`!p-5 border-l-[4px] ${config.color} hover:bg-white hover:shadow-xl hover:shadow-gray-200/50 transition-all duration-300 h-full flex flex-col justify-between shadow-sm border border-gray-100 bg-white/50`}>
                            <div className="space-y-4">
                              <div className="space-y-1.5">
                                {lead.intake_data?.context?.type === 'location' && (
                                  <p className="text-[9px] font-black text-primary uppercase tracking-[0.2em] mb-1">
                                    {lead.intake_data.context.data.name}
                                  </p>
                                )}
                                {lead.intake_data?.context?.type === 'production_reference' && (
                                  <p className="text-[9px] font-black text-indigo-500 uppercase tracking-[0.2em] mb-1">
                                    Ref: {lead.intake_data.context.data.name}
                                  </p>
                                )}
                                <h3 className="font-black text-gray-900 text-sm truncate leading-tight">
                                  {contact.name || 'Anonymous'}
                                </h3>
                                <p className="text-[9px] font-bold text-gray-400 uppercase tracking-tight truncate">
                                  {profile.company || 'Private Client'}
                                </p>
                              </div>

                              <div className="space-y-1.5">
                                <div className="flex items-center gap-2 text-[10px] text-gray-500">
                                  <div className="w-4 flex justify-center"><svg className="w-3 h-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg></div>
                                  <span className="truncate">{contact.email}</span>
                                </div>
                                <div className="flex items-center gap-2 text-[10px] text-gray-500">
                                  <div className="w-4 flex justify-center"><svg className="w-3 h-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" /></svg></div>
                                  <span>{contact.phone || 'N/A'}</span>
                                </div>
                              </div>

                              <div className="flex items-center justify-between pt-3 border-t border-gray-50">
                                <span className="text-[10px] font-black text-primary uppercase tracking-wider">
                                  {lead.intake_data?.shoot_type}
                                </span>
                                <span className="text-[9px] text-gray-300 font-bold">
                                  {new Date(lead.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
                                </span>
                              </div>
                            </div>

                            <div className="mt-5 flex flex-wrap gap-1.5">
                              {validTransitions.map((target) => (
                                <button
                                  key={target}
                                  onClick={(e) => handleAction(e, lead.id, target)}
                                  className="px-2.5 py-1 bg-gray-50 hover:bg-primary hover:text-white border border-gray-100 rounded text-[9px] font-black text-gray-500 uppercase tracking-tighter transition-all"
                                >
                                  {target.replace(/_/g, ' ')}
                                </button>
                              ))}
                            </div>
                          </Card>
                        </div>
                      );
                    })}
                    {leads.length === 0 && (
                      <div className="flex-shrink-0 w-48 h-24 border border-dashed border-gray-100 rounded-2xl flex items-center justify-center text-gray-200 text-[9px] font-black uppercase tracking-widest bg-gray-50/20">
                        Zero Leads
                      </div>
                    )}
                  </div>
                </section>
              );
            })}
          </div>
        </div>

        {/* Side Panel Detail View */}
        {selectedLead && (
          <div className="fixed inset-0 z-50 flex justify-end">
            <div className="absolute inset-0 bg-black/20 backdrop-blur-[2px] transition-all" onClick={() => setSelectedLead(null)} />
            <div className="relative w-full max-w-xl bg-white h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-500 ease-in-out">
              <div className="p-8 border-b border-gray-100 flex justify-between items-center bg-white">
                <div className="space-y-1">
                  <h2 className="text-xl font-black text-gray-900 uppercase tracking-tight">{selectedLead.intake_data?.contact?.name}</h2>
                  <p className="text-[10px] font-black text-primary uppercase tracking-[0.3em]">Operational Lead File: {selectedLead.id.slice(0, 8)}</p>
                </div>
                <button onClick={() => setSelectedLead(null)} className="w-10 h-10 flex items-center justify-center bg-gray-50 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-900 transition-colors">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-10 space-y-12 custom-scrollbar">
                {/* Client Profile */}
                <div className="space-y-8">
                  <label className="text-[11px] font-black text-gray-400 uppercase tracking-[0.3em] border-b border-gray-50 pb-3 block">Client Profile</label>
                  <div className="grid grid-cols-2 gap-y-8 gap-x-6">
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Full Name</label>
                      <p className="text-sm font-bold text-gray-900">{selectedLead.intake_data?.contact?.name}</p>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Work Email</label>
                      <p className="text-sm font-bold text-gray-900">{selectedLead.intake_data?.contact?.email}</p>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Phone</label>
                      <p className="text-sm font-bold text-gray-900">{selectedLead.intake_data?.contact?.phone || 'N/A'}</p>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Company</label>
                      <p className="text-sm font-bold text-gray-900">{selectedLead.intake_data?.client_profile?.company || 'N/A'}</p>
                    </div>
                  </div>
                </div>

                {/* Project Requirements */}
                <div className="space-y-8">
                  <label className="text-[11px] font-black text-gray-400 uppercase tracking-[0.3em] border-b border-gray-50 pb-3 block">Production Brief</label>
                  <div className="space-y-6">
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Shoot Type</label>
                      <p className="text-sm font-bold text-gray-900 capitalize">{selectedLead.intake_data?.shoot_type}</p>
                    </div>
                    <div className="space-y-2">
                      <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Requirements</label>
                      <div className="p-6 bg-gray-50 rounded-2xl text-sm text-gray-700 leading-relaxed italic border border-gray-100 font-serif">
                        "{selectedLead.intake_data?.requirements}"
                      </div>
                    </div>
                  </div>
                </div>

                {/* Timeline */}
                <div className="space-y-8">
                  <label className="text-[11px] font-black text-gray-400 uppercase tracking-[0.3em] border-b border-gray-50 pb-3 block">System Timeline</label>
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
                            Triggered by {step.actor} via {step.trigger} • {new Date(step.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="p-8 border-t border-gray-100 bg-gray-50/30">
                <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest block mb-5">Workflow Actions</label>
                <div className="flex flex-wrap gap-3">
                  {ALLOWED_TRANSITIONS[selectedLead.status]?.map((target) => (
                    <button
                      key={target}
                      onClick={(e) => handleAction(e, selectedLead.id, target)}
                      className="px-6 py-3 bg-gray-900 text-white rounded-full text-[10px] font-black uppercase tracking-widest shadow-xl shadow-gray-200 hover:bg-primary transition-all active:scale-95"
                    >
                      Move to {target.replace(/_/g, ' ')}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OpsDashboard;
