import React, { useEffect, useState } from 'react';
import client from '../api/client';
import Card from '../components/Card';

const ClientDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const response = await client.get('/api/v1/client/dashboard');
        setDashboardData(response.data);
      } catch (error) {
        console.error('Fetch dashboard error:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, []);

  if (loading) return <div>Loading your dashboard...</div>;
  if (!dashboardData) return <div>No data available.</div>;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Your Shoots</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <h2 className="text-lg font-semibold text-gray-700 mb-4">Active Leads</h2>
          <div className="space-y-4">
            {dashboardData.leads?.map((lead) => (
              <Card key={lead.id}>
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-bold">{lead.shoot_type}</h3>
                    <p className="text-sm text-gray-500">{lead.requirements}</p>
                  </div>
                  <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 uppercase">
                    {lead.status}
                  </span>
                </div>
              </Card>
            ))}
            {(!dashboardData.leads || dashboardData.leads.length === 0) && (
              <p className="text-gray-500 italic">No active leads.</p>
            )}
          </div>
        </div>
        <div>
          <h2 className="text-lg font-semibold text-gray-700 mb-4">Confirmed Bookings</h2>
          <div className="space-y-4">
            {dashboardData.bookings?.map((booking) => (
              <Card key={booking.id}>
                <h3 className="font-bold">{booking.shoot_name}</h3>
                <p className="text-sm text-gray-500">{booking.date}</p>
                <div className="mt-2 text-primary font-medium">Status: Confirmed</div>
              </Card>
            ))}
            {(!dashboardData.bookings || dashboardData.bookings.length === 0) && (
              <p className="text-gray-500 italic">No confirmed bookings yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClientDashboard;
