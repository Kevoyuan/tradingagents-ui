import React from 'react';

interface IconRailProps {
  currentPath?: string;
  onNavigate?: (path: string) => void;
}

export const IconRail: React.FC<IconRailProps> = ({ currentPath = '/', onNavigate }) => {
  const isSettings = currentPath === '/settings' || currentPath.startsWith('/settings');
  const isReports = !isSettings && currentPath.startsWith('/reports');
  const isMonitor = !isReports && !isSettings;

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
        href="/"
        aria-current={isMonitor ? 'page' : undefined}
        title="Monitor"
        onClick={(e) => {
          if (onNavigate) {
            e.preventDefault();
            onNavigate('/');
          }
        }}
        className={`w-9 h-9 grid place-items-center transition-colors ${
          isMonitor ? 'text-white' : 'text-[#7c786f] hover:text-white'
        }`}
        data-testid="nav-monitor"
      >
        <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
          <rect x="2.5" y="3.5" width="15" height="10.5" />
          <path d="M7 17h6M10 14v3" />
        </svg>
      </a>

      {/* Reports Icon */}
      <a
        href="/reports"
        aria-current={isReports ? 'page' : undefined}
        title="Reports"
        onClick={(e) => {
          if (onNavigate) {
            e.preventDefault();
            onNavigate('/reports');
          }
        }}
        className={`w-9 h-9 grid place-items-center transition-colors ${
          isReports ? 'text-white' : 'text-[#7c786f] hover:text-white'
        }`}
        data-testid="nav-reports"
      >
        <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
          <path d="M5 2.6h6.4L15.5 6.7v10.7H5z" />
          <path d="M7.4 10.4h5.6M7.4 13.2h4" />
        </svg>
      </a>

      {/* Settings Icon */}
      <a
        href="/settings"
        aria-current={isSettings ? 'page' : undefined}
        title="Settings"
        onClick={(e) => {
          if (onNavigate) {
            e.preventDefault();
            onNavigate('/settings');
          }
        }}
        className={`w-9 h-9 grid place-items-center transition-colors ${
          isSettings ? 'text-white' : 'text-[#9a958a] hover:text-white'
        }`}
        data-testid="nav-settings"
      >
        {/* Sliders, not a gear: a 20-tab gear outline turns to mud at 16px and
            the previous four-spoke glyph was invisible at this size. Three
            ruled tracks with a knob each stays crisp and still reads as
            "settings". */}
        <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
          <path d="M3 6h4M11 6h6M3 10h7M14 10h3M3 14h2M9 14h8" />
          <circle cx="9" cy="6" r="1.7" />
          <circle cx="12.5" cy="10" r="1.7" />
          <circle cx="7" cy="14" r="1.7" />
        </svg>
      </a>
    </nav>
  );
};
