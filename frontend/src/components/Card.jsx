import React from 'react';

const Card = ({ children, title, className = '' }) => {
  return (
    <div className={`bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden ${className}`}>
      {title && (
        <div className="px-6 py-4 border-bottom border-gray-100 bg-gray-50/50">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        </div>
      )}
      <div className="p-6">
        {children}
      </div>
    </div>
  );
};

export default Card;
