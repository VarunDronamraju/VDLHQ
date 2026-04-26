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

  if (loading) return <div className="p-8 text-center text-gray-500 text-xs font-bold">LOADING PIPELINE...</div>;

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
    <div className="relative min-h-[calc(100vh-4rem)]">
      <div className="space-y-10 pb-20">
        <div className="flex justify-between items-end border-b border-gray-100 pb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Ops Pipeline</h1>
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-widest mt-0.5">High Density Queue</p>
          </div>
          <Button onClick={fetchPipeline} variant="secondary" className="text-[10px] font-black px-3 py-1.5 uppercase tracking-wider">
            Refresh
          </Button>
        </div>
        
        <div className="space-y-8">
          {STATUS_ORDER.map((statusKey) => {
            const leads = groupedLeads[statusKey] || [];
            const config = STATUS_CONFIG[statusKey] || { label: statusKey, color: 'border-gray-200', bg: 'bg-gray-50', text: 'text-gray-500' };
            
            return (
              <section key={statusKey} className="space-y-3">
                <div className="flex items-center gap-2 px-1">
                  <h2 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]">
                    {config.label}
                  </h2>
                  <span className={`${config.bg} ${config.text} text-[9px] font-black px-1.5 py-0.5 rounded`}>
                    {leads.length}
                  </span>
                </div>

                <div className="flex gap-2 overflow-x-auto pb-2 no-scrollbar">
                  {leads.map((lead) => {
                    const validTransitions = ALLOWED_TRANSITIONS[lead.status] || [];
                    return (
                      <div 
                        key={lead.id} 
                        onClick={() => openLeadDetail(lead.id)}
                        className="flex-shrink-0 w-64 group cursor-pointer"
                      >
                        <Card className={`!p-3 border-l-[3px] ${config.color} hover:bg-gray-50 transition-colors h-full flex flex-col justify-between shadow-none border border-gray-100`}>
                          <div className="space-y-2">
                            <div className="flex justify-between items-start gap-2">
                              <h3 className="font-bold text-gray-900 text-xs truncate w-full">
                                {lead.intake_data?.contact?.name}
                              </h3>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-[9px] font-black text-gray-400 uppercase tracking-wider">
                                {lead.intake_data?.shoot_type}
                              </span>
                              <span className="text-[8px] text-gray-300 font-bold">
                                {new Date(lead.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
                              </span>
                            </div>
                            <p className="text-[10px] text-gray-500 line-clamp-1 italic">
                              {lead.intake_data?.requirements}
                            </p>
                          </div>

                          <div className="mt-3 flex flex-wrap gap-1">
                            {validTransitions.map((target) => (
                              <button
                                key={target}
                                onClick={(e) => handleAction(e, lead.id, target)}
                                className="px-2 py-0.5 bg-white hover:bg-primary hover:text-white border border-gray-200 rounded text-[8px] font-black text-gray-400 uppercase tracking-tighter transition-all"
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
                    <div className="flex-shrink-0 w-48 h-20 border border-dashed border-gray-100 rounded-lg flex items-center justify-center text-gray-200 text-[9px] font-black uppercase tracking-widest bg-gray-50/20">
                      Empty
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
          <div className="absolute inset-0 bg-black/10 backdrop-blur-[1px]" onClick={() => setSelectedLead(null)} />
          <div className="relative w-full max-w-lg bg-white h-full shadow-2xl border-l border-gray-100 flex flex-col animate-in slide-in-from-right duration-300">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
              <div>
                <h2 className="text-lg font-bold text-gray-900">{selectedLead.intake_data?.contact?.name}</h2>
                <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Lead ID: {selectedLead.id.slice(0, 8)}</p>
              </div>
              <button onClick={() => setSelectedLead(null)} className="text-gray-400 hover:text-gray-900 p-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-8 space-y-10">
              {/* Core Info */}
              <div className="grid grid-cols-2 gap-8">
                <div className="space-y-1">
                  <label className="text-[9px] font-black text-gray-400 uppercase tracking-widest">Email</label>
                  <p className="text-sm font-medium text-gray-900">{selectedLead.intake_data?.contact?.email}</p>
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] font-black text-gray-400 uppercase tracking-widest">Shoot Type</label>
                  <p className="text-sm font-medium text-gray-900 capitalize">{selectedLead.intake_data?.shoot_type}</p>
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] font-black text-gray-400 uppercase tracking-widest">Created At</label>
                  <p className="text-sm font-medium text-gray-900">{new Date(selectedLead.created_at).toLocaleString()}</p>
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] font-black text-gray-400 uppercase tracking-widest">Status</label>
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-primary" />
                    <p className="text-sm font-bold text-gray-900 uppercase tracking-tighter">{selectedLead.status}</p>
                  </div>
                </div>
              </div>

              {/* Requirements */}
              <div className="space-y-2">
                <label className="text-[9px] font-black text-gray-400 uppercase tracking-widest">Full Requirements</label>
                <div className="p-4 bg-gray-50 rounded-lg text-sm text-gray-700 leading-relaxed italic border border-gray-100">
                  "{selectedLead.intake_data?.requirements}"
                </div>
              </div>

              {/* Workflow History */}
              <div className="space-y-6">
                <label className="text-[9px] font-black text-gray-400 uppercase tracking-widest">Workflow Timeline</label>
                <div className="space-y-4">
                  {selectedLead.workflow_history?.map((step, i) => (
                    <div key={i} className="flex gap-4 items-start">
                      <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-gray-300 flex-shrink-0" />
                      <div className="space-y-1">
                        <p className="text-xs font-bold text-gray-900">
                          {step.new_state.replace(/_/g, ' ')}
                        </p>
                        <p className="text-[10px] text-gray-500">
                          {step.trigger} • {new Date(step.created_at).toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Communication Logs */}
              <div className="space-y-6">
                <label className="text-[9px] font-black text-gray-400 uppercase tracking-widest">System Communications</label>
                <div className="space-y-4">
                  {selectedLead.communications?.length > 0 ? selectedLead.communications.map((log, i) => (
                    <div key={i} className="p-3 border border-gray-100 rounded-md bg-white flex justify-between items-center">
                      <div>
                        <p className="text-xs font-bold text-gray-900">{log.template_name}</p>
                        <p className="text-[9px] text-gray-400 uppercase font-bold">{log.channel} • {log.status}</p>
                      </div>
                      <span className="text-[9px] text-gray-400">{new Date(log.sent_at).toLocaleDateString()}</span>
                    </div>
                  )) : (
                    <p className="text-[10px] text-gray-300 italic">No automated communications logged.</p>
                  )}
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-gray-100 bg-gray-50/50">
              <label className="text-[9px] font-black text-gray-400 uppercase tracking-widest block mb-4">Manual Override</label>
              <div className="flex flex-wrap gap-2">
                {ALLOWED_TRANSITIONS[selectedLead.status]?.map((target) => (
                  <button
                    key={target}
                    onClick={(e) => handleAction(e, selectedLead.id, target)}
                    className="px-4 py-2 bg-primary text-white rounded text-xs font-bold shadow-sm hover:opacity-90 transition-opacity"
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
  );
};

export default OpsDashboard;
