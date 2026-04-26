import React, { useEffect, useState } from 'react';
import client from '../api/client';
import Card from '../components/Card';

const ClientDashboard = () => {
  const [dashboardData, setDashboardData] = useState({ leads: [], bookings: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
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
    fetchDashboard();
  }, []);

  if (loading) return <div className="p-8 text-center text-gray-500 text-sm">Loading your dashboard...</div>;
  
  if (error) {
    return (
      <div className="max-w-xl mx-auto p-6 bg-red-50 text-red-700 rounded-lg border border-red-100">
        <h2 className="font-bold mb-2">Access Error</h2>
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  const getStatusBadge = (status) => {
    const styles = {
      new: 'bg-blue-50 text-blue-700 border-blue-100',
      ready: 'bg-green-50 text-green-700 border-green-100',
      matched: 'bg-teal-50 text-teal-700 border-teal-100',
      booked: 'bg-indigo-50 text-indigo-700 border-indigo-100',
      default: 'bg-gray-50 text-gray-700 border-gray-100',
    };
    const style = styles[status] || styles.default;
    return (
      <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded-full border ${style}`}>
        {status.replace(/_/g, ' ')}
      </span>
    );
  };

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Client Dashboard</h1>
        <p className="text-sm text-gray-500">Track your shoot inquiries and active bookings.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        {/* Leads Section */}
        <section className="space-y-4">
          <div className="flex justify-between items-center px-1">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-widest">Active Leads</h2>
            <span className="text-xs text-gray-400">{dashboardData.leads.length} total</span>
          </div>
          
          <div className="space-y-3">
            {dashboardData.leads.map((lead) => (
              <Card key={lead.id} className="hover:border-primary/30 transition-colors">
                <div className="flex justify-between items-start gap-4">
                  <div className="space-y-1">
                    <h3 className="font-bold text-gray-900">{lead.intake_data?.shoot_type || 'General Shoot'}</h3>
                    <p className="text-xs text-gray-500 line-clamp-2">
                      {lead.intake_data?.requirements || 'No specific requirements provided.'}
                    </p>
                    <p className="text-[10px] text-gray-400 mt-2">
                      Submitted: {new Date(lead.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  {getStatusBadge(lead.status)}
                </div>
              </Card>
            ))}
            {dashboardData.leads.length === 0 && (
              <div className="p-8 text-center border-2 border-dashed border-gray-100 rounded-lg text-gray-400 text-xs italic">
                No active inquiries found.
              </div>
            )}
          </div>
        </section>

        {/* Bookings Section */}
        <section className="space-y-4">
          <div className="flex justify-between items-center px-1">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-widest">Confirmed Bookings</h2>
            <span className="text-xs text-gray-400">{dashboardData.bookings.length} total</span>
          </div>

          <div className="space-y-3">
            {dashboardData.bookings.map((booking) => (
              <Card key={booking.id} className="border-l-4 border-l-indigo-500">
                <div className="space-y-2">
                  <div className="flex justify-between items-start">
                    <h3 className="font-bold text-indigo-900">{booking.location_name || 'Location Reserved'}</h3>
                    <span className="bg-indigo-100 text-indigo-700 text-[10px] font-bold px-2 py-0.5 rounded uppercase">
                      {booking.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-600">
                    <div className="flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      {booking.shoot_date ? new Date(booking.shoot_date).toLocaleDateString() : 'TBD'}
                    </div>
                  </div>
                </div>
              </Card>
            ))}
            {dashboardData.bookings.length === 0 && (
              <div className="p-8 text-center border-2 border-dashed border-gray-100 rounded-lg text-gray-400 text-xs italic">
                No confirmed bookings yet.
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

export default ClientDashboard;
