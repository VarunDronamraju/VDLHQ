import React from 'react';

const Card = ({ children, className = "" }) => {
  return (
    <div className={`bg-white border border-gray-100 rounded-xl overflow-hidden ${className}`}>
      {children}
    </div>
  );
};

export default Card;
