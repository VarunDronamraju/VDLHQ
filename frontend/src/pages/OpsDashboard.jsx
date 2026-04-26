import React, { useEffect, useState } from 'react';
import client from '../api/client';
import Card from '../components/Card';
import Button from '../components/Button';

const OpsDashboard = () => {
  const [pipeline, setPipeline] = useState([]);
  const [loading, setLoading] = useState(true);

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

  const handleAction = async (leadId, targetState) => {
    try {
      // For 'booked', we need a location_id metadata. 
      // For now, if user selects booked, we'll send a dummy location_id if none exists
      // or handle it gracefully.
      const payload = {
        target_state: targetState,
        trigger: "manual_ops_action",
        actor: "ops"
      };

      // Special case for booked (requires location_id in metadata)
      if (targetState === 'booked') {
        payload.metadata = { location_id: "00000000-0000-0000-0000-000000000000" }; // Placeholder
      }

      await client.post(`/api/v1/ops/leads/${leadId}/action`, payload);
      fetchPipeline(); // Refresh
    } catch (error) {
      console.error('Action error:', error);
      const msg = error.response?.data?.detail || 'Failed to transition state';
      alert(`Error: ${typeof msg === 'string' ? msg : JSON.stringify(msg)}`);
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">Loading pipeline...</div>;

  const STATUSES = [
    "new", "needs_info", "ready", "matching_in_progress", "matched", 
    "booked", "permit_pending", "permit_submitted", "permit_approved", 
    "coordination", "closed", "inactive"
  ];

  const groupedLeads = pipeline.reduce((acc, lead) => {
    const status = lead.status || 'unknown';
    if (!acc[status]) acc[status] = [];
    acc[status].push(lead);
    return acc;
  }, {});

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Operations Dashboard</h1>
        <Button onClick={fetchPipeline} variant="secondary" className="text-sm">Refresh</Button>
      </div>
      
      <div className="flex gap-6 overflow-x-auto pb-4 items-start">
        {STATUSES.map((status) => {
          const leads = groupedLeads[status] || [];
          return (
            <div key={status} className="flex-shrink-0 w-80 flex flex-col gap-4">
              <div className="flex justify-between items-center px-2">
                <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  {status.replace(/_/g, ' ')}
                </h2>
                <span className="bg-gray-200 text-gray-700 text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                  {leads.length}
                </span>
              </div>
              <div className="flex flex-col gap-3 min-h-[100px]">
                {leads.map((lead) => (
                  <Card key={lead.id} className="!p-4 space-y-3 border-l-4 border-l-primary">
                    <div>
                      <h3 className="font-bold text-gray-900 text-sm">{lead.contact?.name || 'Unknown'}</h3>
                      <p className="text-xs text-gray-500">{lead.shoot_type}</p>
                    </div>
                    
                    <div className="flex flex-col gap-2">
                      <label className="text-[10px] font-bold text-gray-400 uppercase">Transition to:</label>
                      <select 
                        className="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-primary"
                        onChange={(e) => handleAction(lead.id, e.target.value)}
                        value={status}
                      >
                        <option disabled value={status}>-- Select State --</option>
                        {STATUSES.filter(s => s !== status).map(s => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                  </Card>
                ))}
                {leads.length === 0 && (
                  <div className="border-2 border-dashed border-gray-200 rounded-lg h-24 flex items-center justify-center text-gray-300 text-xs italic">
                    Empty
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default OpsDashboard;
