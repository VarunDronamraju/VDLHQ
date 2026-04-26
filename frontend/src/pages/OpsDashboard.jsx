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
      setPipeline(response.data.leads || []);
    } catch (error) {
      console.error('Fetch pipeline error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPipeline();
  }, []);

  const handleAction = async (leadId, action) => {
    try {
      await client.post(`/api/v1/ops/leads/${leadId}/action`, { action });
      fetchPipeline(); // Refresh
    } catch (error) {
      console.error('Action error:', error);
      alert('Failed to perform action');
    }
  };

  if (loading) return <div>Loading pipeline...</div>;

  const groupedLeads = pipeline.reduce((acc, lead) => {
    const status = lead.status || 'unknown';
    if (!acc[status]) acc[status] = [];
    acc[status].push(lead);
    return acc;
  }, {});

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Operations Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Object.entries(groupedLeads).map(([status, leads]) => (
          <div key={status} className="flex flex-col gap-4">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider px-2">
              {status} ({leads.length})
            </h2>
            {leads.map((lead) => (
              <Card key={lead.id} className="!p-4 space-y-4">
                <div>
                  <h3 className="font-medium text-gray-900">{lead.name}</h3>
                  <p className="text-sm text-gray-500 truncate">{lead.shoot_type}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button 
                    variant="secondary" 
                    className="text-xs !px-2 !py-1"
                    onClick={() => handleAction(lead.id, 'match')}
                  >
                    Match
                  </Button>
                  <Button 
                    variant="teal" 
                    className="text-xs !px-2 !py-1"
                    onClick={() => handleAction(lead.id, 'book')}
                  >
                    Book
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

export default OpsDashboard;
