import { Link } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import powerButtonIcon from "../assets/DashBoard/PowerButton.svg";
import imgImageAquasenseProDevice from "../assets/DashBoard/Device (Front).png";
import imgIcon2 from "../assets/DashBoard/Star.svg";
import imgIcon4 from "../assets/DashBoard/Temp(Orange).svg";
import imgIcon5 from "../assets/DashBoard/Ph(Blue).svg";
import imgIcon6 from "../assets/DashBoard/Turb(Gray).svg";

export default function Dashboard() {
  const firstTank = { id: 1, name: "Tank A1" };
  const firstDevice = { name: "Aquasense Pro", is_online: true };
  const latestLog = { temp: 28.5, ph: 7.2, turbidity: 5 };

  return (
    <div className="bg-[#f4f6f8] flex flex-col min-h-screen">
      <AppHeader 
        title="Hatchery Monitor" 
        leftNode={
          <div className="bg-white rounded-full p-[8px] shadow-sm border border-gray-100">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 12H21M3 6H21M3 18H21" stroke="#5c666e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        } 
      />
      <div className="flex-1 w-full pb-[32px] pt-[24px] px-[16px] flex flex-col gap-[24px]">
        <div className="flex flex-col">
          <h2 className="font-bold text-[#101828] text-[24px] leading-[30px]">Hello, Manager</h2>
          <p className="text-[#6b7280] text-[14px] leading-[20px] mt-1">Bangus Buhai water quality at a glance.</p>
        </div>

        <div className="bg-white rounded-[24px] p-[20px] flex items-center gap-[16px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white/20">
          <div className="bg-blue-50 rounded-[16px] w-[48px] h-[48px] flex items-center justify-center shrink-0">
            <img src={imgIcon2} alt="AI" className="w-[24px] h-[24px]" />
          </div>
          <div className="flex flex-col flex-1">
            <h3 className="font-bold text-[#101828] text-[15px] leading-[20px]">AI Forecasting Active</h3>
            <p className="text-[#6b7280] text-[13px] leading-[18px] mt-[2px]">Predicting Temp · pH · Turbidity</p>
          </div>
          <div className="bg-blue-50 rounded-full px-[12px] py-[6px]">
            <span className="font-bold text-[#003fb1] text-[11px]">LSTM</span>
          </div>
        </div>

        <div className="flex flex-col gap-[12px]">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-[#101828] text-[18px] leading-[28px]">{firstTank.name}</h3>
            <Link to="/tanks" className="bg-[#00bc7d] rounded-full px-[16px] py-[6px] text-white text-[13px] font-medium leading-[13px] shadow-[0_4px_12px_rgba(0,188,125,0.3)]">
              See All
            </Link>
          </div>

          <Link to={`/tanks/${firstTank.id}`} className="bg-white rounded-[32px] overflow-hidden shadow-[0_8px_30px_rgb(0,0,0,0.04)] flex flex-col h-[280px] block relative">
            <div className="absolute top-0 right-0 w-full h-full opacity-[0.03] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-[#003fb1] via-transparent to-transparent pointer-events-none"></div>
            <div className="p-[24px] flex-1 flex flex-col relative z-10">
              <div className="flex justify-between items-start">
                <div className="flex flex-col">
                  <h4 className="font-bold text-[#101828] text-[20px]">{firstTank.name}</h4>
                  <p className="font-medium text-[#6b7280] text-[14px] mt-[2px]">{firstDevice.name}</p>
                  <p className={`font-medium text-[14px] mt-[4px] flex items-center gap-[6px] ${firstDevice.is_online ? "text-[#009966]" : "text-[#99a1af]"}`}>
                    <span className={`w-[8px] h-[8px] rounded-full ${firstDevice.is_online ? 'bg-[#00bc7d]' : 'bg-[#99a1af]'}`}></span>
                    {firstDevice.is_online ? "Connected" : "Disconnected"}
                  </p>
                </div>
                <div className="bg-[#00bcff] rounded-full w-[48px] h-[48px] flex items-center justify-center shadow-[0_8px_16px_rgba(14,165,233,0.3)]">
                  <img src={powerButtonIcon} alt="Power" className="w-[23px] h-[23px]" />
                </div>
              </div>

              <div className="mt-auto flex justify-between items-end">
                <div className="flex flex-col mb-4">
                  <p className="font-bold text-[#99a1af] text-[12px] tracking-[0.8px] uppercase">Sensors Active</p>
                  <p className="font-bold text-[#00bc7d] text-[48px] leading-[48px] tracking-[-1.2px] mt-1">3 <span className="text-[24px] text-[#99a1af]">/ 3</span></p>
                </div>
                <img src={imgImageAquasenseProDevice} alt="Device" className="w-[140px] h-[120px] object-contain drop-shadow-xl" />
              </div>
            </div>
            <div className="px-[24px] pb-[24px] pt-[8px] relative z-10">
              <div className="bg-[#f3f4f6] h-[8px] rounded-full w-full overflow-hidden">
                <div className="bg-[#00bc7d] h-full w-full rounded-full"></div>
              </div>
            </div>
          </Link>
        </div>

        <div className="flex flex-col gap-[12px]">
          <h3 className="font-bold text-[#101828] text-[18px] leading-[28px]">Live Readings</h3>
          <div className="grid grid-cols-2 grid-rows-2 gap-[16px]">
            {/* Temperature Card */}
            <div className="bg-gradient-to-br from-[#11998e] to-[#38ef7d] rounded-[24px] p-[20px] shadow-[0_8px_24px_rgba(56,239,125,0.3)] flex flex-col justify-between overflow-hidden relative min-h-[140px]">
              <div className="flex justify-between items-start z-10">
                <img src={imgIcon4} alt="Temp" className="w-[18px] h-[18px] brightness-0 invert" />
                <span className="bg-white/20 text-white text-[11px] font-bold px-[10px] py-[4px] rounded-full backdrop-blur-md shadow-sm">Avg</span>
              </div>
              <div className="flex flex-col z-10 mt-auto">
                <div className="flex items-end gap-[2px]">
                  <span className="font-bold text-white text-[40px] leading-[40px] tracking-[-1px]">{latestLog.temp}</span>
                  <span className="font-semibold text-white text-[20px] leading-[28px] pb-[4px]">°C</span>
                </div>
                <span className="font-semibold text-white/90 text-[13px] mt-1">Temperature</span>
              </div>
            </div>

            {/* pH Card */}
            <div className="bg-gradient-to-br from-[#00c6ff] to-[#0072ff] rounded-[24px] p-[20px] shadow-[0_8px_24px_rgba(0,114,255,0.3)] flex flex-col justify-between overflow-hidden relative min-h-[140px]">
              <div className="flex justify-between items-start z-10">
                <img src={imgIcon5} alt="pH" className="w-[16px] h-[20px] brightness-0 invert" />
                <span className="bg-white/20 text-white text-[11px] font-bold px-[10px] py-[4px] rounded-full backdrop-blur-md shadow-sm">Optimal</span>
              </div>
              <div className="flex flex-col z-10 mt-auto">
                <span className="font-bold text-white text-[40px] leading-[40px] tracking-[-1px]">{latestLog.ph}</span>
                <span className="font-semibold text-white/90 text-[13px] mt-1">pH Level</span>
              </div>
            </div>

            {/* Turbidity Card */}
            <div className="col-span-2 bg-white rounded-[24px] p-[24px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] flex justify-between items-end min-h-[140px]">
              <div className="flex flex-col justify-between h-full">
                <img src={imgIcon6} alt="Turbidity" className="w-[20px] h-[17px] mb-[12px]" />
                <div className="flex flex-col mt-auto">
                  <div className="flex items-end gap-[4px]">
                    <span className="font-bold text-[#101828] text-[40px] leading-[40px] tracking-[-1px]">{latestLog.turbidity}</span>
                    <span className="font-semibold text-[#6b7280] text-[20px] leading-[28px] pb-[4px]">NTU</span>
                  </div>
                  <span className="font-semibold text-[#6b7280] text-[13px] mt-1">Turbidity</span>
                </div>
              </div>
              <div className="flex items-end gap-[6px] h-[40px] opacity-70 pb-[2px]">
                <div className="w-[14px] h-[12px] bg-[#e5e7eb] rounded-[4px]"></div>
                <div className="w-[14px] h-[20px] bg-[#e5e7eb] rounded-[4px]"></div>
                <div className="w-[14px] h-[28px] bg-[#e5e7eb] rounded-[4px]"></div>
                <div className="w-[14px] h-[40px] bg-[#003fb1] rounded-[4px] shadow-sm"></div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
