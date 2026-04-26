import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import client from '../api/client';
import Button from '../components/Button';
import Input from '../components/Input';
import Card from '../components/Card';

const Inquiry = () => {
  const { state } = useLocation();
  const context = state?.context; // { type: "location" | "production_reference", data: {...} }

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    company: '',
    role: '',
    shoot_type: '',
    requirements: '',
    budget: '',
  });

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  useEffect(() => {
    const savedName = localStorage.getItem('user_name');
    const savedEmail = localStorage.getItem('user_email');
    if (savedName || savedEmail) {
      setFormData(prev => ({ ...prev, name: savedName || '', email: savedEmail || '' }));
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const payload = {
        contact: {
          name: formData.name,
          email: formData.email,
          phone: formData.phone,
        },
        client_profile: {
          company: formData.company,
          role: formData.role,
        },
        // Real structured context propagation
        context: context || null, 
        shoot_type: formData.shoot_type,
        requirements: formData.requirements,
        budget: formData.budget,
      };

      await client.post('/api/v1/inquiry', payload);
      
      localStorage.setItem('user_name', formData.name);
      localStorage.setItem('user_email', formData.email);

      setMessage({ type: 'success', text: 'Inquiry submitted! Our team will reach out shortly.' });
      setFormData({ name: '', email: '', phone: '', company: '', role: '', shoot_type: '', requirements: '', budget: '' });
    } catch (error) {
      console.error('Inquiry error:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Something went wrong.';
      setMessage({ type: 'error', text: typeof errorMsg === 'string' ? errorMsg : 'Failed to submit.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-12 py-10 px-6">
      <div className="text-center space-y-4">
        <div className="inline-flex items-center gap-3 px-4 py-1 bg-primary/5 border border-primary/10 rounded-full">
          <span className="text-[9px] font-black text-primary uppercase tracking-[0.3em]">
            {context?.type === 'location' ? 'Location Specific Inquiry' : 
             context?.type === 'production_reference' ? 'Production Reference Inquiry' : 
             'General Discovery'}
          </span>
        </div>
        <h1 className="text-4xl md:text-5xl font-serif text-gray-900 leading-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
          {context?.type === 'location' ? 'Secure Your Set' : 
           context?.type === 'production_reference' ? 'Production Brief' : 
           'Inquiry Studio'}
        </h1>
        <p className="text-gray-500 text-sm max-w-md mx-auto">
          {context?.type === 'location' ? `Finalizing requirements for ${context.data.name}.` :
           context?.type === 'production_reference' ? `Exploring a similar aesthetic to ${context.data.name}.` :
           'Share your production vision. Our agents will architect the strategy.'}
        </p>
      </div>

      {context && (
        <Card className="!p-6 bg-primary/5 border-primary/10 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="space-y-1 text-center md:text-left">
            <p className="text-[10px] font-black text-primary uppercase tracking-widest">
              {context.type === 'location' ? 'Selected Location' : 'Referencing Production'}
            </p>
            <h3 className="text-xl font-serif text-gray-900" style={{ fontFamily: "'Playfair Display', serif" }}>
              {context.data.name}
            </h3>
          </div>
          <div className="flex gap-8">
            {context.type === 'location' ? (
              <>
                <div className="text-center">
                  <p className="text-[9px] font-black text-gray-400 uppercase tracking-tighter">Capacity</p>
                  <p className="text-xs font-bold text-gray-700">{context.data.crew_capacity} Pax</p>
                </div>
                <div className="text-center">
                  <p className="text-[9px] font-black text-gray-400 uppercase tracking-tighter">Rate</p>
                  <p className="text-xs font-bold text-gray-700">£{context.data.price_per_day?.toLocaleString()}/Day</p>
                </div>
              </>
            ) : (
              <>
                <div className="text-center">
                  <p className="text-[9px] font-black text-gray-400 uppercase tracking-tighter">Studio</p>
                  <p className="text-xs font-bold text-gray-700">{context.data.house}</p>
                </div>
                <div className="text-center">
                  <p className="text-[9px] font-black text-gray-400 uppercase tracking-tighter">Year</p>
                  <p className="text-xs font-bold text-gray-700">{context.data.year}</p>
                </div>
              </>
            )}
          </div>
        </Card>
      )}

      <Card className="p-10 border-gray-100 shadow-2xl shadow-gray-100/50">
        <form onSubmit={handleSubmit} className="space-y-10">
          <div className="space-y-6">
            <h2 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] border-b border-gray-50 pb-2">Client Identity</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Input
                label="Full Name"
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
              <Input
                label="Work Email"
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
              />
              <Input
                label="Phone Number"
                id="phone"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                required
              />
              <Input
                label="Company / Studio"
                id="company"
                value={formData.company}
                onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] border-b border-gray-50 pb-2">Production Specs</h2>
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Input
                  label="Shoot Type"
                  id="shoot_type"
                  value={formData.shoot_type}
                  onChange={(e) => setFormData({ ...formData, shoot_type: e.target.value })}
                  placeholder="e.g. Commercial"
                  required
                />
                <Input
                  label="Est. Budget (Optional)"
                  id="budget"
                  value={formData.budget}
                  onChange={(e) => setFormData({ ...formData, budget: e.target.value })}
                  placeholder="e.g. £5,000"
                />
              </div>
              
              <div className="space-y-2">
                <label htmlFor="requirements" className="text-[11px] font-bold text-gray-700 uppercase tracking-wider">
                  Requirements & Production Notes
                </label>
                <textarea
                  id="requirements"
                  value={formData.requirements}
                  onChange={(e) => setFormData({ ...formData, requirements: e.target.value })}
                  placeholder="Describe the desired aesthetic, dates, and logistics..."
                  className="w-full px-4 py-4 border border-gray-100 rounded-xl focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-sm min-h-[160px] resize-none bg-gray-50/30"
                  required
                />
              </div>
            </div>
          </div>

          {message.text && (
            <div className={`p-4 rounded-xl text-sm font-bold tracking-tight text-center ${
              message.type === 'success' ? 'bg-teal-50 text-teal-800 border border-teal-100' : 'bg-red-50 text-red-800 border border-red-100'
            }`}>
              {message.text}
            </div>
          )}

          <Button 
            type="submit" 
            disabled={loading} 
            className="w-full h-14 text-sm font-black uppercase tracking-[0.2em] transition-all hover:scale-[1.01] active:scale-[0.99] shadow-xl shadow-primary/20"
          >
            {loading ? 'Transmitting Specs...' : 'Initialize Inquiry'}
          </Button>
        </form>
      </Card>
    </div>
  );
};

export default Inquiry;
