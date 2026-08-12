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
    <div className="bg-white flex flex-col min-h-screen relative pb-[100px]">
      <AppHeader 
        title={tank.name} 
        leftNode={
          <div 
            onClick={() => navigate("/tanks")}
            className="w-[34px] h-[34px] rounded-full flex items-center justify-center cursor-pointer ml-[-8px] hover:bg-gray-100"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#5c666e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </div>
        } 
      />
      
      <div 
        className="flex-1 w-full px-[16px] py-[16px] flex flex-col gap-[20px]"
        style={{ backgroundImage: "linear-gradient(134.5deg, rgb(248, 249, 250) 8.48%, rgb(243, 244, 245) 91.51%)" }}
      >
        <div className="bg-white border-[1.2px] border-[#e5e7eb] rounded-[16px] drop-shadow-[0px_2px_4px_rgba(0,0,0,0.06)] p-[16px] flex items-center gap-[12px]">
          <img src={imgImage} alt="Aquasense Pro" className="w-[40px] h-[40px] object-contain" />
          <div className="flex flex-col flex-1">
            <p className="font-semibold text-[#101828] text-[14px] leading-[21px]">Aquasense Pro #1</p>
            <p className="font-normal text-[#99a1af] text-[12px] leading-[18px]">Monitoring pH · Temp · Turbidity</p>
          </div>
          <div className={`w-[10px] h-[10px] rounded-full ${deviceState.isOnline ? "bg-[#00bc7d]" : "bg-[#99a1af]"}`}></div>
        </div>

        <div className="flex gap-[12px] w-full">
          <div className="bg-[#00b4d8] flex-1 rounded-[24px] p-[20px] flex flex-col justify-between h-[176px] drop-shadow-[0px_4px_3.75px_rgba(26,86,219,0.04)]">
            <div className="flex items-center gap-[8px]">
              <img src={imgIconPh} alt="pH" className="w-[16px] h-[20px]" />
              <span className="font-medium text-[15px] text-[rgba(255,255,255,0.9)]">pH</span>
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-white text-[24px] leading-[24px]">{latest.pH}</span>
              <span className="font-semibold text-[11px] text-[rgba(255,255,255,0.8)] tracking-[0.275px] mt-[8px]">Normal 6.5 – 7.5</span>
            </div>
          </div>
          
          <div className="bg-[#059669] flex-1 rounded-[24px] p-[20px] flex flex-col justify-between h-[176px] drop-shadow-[0px_4px_3.75px_rgba(26,86,219,0.04)]">
            <div className="flex items-center gap-[8px]">
              <img src={imgIconTemp} alt="Temp" className="w-[10px] h-[20px]" />
              <span className="font-medium text-[15px] text-[rgba(255,255,255,0.9)]">Water Temp</span>
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-white text-[24px] leading-[24px]">{latest.temperature}°C</span>
              <span className="font-semibold text-[11px] text-[rgba(255,255,255,0.8)] tracking-[0.275px] mt-[8px]">Optimal range 25°C – 30°C</span>
            </div>
          </div>
        </div>

        <div className="bg-[#003fb1] rounded-[24px] p-[20px] flex items-center justify-between w-full drop-shadow-[0px_4px_3.75px_rgba(26,86,219,0.08)]">
          <div className="flex flex-col gap-[12px]">
            <div className="flex items-center gap-[8px]">
              <img src={imgIconTurb} alt="Turbidity" className="w-[20px] h-[17px] brightness-0 invert" />
              <span className="font-medium text-[15px] text-[rgba(255,255,255,0.9)]">Turbidity</span>
            </div>
            <div className="flex flex-col">
              <div className="flex items-end gap-[6px]">
                <span className="font-bold text-white text-[24px] leading-[24px]">{latest.turbidity}</span>
                <span className="font-semibold text-[13px] text-[rgba(255,255,255,0.7)] pb-[2px]">NTU</span>
              </div>
              <span className="font-semibold text-[11px] text-[rgba(255,255,255,0.7)] tracking-[0.275px] mt-[8px]">{"Normal < 20 NTU"}</span>
            </div>
          </div>
          <div className="flex items-end gap-[6px] h-[40px] opacity-60">
            <div className="bg-[rgba(255,255,255,0.7)] w-[12px] h-[18px] rounded-t-[4px]"></div>
            <div className="bg-[rgba(255,255,255,0.7)] w-[12px] h-[30px] rounded-t-[4px]"></div>
            <div className="bg-[rgba(255,255,255,0.7)] w-[12px] h-[48px] rounded-t-[4px]"></div>
            <div className="bg-[rgba(255,255,255,0.7)] w-[12px] h-[15px] rounded-t-[4px]"></div>
          </div>
        </div>

        <div className="bg-white border-[1.2px] border-[#f3f4f6] rounded-[24px] p-[20px] flex flex-col drop-shadow-[0px_4px_3.75px_rgba(26,86,219,0.04)]">
          <p className="font-semibold text-[#99a1af] text-[13px] tracking-[0.65px] uppercase">Relay Control</p>
          <div className="flex items-center justify-between mt-[16px]">
            <div className="flex flex-col">
              <p className="font-semibold text-[#1e2939] text-[15px] leading-[22px]">{tank.name} — Heater</p>
              <p className="font-normal text-[#99a1af] text-[12px] mt-[2px]">Send command via MQTT</p>
            </div>
            <div 
              onClick={handleToggleRelay}
              className={`w-[48px] h-[24px] rounded-full relative cursor-pointer ${relayIsOn ? 'bg-[#00bc7d]' : 'bg-[#e5e7eb]'}`}
            >
              <div 
                className={`absolute w-[20px] h-[20px] bg-white rounded-full top-[2px] transition-all shadow-[0px_1px_3px_rgba(0,0,0,0.1)] ${relayIsOn ? 'left-[26px]' : 'left-[2px]'}`}
              ></div>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-[16px]">
          <h3 className="font-semibold text-[#191c1d] text-[20px]">4-Hour AI Forecast</h3>
          <div className="grid grid-cols-2 gap-[16px]">
            {[1, 2, 3, 4].map(hr => {
              const temp = prediction[`temperature_${hr}h`];
              const ph = prediction[`pH_${hr}h`];
              const status = getPredictionStatus(temp, ph);
              
              return (
                <div key={hr} className="bg-white border-[1.2px] border-[rgba(243,244,246,0.5)] rounded-[24px] p-[20px] flex flex-col items-center gap-[12px] drop-shadow-[0px_4px_3.75px_rgba(26,86,219,0.04)]">
                  <p className="font-semibold text-[#99a1af] text-[12px] tracking-[1.2px] uppercase">+{hr} HR</p>
                  <div className="flex flex-col gap-[8px] items-center w-full">
                    <div className="flex items-center gap-[4px]">
                      <img src={imgIconBlueTemp} alt="Temp" className="w-[7px] h-[14px]" />
                      <span className="font-semibold text-[#003fb1] text-[20px]">{temp.toFixed(1)}°C</span>
                    </div>
                    <div className="flex items-center gap-[4px]">
                      <img src={imgIconBluePh} alt="pH" className="w-[11px] h-[14px]" />
                      <span className="font-semibold text-[#00b4d8] text-[20px]">{ph.toFixed(1)}</span>
                    </div>
                  </div>
                  <div className={`px-[16px] py-[6px] rounded-full ${status.color}`}>
                    <span className={`font-medium text-[13px] ${status.text}`}>{status.label}</span>
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
