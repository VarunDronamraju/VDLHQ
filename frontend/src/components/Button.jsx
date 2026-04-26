import React from 'react';

const Button = ({ children, onClick, type = 'button', variant = 'primary', className = '', ...props }) => {
  const baseStyles = 'px-4 py-2 rounded-md font-medium transition-colors duration-200 disabled:opacity-50';
  const variants = {
    primary: 'bg-primary text-white hover:bg-primary-hover',
    secondary: 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50',
    teal: 'bg-teal-accent text-white hover:opacity-90',
  };

  return (
    <button
      type={type}
      onClick={onClick}
      className={`${baseStyles} ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;
