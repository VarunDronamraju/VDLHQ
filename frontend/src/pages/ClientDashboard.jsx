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
    <div className="space-y-12 max-w-5xl mx-auto">
      <div className="border-b border-gray-100 pb-8">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Client Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Track your production inquiries and confirmed bookings.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        {/* Leads Section */}
        <section className="space-y-6">
          <div className="flex justify-between items-center px-1">
            <h2 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">Active Inquiries</h2>
            <span className="bg-gray-100 text-gray-500 text-[10px] font-black px-2 py-0.5 rounded-full">
              {dashboardData.leads.length}
            </span>
          </div>
          
          <div className="space-y-4">
            {dashboardData.leads.map((lead) => (
              <Card key={lead.id} className="hover:border-primary/20 transition-all hover:shadow-sm">
                <div className="flex justify-between items-start gap-6">
                  <div className="space-y-2">
                    <h3 className="font-bold text-gray-900 text-sm leading-tight">
                      {lead.intake_data?.shoot_type || 'Production'}
                    </h3>
                    <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">
                      {lead.intake_data?.requirements || 'Pending detailed requirements.'}
                    </p>
                    <div className="flex items-center gap-2 text-[10px] text-gray-400 font-medium">
                      <span>Submitted</span>
                      <span className="w-1 h-1 bg-gray-200 rounded-full" />
                      <span>{new Date(lead.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  {getStatusBadge(lead.status)}
                </div>
              </Card>
            ))}
            {dashboardData.leads.length === 0 && (
              <div className="p-10 text-center border-2 border-dashed border-gray-100 rounded-xl text-gray-300 text-[10px] font-bold uppercase tracking-widest italic bg-gray-50/50">
                No active inquiries
              </div>
            )}
          </div>
        </section>

        {/* Bookings Section */}
        <section className="space-y-6">
          <div className="flex justify-between items-center px-1">
            <h2 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">Confirmed Bookings</h2>
            <span className="bg-indigo-50 text-indigo-500 text-[10px] font-black px-2 py-0.5 rounded-full">
              {dashboardData.bookings.length}
            </span>
          </div>

          <div className="space-y-4">
            {dashboardData.bookings.map((booking) => (
              <Card key={booking.id} className="border-l-4 border-l-indigo-500 hover:shadow-sm transition-all">
                <div className="space-y-3">
                  <div className="flex justify-between items-start">
                    <h3 className="font-bold text-indigo-950 text-sm leading-tight">
                      {booking.location_name || 'Location Reserved'}
                    </h3>
                    <span className="bg-indigo-50 text-indigo-600 text-[9px] font-black px-2 py-1 rounded uppercase tracking-wider">
                      {booking.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 text-[11px] text-indigo-900/60 font-semibold bg-indigo-50/50 px-2 py-1 rounded">
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      {booking.shoot_date ? new Date(booking.shoot_date).toLocaleDateString() : 'Date TBD'}
                    </div>
                  </div>
                </div>
              </Card>
            ))}
            {dashboardData.bookings.length === 0 && (
              <div className="p-10 text-center border-2 border-dashed border-gray-100 rounded-xl text-gray-300 text-[10px] font-bold uppercase tracking-widest italic bg-gray-50/50">
                No bookings yet
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

export default ClientDashboard;
