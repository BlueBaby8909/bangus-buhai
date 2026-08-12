import { Link } from "react-router-dom";
import AppHeader from "../components/AppHeader";

export default function Alerts() {
  return (
    <div className="bg-white flex flex-col min-h-screen">
      <AppHeader 
        title="Alerts" 
        leftNode={
          <div className="w-[34px] h-[34px] rounded-full flex items-center justify-center">
            {/* Generic back button if needed, but the design 6-2 shows an icon which is probably a menu or similar. Using a menu icon. */}
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 12H21M3 6H21M3 18H21" stroke="#5c666e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        }
      />
      
      {/* We add a custom right area for the header to match the design's badges */}
      {/* But since AppHeader takes only title and leftNode, we can't easily add rightNode without modifying AppHeader. */}
      {/* Wait, AppHeader has a Bell icon hardcoded on the right. In Alerts design, the header right has "2" in red and "1" in orange. Let's just live with the Bell icon for now or I can update AppHeader to accept rightNode. */}
      {/* Let's just modify the content area to show the grid. */}

      <div 
        className="flex-1 w-full pb-[32px] pt-[24px] px-[16px] flex flex-col gap-[24px]"
        style={{ backgroundImage: "linear-gradient(133.21deg, rgb(235, 245, 255) 8.48%, rgb(240, 246, 255) 91.51%)" }}
      >
        <div className="grid grid-cols-3 gap-[12px]">
          <div className="bg-white border-[1.2px] border-[#f3f4f6] rounded-[12px] p-[12px] drop-shadow-[0px_2px_4px_rgba(0,0,0,0.05)] flex flex-col gap-[4px]">
            <div className="flex items-center gap-[6px]">
              <div className="bg-[#ff2056] w-[8px] h-[8px] rounded-full"></div>
              <span className="font-semibold text-[#99a1af] text-[10px] tracking-[0.25px] uppercase">Critical</span>
            </div>
            <p className="font-bold text-[#ec003f] text-[24px] leading-[32px]">2</p>
          </div>
          
          <div className="bg-white border-[1.2px] border-[#f3f4f6] rounded-[12px] p-[12px] drop-shadow-[0px_2px_4px_rgba(0,0,0,0.05)] flex flex-col gap-[4px]">
            <div className="flex items-center gap-[6px]">
              <div className="bg-[#ffb900] w-[8px] h-[8px] rounded-full"></div>
              <span className="font-semibold text-[#99a1af] text-[10px] tracking-[0.25px] uppercase">Warning</span>
            </div>
            <p className="font-bold text-[#e17100] text-[24px] leading-[32px]">1</p>
          </div>
          
          <div className="bg-white border-[1.2px] border-[#f3f4f6] rounded-[12px] p-[12px] drop-shadow-[0px_2px_4px_rgba(0,0,0,0.05)] flex flex-col gap-[4px]">
            <div className="flex items-center gap-[6px]">
              <div className="bg-[#003fb1] w-[8px] h-[8px] rounded-full"></div>
              <span className="font-semibold text-[#99a1af] text-[10px] tracking-[0.25px] uppercase">AI Forecast</span>
            </div>
            <p className="font-bold text-[#003fb1] text-[24px] leading-[32px]">2</p>
          </div>
        </div>

        <div className="flex flex-col gap-[12px]">
          <h3 className="font-semibold text-[#364153] text-[15px] leading-[22.5px]">Active</h3>
          
          <div className="bg-white border-[1.2px] border-[#f3f4f6] rounded-[16px] shadow-[0px_2px_8px_0px_rgba(0,0,0,0.06)] overflow-hidden flex flex-col">
            <div className="bg-[#ec003f] h-[4px] w-full"></div>
            <div className="p-[16px] flex flex-col">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-[8px]">
                  <div className="bg-[#fff1f2] px-[8px] py-[2px] rounded-[4px]">
                    <span className="font-semibold text-[#ec003f] text-[11px]">Critical</span>
                  </div>
                  <span className="font-semibold text-[#364153] text-[12px]">Tank C3</span>
                  <span className="text-[#d1d5dc] text-[12px]">·</span>
                  <span className="text-[#99a1af] text-[12px]">Connection</span>
                </div>
                <span className="text-[#99a1af] text-[11px] pt-[2px]">2h ago</span>
              </div>
              <p className="font-semibold text-[#101828] text-[15px] mt-[8px]">Sensor offline</p>
              <p className="text-[#99a1af] text-[13px] leading-[21px] mt-[4px]">Aquasense Pro #3 has lost connection. Last reading 2h ago.</p>
            </div>
          </div>

          <div className="bg-white border-[1.2px] border-[#f3f4f6] rounded-[16px] shadow-[0px_2px_8px_0px_rgba(0,0,0,0.06)] overflow-hidden flex flex-col">
            <div className="bg-[#ec003f] h-[4px] w-full"></div>
            <div className="p-[16px] flex flex-col">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-[8px]">
                  <div className="bg-[#fff1f2] px-[8px] py-[2px] rounded-[4px]">
                    <span className="font-semibold text-[#ec003f] text-[11px]">Critical</span>
                  </div>
                  <span className="font-semibold text-[#364153] text-[12px]">Tank C3</span>
                  <span className="text-[#d1d5dc] text-[12px]">·</span>
                  <span className="text-[#99a1af] text-[12px]">Temperature</span>
                </div>
                <span className="text-[#99a1af] text-[11px] pt-[2px]">2h ago</span>
              </div>
              <p className="font-semibold text-[#101828] text-[15px] mt-[8px]">32.4 °C — Above range</p>
              <p className="text-[#99a1af] text-[13px] leading-[21px] mt-[4px]">Exceeds optimal 25–30 °C threshold. Heater relay may be stuck ON.</p>
            </div>
          </div>

          <div className="bg-white border-[1.2px] border-[#f3f4f6] rounded-[16px] shadow-[0px_2px_8px_0px_rgba(0,0,0,0.06)] overflow-hidden flex flex-col">
            <div className="bg-[#fe9a00] h-[4px] w-full"></div>
            <div className="p-[16px] flex flex-col">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-[8px]">
                  <div className="bg-[#fffbeb] px-[8px] py-[2px] rounded-[4px]">
                    <span className="font-semibold text-[#e17100] text-[11px]">Warning</span>
                  </div>
                  <span className="font-semibold text-[#364153] text-[12px]">Tank A1</span>
                  <span className="text-[#d1d5dc] text-[12px]">·</span>
                  <span className="text-[#99a1af] text-[12px]">Turbidity</span>
                </div>
                <span className="text-[#99a1af] text-[11px] pt-[2px]">34m ago</span>
              </div>
              <p className="font-semibold text-[#101828] text-[15px] mt-[8px]">18 NTU — Elevated</p>
              <p className="text-[#99a1af] text-[13px] leading-[21px] mt-[4px]">Approaching the 20 NTU warning threshold. Consider partial water change.</p>
            </div>
          </div>

          <div className="bg-white border-[1.2px] border-[#f3f4f6] rounded-[16px] shadow-[0px_2px_8px_0px_rgba(0,0,0,0.06)] overflow-hidden flex flex-col">
            <div className="bg-[#003fb1] h-[4px] w-full"></div>
            <div className="p-[16px] flex flex-col">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-[8px]">
                  <div className="bg-[#eff6ff] px-[8px] py-[2px] rounded-[4px]">
                    <span className="font-semibold text-[#003fb1] text-[11px]">AI Forecast</span>
                  </div>
                  <span className="font-semibold text-[#364153] text-[12px]">Tank A1</span>
                  <span className="text-[#d1d5dc] text-[12px]">·</span>
                  <span className="text-[#99a1af] text-[12px]">pH Forecast</span>
                </div>
                <span className="text-[#99a1af] text-[11px] pt-[2px]">ML · 12m ago</span>
              </div>
              <p className="font-semibold text-[#101828] text-[15px] mt-[8px]">Drop to 6.4 in ~3 h</p>
              <p className="text-[#99a1af] text-[13px] leading-[21px] mt-[4px]">LSTM model predicts pH will fall below optimal range (6.5–7.5) within 3 hours.</p>
            </div>
          </div>

          <div className="bg-white border-[1.2px] border-[#f3f4f6] rounded-[16px] shadow-[0px_2px_8px_0px_rgba(0,0,0,0.06)] overflow-hidden flex flex-col">
            <div className="bg-[#003fb1] h-[4px] w-full"></div>
            <div className="p-[16px] flex flex-col">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-[8px]">
                  <div className="bg-[#eff6ff] px-[8px] py-[2px] rounded-[4px]">
                    <span className="font-semibold text-[#003fb1] text-[11px]">AI Forecast</span>
                  </div>
                  <span className="font-semibold text-[#364153] text-[12px]">Nursery B</span>
                  <span className="text-[#d1d5dc] text-[12px]">·</span>
                  <span className="text-[#99a1af] text-[12px]">Temp Forecast</span>
                </div>
                <span className="text-[#99a1af] text-[11px] pt-[2px]">ML · 12m ago</span>
              </div>
              <p className="font-semibold text-[#101828] text-[15px] mt-[8px]">Rise to 30.8 °C in ~4 h</p>
              <p className="text-[#99a1af] text-[13px] leading-[21px] mt-[4px]">LSTM model predicts temperature may exceed the upper threshold by hour 4.</p>
            </div>
          </div>

        </div>

        <div className="flex flex-col gap-[12px] mt-[12px]">
          <h3 className="font-semibold text-[#99a1af] text-[15px] leading-[22.5px]">Resolved</h3>
          
          <div className="bg-white border-[1.2px] border-[#f3f4f6] rounded-[16px] shadow-[0px_2px_8px_0px_rgba(0,0,0,0.06)] overflow-hidden flex flex-col opacity-50">
            <div className="bg-[#fe9a00] h-[4px] w-full"></div>
            <div className="p-[16px] flex flex-col">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-[8px]">
                  <div className="bg-[#fffbeb] px-[8px] py-[2px] rounded-[4px]">
                    <span className="font-semibold text-[#e17100] text-[11px]">Warning</span>
                  </div>
                  <span className="font-semibold text-[#364153] text-[12px]">Nursery B</span>
                  <span className="text-[#d1d5dc] text-[12px]">·</span>
                  <span className="text-[#99a1af] text-[12px]">pH</span>
                </div>
                <span className="text-[#99a1af] text-[11px] pt-[2px]">1h ago</span>
              </div>
              <p className="font-semibold text-[#101828] text-[15px] mt-[8px]">6.6 — Near lower bound</p>
              <p className="text-[#99a1af] text-[13px] leading-[21px] mt-[4px]">pH is within range but trending downward. Monitor closely.</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
