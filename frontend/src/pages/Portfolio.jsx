import React from 'react';
import Card from '../components/Card';

const Portfolio = () => {
  return (
    <div className="space-y-12">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Portfolio</h1>
        <p className="text-gray-500 max-w-2xl mx-auto">
          A showcase of premium locations and recent productions across London.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="group cursor-pointer">
            <div className="aspect-[4/3] bg-gray-100 rounded-2xl overflow-hidden mb-4 border border-gray-100">
              <div className="w-full h-full flex items-center justify-center text-gray-300 font-bold text-xs uppercase tracking-widest">
                Space Showcase {i}
              </div>
            </div>
            <h3 className="font-bold text-gray-900 text-sm">Industrial Studio {i}</h3>
            <p className="text-xs text-gray-500">Shoreditch, London</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Portfolio;
