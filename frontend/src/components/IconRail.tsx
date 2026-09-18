import React from 'react';

export const IconRail: React.FC = () => {
  return (
    <nav
      className="sticky top-0 h-screen w-14 bg-ink flex flex-col items-center py-4 gap-1 z-40 select-none"
      aria-label="Sidebar Navigation"
    >
      {/* Brand mark */}
      <span className="w-6 h-6 flex flex-col justify-center gap-[2.5px] mb-4.5" aria-hidden="true">
        <i className="block h-[2.5px] bg-white w-full"></i>
        <i className="block h-[2.5px] bg-white w-[56%]"></i>
        <i className="block h-[2.5px] bg-white w-[80%]"></i>
      </span>

      {/* Monitor Icon */}
      <a
        href="#"
        aria-current="page"
        title="Monitor"
        className="w-9 h-9 grid place-items-center text-white hover:text-white"
      >
        <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
          <rect x="2.5" y="3.5" width="15" height="10.5" />
          <path d="M7 17h6M10 14v3" />
        </svg>
      </a>

      {/* Reports Icon */}
      <a
        href="#"
        title="Reports"
        className="w-9 h-9 grid place-items-center text-[#7c786f] hover:text-white transition-colors"
      >
        <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
          <path d="M5 2.6h6.4L15.5 6.7v10.7H5z" />
          <path d="M7.4 10.4h5.6M7.4 13.2h4" />
        </svg>
      </a>

      {/* Settings Icon */}
      <a
        href="#"
        title="Settings"
        className="w-9 h-9 grid place-items-center text-[#7c786f] hover:text-white transition-colors"
      >
        <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
          <circle cx="10" cy="10" r="2.6" />
          <path d="M10 2.6v2.2M10 15.2v2.2M17.4 10h-2.2M4.8 10H2.6" />
        </svg>
      </a>
    </nav>
  );
};
