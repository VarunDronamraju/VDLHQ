import React from 'react';
import { ALL_LOCATIONS } from '../api/data';
import ShowcaseCard from '../components/ShowcaseCard';

const Portfolio = () => {
  return (
    <div className="space-y-24 py-12">
      <div className="text-center space-y-6 max-w-3xl mx-auto px-6">
        <div className="inline-flex items-center gap-3 px-4 py-1 bg-primary/5 border border-primary/10 rounded-full">
          <span className="text-[9px] font-black text-primary uppercase tracking-[0.3em]">Strategic Archive</span>
        </div>
        <h1 className="text-5xl md:text-7xl font-serif text-gray-900 leading-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
          The Portfolio
        </h1>
        <p className="text-gray-500 text-sm md:text-base leading-relaxed">
          Explore our curated selection of high-end locations and recent global productions. 
          Each space is vetted for production excellence.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-16 px-8">
        {ALL_LOCATIONS.map((loc) => (
          <ShowcaseCard 
            key={loc.id}
            image={loc.image}
            label={loc.category}
            title={loc.name}
            meta={`${loc.area} • £${loc.price_per_day}/DAY`}
            data={loc}
            type="location"
          />
        ))}
      </div>
    </div>
  );
};

export default Portfolio;
