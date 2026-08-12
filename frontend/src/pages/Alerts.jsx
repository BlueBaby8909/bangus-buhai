import { Link } from "react-router-dom";
import AppHeader from "../components/AppHeader";

export default function Alerts() {
  return (
    <div className="bg-[#f4f6f8] flex flex-col min-h-screen">
      <AppHeader 
        title="Alerts" 
        leftNode={
          <div className="w-[40px] h-[40px] bg-white rounded-full flex items-center justify-center shadow-sm border border-gray-100">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 12H21M3 6H21M3 18H21" stroke="#5c666e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        }
      />
      
      <div className="flex-1 w-full pb-[32px] pt-[24px] px-[16px] flex flex-col gap-[24px]">
        <div className="grid grid-cols-3 gap-[12px]">
          <div className="bg-white rounded-[20px] p-[16px] shadow-[0_4px_12px_rgba(0,0,0,0.05)] flex flex-col gap-[6px] items-center text-center">
            <div className="flex items-center gap-[6px]">
              <div className="bg-[#ff2056] w-[8px] h-[8px] rounded-full"></div>
              <span className="font-bold text-[#6b7280] text-[10px] tracking-[0.5px] uppercase">Critical</span>
            </div>
            <p className="font-bold text-[#ec003f] text-[28px] leading-[32px]">2</p>
          </div>
          
          <div className="bg-white rounded-[20px] p-[16px] shadow-[0_4px_12px_rgba(0,0,0,0.05)] flex flex-col gap-[6px] items-center text-center">
            <div className="flex items-center gap-[6px]">
              <div className="bg-[#ffb900] w-[8px] h-[8px] rounded-full"></div>
              <span className="font-bold text-[#6b7280] text-[10px] tracking-[0.5px] uppercase">Warning</span>
            </div>
            <p className="font-bold text-[#e17100] text-[28px] leading-[32px]">1</p>
          </div>
          
          <div className="bg-white rounded-[20px] p-[16px] shadow-[0_4px_12px_rgba(0,0,0,0.05)] flex flex-col gap-[6px] items-center text-center">
            <div className="flex items-center gap-[6px]">
              <div className="bg-[#003fb1] w-[8px] h-[8px] rounded-full"></div>
              <span className="font-bold text-[#6b7280] text-[10px] tracking-[0.5px] uppercase">Forecast</span>
            </div>
            <p className="font-bold text-[#003fb1] text-[28px] leading-[32px]">2</p>
          </div>
        </div>

        <div className="flex flex-col gap-[16px]">
          <h3 className="font-bold text-[#101828] text-[18px]">Active</h3>
          
          <div className="bg-white rounded-[24px] shadow-[0_4px_12px_rgba(0,0,0,0.05)] flex flex-col p-[20px]">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-[12px]">
                <div className="bg-[#fff1f2] px-[10px] py-[4px] rounded-[6px]">
                  <span className="font-bold text-[#ec003f] text-[11px] tracking-wide uppercase">Critical</span>
                </div>
                <span className="font-medium text-[#6b7280] text-[13px]">Tank C3</span>
                <span className="text-[#e5e7eb] text-[14px]">·</span>
                <span className="font-medium text-[#9ca3af] text-[13px]">Connection</span>
              </div>
              <span className="font-medium text-[#9ca3af] text-[11px] pt-[4px]">2h ago</span>
            </div>
            <p className="font-bold text-[#101828] text-[16px] mt-[16px]">Sensor offline</p>
            <p className="text-[#6b7280] text-[14px] leading-[22px] mt-[4px]">Aquasense Pro #3 has lost connection. Last reading 2h ago.</p>
          </div>

          <div className="bg-white rounded-[24px] shadow-[0_4px_12px_rgba(0,0,0,0.05)] flex flex-col p-[20px]">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-[12px]">
                <div className="bg-[#fff1f2] px-[10px] py-[4px] rounded-[6px]">
                  <span className="font-bold text-[#ec003f] text-[11px] tracking-wide uppercase">Critical</span>
                </div>
                <span className="font-medium text-[#6b7280] text-[13px]">Tank C3</span>
                <span className="text-[#e5e7eb] text-[14px]">·</span>
                <span className="font-medium text-[#9ca3af] text-[13px]">Temperature</span>
              </div>
              <span className="font-medium text-[#9ca3af] text-[11px] pt-[4px]">2h ago</span>
            </div>
            <p className="font-bold text-[#101828] text-[16px] mt-[16px]">32.4 °C — Above range</p>
            <p className="text-[#6b7280] text-[14px] leading-[22px] mt-[4px]">Exceeds optimal 25–30 °C threshold. Heater relay may be stuck ON.</p>
          </div>

          <div className="bg-white rounded-[24px] shadow-[0_4px_12px_rgba(0,0,0,0.05)] flex flex-col p-[20px]">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-[12px]">
                <div className="bg-[#fffbeb] px-[10px] py-[4px] rounded-[6px]">
                  <span className="font-bold text-[#e17100] text-[11px] tracking-wide uppercase">Warning</span>
                </div>
                <span className="font-medium text-[#6b7280] text-[13px]">Tank A1</span>
                <span className="text-[#e5e7eb] text-[14px]">·</span>
                <span className="font-medium text-[#9ca3af] text-[13px]">Turbidity</span>
              </div>
              <span className="font-medium text-[#9ca3af] text-[11px] pt-[4px]">34m ago</span>
            </div>
            <p className="font-bold text-[#101828] text-[16px] mt-[16px]">18 NTU — Elevated</p>
            <p className="text-[#6b7280] text-[14px] leading-[22px] mt-[4px]">Approaching the 20 NTU warning threshold. Consider partial water change.</p>
          </div>

          <div className="bg-white rounded-[24px] shadow-[0_4px_12px_rgba(0,0,0,0.05)] flex flex-col p-[20px]">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-[12px]">
                <div className="bg-[#eff6ff] px-[10px] py-[4px] rounded-[6px]">
                  <span className="font-bold text-[#003fb1] text-[11px] tracking-wide uppercase">AI Forecast</span>
                </div>
                <span className="font-medium text-[#6b7280] text-[13px]">Tank A1</span>
                <span className="text-[#e5e7eb] text-[14px]">·</span>
                <span className="font-medium text-[#9ca3af] text-[13px]">pH Forecast</span>
              </div>
              <span className="font-medium text-[#9ca3af] text-[11px] pt-[4px]">ML · 12m ago</span>
            </div>
            <p className="font-bold text-[#101828] text-[16px] mt-[16px]">Drop to 6.4 in ~3 h</p>
            <p className="text-[#6b7280] text-[14px] leading-[22px] mt-[4px]">LSTM model predicts pH will fall below optimal range (6.5–7.5) within 3 hours.</p>
          </div>

          <div className="bg-white rounded-[24px] shadow-[0_4px_12px_rgba(0,0,0,0.05)] flex flex-col p-[20px]">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-[12px]">
                <div className="bg-[#eff6ff] px-[10px] py-[4px] rounded-[6px]">
                  <span className="font-bold text-[#003fb1] text-[11px] tracking-wide uppercase">AI Forecast</span>
                </div>
                <span className="font-medium text-[#6b7280] text-[13px]">Nursery B</span>
                <span className="text-[#e5e7eb] text-[14px]">·</span>
                <span className="font-medium text-[#9ca3af] text-[13px]">Temp Forecast</span>
              </div>
              <span className="font-medium text-[#9ca3af] text-[11px] pt-[4px]">ML · 12m ago</span>
            </div>
            <p className="font-bold text-[#101828] text-[16px] mt-[16px]">Rise to 30.8 °C in ~4 h</p>
            <p className="text-[#6b7280] text-[14px] leading-[22px] mt-[4px]">LSTM model predicts temperature may exceed the upper threshold by hour 4.</p>
          </div>

        </div>

        <div className="flex flex-col gap-[16px] mt-[8px]">
          <h3 className="font-bold text-[#9ca3af] text-[18px]">Resolved</h3>
          
          <div className="bg-white rounded-[24px] shadow-[0_4px_12px_rgba(0,0,0,0.05)] flex flex-col p-[20px] opacity-60">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-[12px]">
                <div className="bg-[#fffbeb] px-[10px] py-[4px] rounded-[6px]">
                  <span className="font-bold text-[#e17100] text-[11px] tracking-wide uppercase">Warning</span>
                </div>
                <span className="font-medium text-[#6b7280] text-[13px]">Nursery B</span>
                <span className="text-[#e5e7eb] text-[14px]">·</span>
                <span className="font-medium text-[#9ca3af] text-[13px]">pH</span>
              </div>
              <span className="font-medium text-[#9ca3af] text-[11px] pt-[4px]">1h ago</span>
            </div>
            <p className="font-bold text-[#101828] text-[16px] mt-[16px]">6.6 — Near lower bound</p>
            <p className="text-[#6b7280] text-[14px] leading-[22px] mt-[4px]">pH is within range but trending downward. Monitor closely.</p>
          </div>
        </div>

      </div>
    </div>
  );
}
