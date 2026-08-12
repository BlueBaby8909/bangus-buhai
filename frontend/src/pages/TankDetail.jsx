import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import imgImage from "../assets/DeviceDetail/Device (Front).png";
import imgIconPh from "../assets/DeviceDetail/Ph(White).svg";
import imgIconTemp from "../assets/DeviceDetail/Temp(White).svg";
import imgIconTurb from "../assets/DashBoard/Turb(Gray).svg";
import imgIconBluePh from "../assets/DeviceDetail/Ph(LightBlue).svg";
import imgIconBlueTemp from "../assets/DeviceDetail/Temp(Blue).svg";

export default function TankDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [relayIsOn, setRelayIsOn] = useState(true);

  const tank = { id, name: `Tank ${id === "1" ? "A1" : id === "2" ? "Nursery B" : "C3"}`, growth_stage: "Grow-out" };
  const latest = { temperature: 28.5, pH: 7.2, turbidity: 5, relay_on: relayIsOn };
  const deviceState = { isOnline: true };
  
  const prediction = {
    temperature_1h: 28.6, pH_1h: 7.2,
    temperature_2h: 28.7, pH_2h: 7.1,
    temperature_3h: 28.8, pH_3h: 7.1,
    temperature_4h: 28.9, pH_4h: 7.0
  };

  const handleToggleRelay = () => {
    setRelayIsOn(!relayIsOn);
  };

  const getPredictionStatus = (temp, ph) => {
    if (!temp || !ph) return { label: "Unknown", color: "bg-[#e5e7eb]", text: "text-[#5c666e]" };
    const isTempIdeal = temp >= 26 && temp <= 32;
    const isPhIdeal = ph >= 7.5 && ph <= 8.5;
    if (isTempIdeal && isPhIdeal) return { label: "Optimal", color: "bg-[#d0fae5]", text: "text-[#009966]" };
    return { label: "Caution", color: "bg-[#fef3c6]", text: "text-[#bb4d00]" };
  };

  return (
    <div className="bg-[#f4f6f8] flex flex-col min-h-screen relative pb-[100px]">
      <AppHeader 
        title={tank.name} 
        leftNode={
          <div 
            onClick={() => navigate("/tanks")}
            className="w-[40px] h-[40px] rounded-full bg-white shadow-sm border border-gray-100 flex items-center justify-center cursor-pointer hover:bg-gray-50 transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#5c666e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </div>
        } 
      />
      
      <div className="flex-1 w-full px-[16px] py-[20px] flex flex-col gap-[24px]">
        <div className="bg-white rounded-[24px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-[20px] flex items-center gap-[16px]">
          <div className="bg-gray-50 rounded-[16px] w-[56px] h-[56px] flex items-center justify-center shadow-inner">
            <img src={imgImage} alt="Aquasense Pro" className="w-[48px] h-[48px] object-contain" />
          </div>
          <div className="flex flex-col flex-1">
            <p className="font-bold text-[#101828] text-[16px] leading-[22px]">Aquasense Pro #1</p>
            <p className="font-medium text-[#6b7280] text-[13px] leading-[18px] mt-[2px]">Monitoring pH · Temp · Turbidity</p>
          </div>
          <div className={`w-[12px] h-[12px] rounded-full shadow-sm ${deviceState.isOnline ? "bg-[#00bc7d]" : "bg-[#99a1af]"}`}></div>
        </div>

        <div className="flex gap-[16px] w-full">
          <div className="bg-gradient-to-br from-[#00c6ff] to-[#0072ff] flex-1 rounded-[24px] p-[20px] shadow-[0_8px_24px_rgba(0,114,255,0.3)] flex flex-col justify-between h-[180px] relative overflow-hidden">
            <div className="absolute top-0 right-0 w-full h-full opacity-20 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-white via-transparent to-transparent pointer-events-none"></div>
            <div className="flex items-center gap-[8px] z-10">
              <img src={imgIconPh} alt="pH" className="w-[16px] h-[20px] drop-shadow-sm" />
              <span className="font-bold text-[15px] text-white">pH</span>
            </div>
            <div className="flex flex-col z-10">
              <span className="font-bold text-white text-[32px] leading-[32px] tracking-[-1px]">{latest.pH}</span>
              <span className="font-semibold text-[12px] text-white/80 mt-[8px]">Normal 6.5 – 7.5</span>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-[#11998e] to-[#38ef7d] flex-1 rounded-[24px] p-[20px] shadow-[0_8px_24px_rgba(56,239,125,0.3)] flex flex-col justify-between h-[180px] relative overflow-hidden">
            <div className="absolute top-0 right-0 w-full h-full opacity-20 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-white via-transparent to-transparent pointer-events-none"></div>
            <div className="flex items-center gap-[8px] z-10">
              <img src={imgIconTemp} alt="Temp" className="w-[12px] h-[20px] drop-shadow-sm" />
              <span className="font-bold text-[15px] text-white">Water Temp</span>
            </div>
            <div className="flex flex-col z-10">
              <span className="font-bold text-white text-[32px] leading-[32px] tracking-[-1px]">{latest.temperature}°C</span>
              <span className="font-semibold text-[12px] text-white/80 mt-[8px]">Optimal range 25°C – 30°C</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-[24px] p-[24px] flex items-center justify-between w-full shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="flex flex-col gap-[16px]">
            <div className="flex items-center gap-[10px]">
              <div className="bg-blue-50 w-[32px] h-[32px] rounded-[10px] flex items-center justify-center">
                <img src={imgIconTurb} alt="Turbidity" className="w-[16px] h-[13px] brightness-0" style={{ filter: 'invert(15%) sepia(87%) saturate(3015%) hue-rotate(211deg) brightness(97%) contrast(108%)' }} />
              </div>
              <span className="font-bold text-[16px] text-[#101828]">Turbidity</span>
            </div>
            <div className="flex flex-col">
              <div className="flex items-end gap-[6px]">
                <span className="font-bold text-[#101828] text-[36px] leading-[36px] tracking-[-1px]">{latest.turbidity}</span>
                <span className="font-semibold text-[#6b7280] text-[16px] pb-[4px]">NTU</span>
              </div>
              <span className="font-semibold text-[13px] text-[#6b7280] mt-[8px]">{"Normal < 20 NTU"}</span>
            </div>
          </div>
          <div className="flex items-end gap-[6px] h-[48px] opacity-70">
            <div className="bg-[#e5e7eb] w-[14px] h-[20px] rounded-[4px]"></div>
            <div className="bg-[#e5e7eb] w-[14px] h-[36px] rounded-[4px]"></div>
            <div className="bg-[#003fb1] w-[14px] h-[48px] rounded-[4px] shadow-sm"></div>
            <div className="bg-[#e5e7eb] w-[14px] h-[18px] rounded-[4px]"></div>
          </div>
        </div>

        <div className="bg-white rounded-[24px] p-[24px] flex flex-col shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <p className="font-bold text-[#99a1af] text-[12px] tracking-[0.8px] uppercase">Relay Control</p>
          <div className="flex items-center justify-between mt-[16px]">
            <div className="flex flex-col">
              <p className="font-bold text-[#101828] text-[18px] leading-[22px]">{tank.name} — Heater</p>
              <p className="font-medium text-[#6b7280] text-[14px] mt-[4px]">Send command via MQTT</p>
            </div>
            <div 
              onClick={handleToggleRelay}
              className={`w-[56px] h-[32px] rounded-full relative cursor-pointer transition-colors duration-300 ${relayIsOn ? 'bg-[#00bc7d]' : 'bg-[#e5e7eb]'}`}
            >
              <div 
                className={`absolute w-[26px] h-[26px] bg-white rounded-full top-[3px] transition-all shadow-md ${relayIsOn ? 'left-[27px]' : 'left-[3px]'}`}
              ></div>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-[16px] mt-[8px]">
          <h3 className="font-bold text-[#101828] text-[20px]">4-Hour AI Forecast</h3>
          <div className="grid grid-cols-2 gap-[16px]">
            {[1, 2, 3, 4].map(hr => {
              const temp = prediction[`temperature_${hr}h`];
              const ph = prediction[`pH_${hr}h`];
              const status = getPredictionStatus(temp, ph);
              
              return (
                <div key={hr} className="bg-white rounded-[24px] p-[20px] flex flex-col items-center gap-[16px] shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
                  <div className="bg-blue-50 text-[#003fb1] font-bold text-[11px] tracking-[1px] uppercase px-[12px] py-[6px] rounded-full w-max">
                    +{hr} HR
                  </div>
                  <div className="flex flex-col gap-[12px] items-center w-full">
                    <div className="flex items-center gap-[6px]">
                      <img src={imgIconBlueTemp} alt="Temp" className="w-[8px] h-[16px]" />
                      <span className="font-bold text-[#003fb1] text-[22px] tracking-[-0.5px]">{temp.toFixed(1)}°C</span>
                    </div>
                    <div className="flex items-center gap-[6px]">
                      <img src={imgIconBluePh} alt="pH" className="w-[12px] h-[16px]" />
                      <span className="font-bold text-[#00b4d8] text-[22px] tracking-[-0.5px]">{ph.toFixed(1)}</span>
                    </div>
                  </div>
                  <div className={`px-[16px] py-[8px] rounded-full w-full flex justify-center mt-1 ${status.color}`}>
                    <span className={`font-bold text-[13px] ${status.text}`}>{status.label}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
