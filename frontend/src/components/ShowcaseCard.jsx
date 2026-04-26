import React from 'react';
import { useNavigate } from 'react-router-dom';

const ShowcaseCard = ({ image, label, title, meta, className = "", data = null, type = "location" }) => {
  const navigate = useNavigate();

  const handleClick = () => {
    if (data) {
      navigate('/inquiry', { 
        state: { 
          context: {
            type: type, // "location" or "production_reference"
            data: data
          }
        } 
      });
    }
  };

  return (
    <div 
      onClick={handleClick}
      className={`group relative overflow-hidden rounded-[32px] bg-gray-100 aspect-[4/5] cursor-pointer transition-all duration-500 hover:scale-[1.02] ${className}`}
    >
      {/* Background Image */}
      <img 
        src={image} 
        alt={title} 
        className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-110"
      />
      
      {/* Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-60 group-hover:opacity-80 transition-opacity" />

      {/* Content */}
      <div className="absolute bottom-0 left-0 right-0 p-8 flex flex-col justify-end transform transition-transform duration-500 group-hover:translate-y-[-8px]">
        <span className="text-[10px] font-black text-primary uppercase tracking-[0.3em] mb-2 drop-shadow-sm">
          {label}
        </span>
        <h3 className="text-2xl font-serif text-white leading-tight mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>
          {title}
        </h3>
        <p className="text-[11px] font-bold text-white/60 uppercase tracking-widest">
          {meta}
        </p>
      </div>
    </div>
  );
};

export default ShowcaseCard;
