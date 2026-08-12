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
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t-[1.276px] border-[#e5e7eb] border-solid drop-shadow-[0px_-4px_6px_rgba(0,0,0,0.06)] flex justify-around items-center h-[69.94px] px-2 z-50">
      <Link to="/" className="flex flex-col items-center min-w-[64px] gap-1 p-1">
        <div className={`flex flex-col items-center px-[12px] py-[6px] rounded-[12px] ${path === '/' ? 'bg-[rgba(219,234,254,0.8)]' : ''}`}>
          <img src={path === '/' ? dashboardIconHighlighted : dashboardIcon} alt="Dashboard" className="w-[18px] h-[18px]" />
          <span className={`text-[11px] font-semibold leading-[11px] tracking-[0.275px] text-center mt-1 ${path === '/' ? 'text-[#003fb1]' : 'text-[#5c666e]'}`}>Dashboard</span>
        </div>
      </Link>
      <Link to="/tanks" className="flex flex-col items-center min-w-[64px] gap-1 p-1">
        <div className={`flex flex-col items-center px-[12px] py-[6px] rounded-[12px] ${path.startsWith('/tanks') ? 'bg-[rgba(219,234,254,0.8)]' : ''}`}>
          <img src={path.startsWith('/tanks') ? tanksIconHighlighted : tanksIcon} alt="Tanks" className="w-[20px] h-[15px]" />
          <span className={`text-[11px] font-semibold leading-[11px] tracking-[0.275px] text-center mt-1 ${path.startsWith('/tanks') ? 'text-[#003fb1]' : 'text-[#5c666e]'}`}>Tanks</span>
        </div>
      </Link>
      <Link to="/alerts" className="flex flex-col items-center min-w-[64px] gap-1 p-1">
        <div className={`flex flex-col items-center px-[12px] py-[6px] rounded-[12px] ${path === '/alerts' ? 'bg-[rgba(219,234,254,0.8)]' : ''}`}>
          <img src={path === '/alerts' ? alertsIconHighlighted : alertsIcon} alt="Alerts" className="w-[22px] h-[19px]" />
          <span className={`text-[11px] font-semibold leading-[11px] tracking-[0.275px] text-center mt-1 ${path === '/alerts' ? 'text-[#003fb1]' : 'text-[#5c666e]'}`}>Alerts</span>
        </div>
      </Link>
    </div>
  );
}
