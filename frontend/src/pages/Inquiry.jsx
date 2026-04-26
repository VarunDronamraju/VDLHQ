import React, { useState } from 'react';
import client from '../api/client';
import Button from '../components/Button';
import Input from '../components/Input';
import Card from '../components/Card';

const Inquiry = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    shoot_type: '',
    requirements: '',
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const payload = {
        contact: {
          name: formData.name,
          email: formData.email,
        },
        shoot_type: formData.shoot_type,
        requirements: formData.requirements,
      };
      const response = await client.post('/api/v1/inquiry', payload);
      setMessage({ type: 'success', text: 'Inquiry submitted! Our team will reach out shortly.' });
      setFormData({ name: '', email: '', shoot_type: '', requirements: '' });
    } catch (error) {
      console.error('Inquiry error:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Something went wrong. Please try again.';
      setMessage({ type: 'error', text: typeof errorMsg === 'string' ? errorMsg : 'Failed to submit inquiry.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto space-y-8">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Start an Inquiry</h1>
        <p className="text-gray-500">Tell us about your production and we'll find the perfect location.</p>
      </div>

      <Card className="p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <Input
            label="Name"
            id="name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Production Lead Name"
            required
            className="text-sm"
          />
          <Input
            label="Email"
            id="email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            placeholder="work@production.com"
            required
            className="text-sm"
          />
          <Input
            label="Shoot Type"
            id="shoot_type"
            value={formData.shoot_type}
            onChange={(e) => setFormData({ ...formData, shoot_type: e.target.value })}
            placeholder="e.g. Fashion, Commercial, Feature Film"
            required
            className="text-sm"
          />
          
          <div className="space-y-2">
            <label htmlFor="requirements" className="text-sm font-semibold text-gray-700">
              Requirements
            </label>
            <textarea
              id="requirements"
              value={formData.requirements}
              onChange={(e) => setFormData({ ...formData, requirements: e.target.value })}
              placeholder="Tell us about the space, duration, and any specific needs..."
              className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-sm min-h-[140px] resize-none"
              required
            />
          </div>

          {message.text && (
            <div className={`p-4 rounded-lg text-sm font-medium ${
              message.type === 'success' ? 'bg-teal-50 text-teal-700' : 'bg-red-50 text-red-700'
            }`}>
              {message.text}
            </div>
          )}

          <Button 
            type="submit" 
            disabled={loading} 
            className="w-full h-12 text-sm font-bold tracking-wide transition-transform active:scale-[0.98]"
          >
            {loading ? 'Sending Inquiry...' : 'Submit Inquiry'}
          </Button>
        </form>
      </Card>
    </div>
  );
};

export default Inquiry;
