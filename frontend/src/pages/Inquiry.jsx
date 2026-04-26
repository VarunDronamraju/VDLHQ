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
      setMessage({ type: 'success', text: 'Inquiry submitted successfully!' });
      setFormData({ name: '', email: '', shoot_type: '', requirements: '' });
    } catch (error) {
      console.error('Inquiry error:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to submit inquiry.';
      setMessage({ type: 'error', text: typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <Card title="Shoot Inquiry Form">
        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          <Input
            label="Name"
            id="name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Your full name"
            required
          />
          <Input
            label="Email"
            id="email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            placeholder="your@email.com"
            required
          />
          <Input
            label="Shoot Type"
            id="shoot_type"
            value={formData.shoot_type}
            onChange={(e) => setFormData({ ...formData, shoot_type: e.target.value })}
            placeholder="e.g. Fashion, Music Video, Commercial"
            required
          />
          <div className="flex flex-col gap-1">
            <label htmlFor="requirements" className="text-sm font-medium text-gray-700">
              Requirements
            </label>
            <textarea
              id="requirements"
              value={formData.requirements}
              onChange={(e) => setFormData({ ...formData, requirements: e.target.value })}
              placeholder="Tell us what you need for this shoot..."
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent min-h-[120px]"
              required
            />
          </div>

          {message.text && (
            <div className={`p-4 rounded-md ${message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
              {message.text}
            </div>
          )}

          <Button type="submit" disabled={loading} className="w-full">
            {loading ? 'Submitting...' : 'Submit Inquiry'}
          </Button>
        </form>
      </Card>
    </div>
  );
};

export default Inquiry;
