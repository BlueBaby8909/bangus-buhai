import { useLocation, Link } from 'react-router-dom';
import dashboardIcon from '../assets/Navigation/Dashboard_icon.svg';
import dashboardIconHighlighted from '../assets/Navigation/Dashboard_icon(highlighted).svg';
import tanksIcon from '../assets/Navigation/Tanks_icon.svg';
import tanksIconHighlighted from '../assets/Navigation/Tanks_icon(highlighted).svg';
import alertsIcon from '../assets/Navigation/Alerts_icon.svg';
import alertsIconHighlighted from '../assets/Navigation/Alerts_icon(highlighted).svg';

export default function BottomNav() {
  const location = useLocation();
  const path = location.pathname;

  return (
    <div className="fixed bottom-0 left-0 right-0 md:top-0 md:bottom-auto md:w-[240px] md:h-screen md:right-auto md:border-t-0 md:border-r bg-white/90 backdrop-blur-lg border-t border-slate-100 shadow-[0_-4px_24px_rgba(0,0,0,0.02)] flex md:flex-col justify-around md:justify-start items-center md:items-stretch h-[72px] px-2 md:px-[20px] md:pt-[32px] md:gap-[8px] z-50">
      
      {/* Desktop Brand Logo Placeholder */}
      <div className="hidden md:flex items-center gap-[12px] px-[16px] mb-[32px]">
        <div className="bg-sky-600 w-[32px] h-[32px] rounded-lg shadow-[0_2px_10px_rgba(2,132,199,0.3)] flex items-center justify-center text-white font-bold text-[18px]">B</div>
        <span className="font-bold text-slate-900 text-[18px] tracking-tight">Bangus BuhAI</span>
      </div>

      <Link to="/" className="flex flex-col md:flex-row items-center md:items-center min-w-[64px] md:min-w-0 md:w-full gap-1 md:gap-0 p-1 md:p-0 group">
        <div className={`flex flex-col md:flex-row items-center px-[16px] py-[8px] md:px-[16px] md:py-[12px] md:w-full rounded-[20px] md:rounded-[12px] transition-all duration-300 ${path === '/' ? 'bg-sky-50 shadow-sm' : 'hover:bg-slate-50'}`}>
          <img src={path === '/' ? dashboardIconHighlighted : dashboardIcon} alt="Dashboard" className={`w-[20px] h-[20px] transition-all ${path === '/' ? 'brightness-0' : 'opacity-60'}`} style={path === '/' ? { filter: 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)' } : {}} />
          <span className={`text-[11px] md:text-[14px] font-bold tracking-[0.3px] text-center md:text-left mt-[6px] md:mt-0 md:ml-[16px] transition-colors ${path === '/' ? 'text-sky-700' : 'text-slate-500 group-hover:text-slate-900'}`}>Dashboard</span>
        </div>
      </Link>
      
      <Link to="/tanks" className="flex flex-col md:flex-row items-center md:items-center min-w-[64px] md:min-w-0 md:w-full gap-1 md:gap-0 p-1 md:p-0 group">
        <div className={`flex flex-col md:flex-row items-center px-[16px] py-[8px] md:px-[16px] md:py-[12px] md:w-full rounded-[20px] md:rounded-[12px] transition-all duration-300 ${path.startsWith('/tanks') ? 'bg-sky-50 shadow-sm' : 'hover:bg-slate-50'}`}>
          <img src={path.startsWith('/tanks') ? tanksIconHighlighted : tanksIcon} alt="Tanks" className={`w-[22px] h-[17px] transition-all ${path.startsWith('/tanks') ? 'brightness-0' : 'opacity-60'}`} style={path.startsWith('/tanks') ? { filter: 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)' } : {}} />
          <span className={`text-[11px] md:text-[14px] font-bold tracking-[0.3px] text-center md:text-left mt-[6px] md:mt-0 md:ml-[14px] transition-colors ${path.startsWith('/tanks') ? 'text-sky-700' : 'text-slate-500 group-hover:text-slate-900'}`}>Tanks</span>
        </div>
      </Link>
      
      <Link to="/alerts" className="flex flex-col md:flex-row items-center md:items-center min-w-[64px] md:min-w-0 md:w-full gap-1 md:gap-0 p-1 md:p-0 group">
        <div className={`flex flex-col md:flex-row items-center px-[16px] py-[8px] md:px-[16px] md:py-[12px] md:w-full rounded-[20px] md:rounded-[12px] transition-all duration-300 ${path === '/alerts' ? 'bg-sky-50 shadow-sm' : 'hover:bg-slate-50'}`}>
          <img src={path === '/alerts' ? alertsIconHighlighted : alertsIcon} alt="Alerts" className={`w-[24px] h-[21px] transition-all ${path === '/alerts' ? 'brightness-0' : 'opacity-60'}`} style={path === '/alerts' ? { filter: 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)' } : {}} />
          <span className={`text-[11px] md:text-[14px] font-bold tracking-[0.3px] text-center md:text-left mt-[6px] md:mt-0 md:ml-[12px] transition-colors ${path === '/alerts' ? 'text-sky-700' : 'text-slate-500 group-hover:text-slate-900'}`}>Alerts</span>
        </div>
      </Link>
      
      <Link to="/data" className="flex flex-col md:flex-row items-center md:items-center min-w-[64px] md:min-w-0 md:w-full gap-1 md:gap-0 p-1 md:p-0 group">
        <div className={`flex flex-col md:flex-row items-center px-[16px] py-[8px] md:px-[16px] md:py-[12px] md:w-full rounded-[20px] md:rounded-[12px] transition-all duration-300 ${path === '/data' ? 'bg-sky-50 shadow-sm' : 'hover:bg-slate-50'}`}>
          <svg className={`w-[20px] h-[20px] md:w-[22px] md:h-[22px] transition-all ${path === '/data' ? 'text-sky-500' : 'text-slate-400 group-hover:text-slate-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          <span className={`text-[11px] md:text-[14px] font-bold tracking-[0.3px] text-center md:text-left mt-[6px] md:mt-0 md:ml-[14px] transition-colors ${path === '/data' ? 'text-sky-700' : 'text-slate-500 group-hover:text-slate-900'}`}>Data</span>
        </div>
      </Link>
    </div>
  );
}
