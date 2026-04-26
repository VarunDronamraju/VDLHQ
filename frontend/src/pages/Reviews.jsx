import React from 'react';
import Card from '../components/Card';

const Reviews = () => {
  const testimonials = [
    { name: 'Sarah J.', company: 'Apex Productions', text: 'LocationHQ made finding our feature film studio seamless. The pipeline tracking was incredibly helpful.' },
    { name: 'Mark T.', company: 'Creative Agency', text: 'The best location agency in London. Clean, professional, and very fast transitions.' },
    { name: 'Elena R.', company: 'Global Brands', text: 'The permit management service saved us weeks of work. Highly recommended for commercial shoots.' },
  ];

  return (
    <div className="max-w-3xl mx-auto space-y-12">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Reviews</h1>
        <p className="text-gray-500">What our production partners say about working with us.</p>
      </div>

      <div className="space-y-6">
        {testimonials.map((review, i) => (
          <Card key={i} className="p-8 space-y-4">
            <p className="text-gray-700 italic leading-relaxed font-medium">"{review.text}"</p>
            <div>
              <p className="font-bold text-gray-900 text-sm">{review.name}</p>
              <p className="text-xs text-gray-500">{review.company}</p>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default Reviews;
