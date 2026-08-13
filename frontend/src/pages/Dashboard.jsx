import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import { api, getWsUrl } from "../api/client";
import powerButtonIcon from "../assets/DashBoard/PowerButton.svg";
import imgImageAquasenseProDevice from "../assets/DashBoard/Device (Front).png";
import imgIcon2 from "../assets/DashBoard/Star.svg";
import imgIcon4 from "../assets/DashBoard/Temp(Orange).svg";
import imgIcon5 from "../assets/DashBoard/Ph(Blue).svg";
import imgIcon6 from "../assets/DashBoard/Turb(Gray).svg";

export default function Dashboard() {
  const [firstTank, setFirstTank] = useState(null);
  const [firstDevice, setFirstDevice] = useState(null);
  const [latestLog, setLatestLog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function loadData() {
      try {
        const [tanks, devices] = await Promise.all([
          api.listTanks(),
          api.listDevices(),
        ]);
        if (!mounted) return;
        if (tanks.length > 0) {
          const tank = tanks[0];
          setFirstTank(tank);
          const summary = await api.getTankSummary(tank.id);
          if (!mounted) return;
          setLatestLog(summary.latest_water_log);
          const device = devices.find((d) => d.id === tank.device_id);
          setFirstDevice(
            device || { name: "Unknown Device", is_online: false },
          );
        }
      } catch (err) {
        if (mounted) setError("Failed to load dashboard data.");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadData();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!firstTank) return;
    const ws = new WebSocket(getWsUrl(`/ws/tanks/${firstTank.id}`));
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "new_reading") {
        setLatestLog(data.water_log);
      } else if (data.type === "device_status") {
        setFirstDevice((prev) =>
          prev ? { ...prev, is_online: data.is_online } : prev,
        );
      }
    };
    return () => ws.close();
  }, [firstTank]);

  const displayLog = {
    temp: latestLog?.temperature?.toFixed(1) ?? "--",
    ph: latestLog?.pH?.toFixed(1) ?? "--",
    turbidity: latestLog?.turbidity?.toFixed(1) ?? "--",
  };

  if (loading) {
    return (
      <div className="bg-slate-50 flex flex-col min-h-screen items-center justify-center">
        <div className="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error || !firstTank) {
    return (
      <div className="bg-slate-50 flex flex-col min-h-screen p-10 items-center justify-center">
        <p className="text-slate-500">
          {error || "No tanks available. Please add a tank."}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-slate-50 flex flex-col min-h-screen">
      <AppHeader
        title="Hatchery Monitor"
        leftNode={
          <div className="bg-white rounded-full p-[8px] md:p-[10px] shadow-sm border border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="md:w-[24px] md:h-[24px]"
            >
              <path
                d="M3 12H21M3 6H21M3 18H21"
                stroke="#64748b"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        }
      />
      <div className="flex-1 w-full pb-[32px] pt-[24px] px-[16px] md:px-[40px] md:py-[40px] flex flex-col gap-[24px] md:gap-[40px]">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-[16px]">
          <div className="flex flex-col">
            <h2 className="font-bold text-slate-900 text-[26px] md:text-[36px] leading-[30px] md:leading-[40px] tracking-[-0.5px]">
              Hello, Manager
            </h2>
            <p className="text-slate-500 text-[14px] md:text-[16px] leading-[20px] md:leading-[24px] mt-1 md:mt-2">
              Bangus BuhAI water quality at a glance.
            </p>
          </div>

          <div className="bg-white rounded-[24px] p-[20px] flex items-center gap-[16px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] md:min-w-[340px]">
            <div className="bg-sky-50 rounded-[16px] w-[48px] h-[48px] flex items-center justify-center shrink-0">
              <img
                src={imgIcon2}
                alt="AI"
                className="w-[24px] h-[24px]"
                style={{
                  filter:
                    "invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)",
                }}
              />
            </div>
            <div className="flex flex-col flex-1">
              <h3 className="font-bold text-slate-900 text-[15px] md:text-[16px] leading-[20px]">
                AI Forecasting Active
              </h3>
              <p className="text-slate-500 text-[13px] md:text-[14px] leading-[18px] mt-[2px]">
                Predicting Temp · pH · Turbidity
              </p>
            </div>
            <div className="bg-sky-50 rounded-full px-[12px] py-[6px]">
              <span className="font-bold text-sky-700 text-[11px] md:text-[12px]">
                LSTM
              </span>
            </div>
          </div>
        </div>

        {/* Dashboard Content Grid */}
        <div className="flex flex-col md:grid md:grid-cols-2 md:gap-[32px] gap-[24px]">
          {/* Primary Tank */}
          <div className="flex flex-col gap-[12px] md:gap-[20px]">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-slate-900 text-[18px] md:text-[22px] leading-[28px]">
                Primary Tank
              </h3>
              <Link
                to="/tanks"
                className="bg-sky-600 hover:bg-sky-700 transition-colors rounded-full px-[16px] md:px-[20px] py-[8px] md:py-[10px] text-white text-[13px] md:text-[14px] font-bold shadow-sm"
              >
                See All
              </Link>
            </div>

            <Link
              to={`/tanks/${firstTank.id}`}
              className="bg-white hover:shadow-[0_8px_30px_rgba(15,23,42,0.08)] transition-all rounded-[32px] overflow-hidden shadow-[0_4px_24px_rgba(15,23,42,0.05)] flex flex-col h-[280px] md:h-[340px] block group"
            >
              <div className="p-[24px] md:p-[32px] flex-1 flex flex-col relative z-10">
                <div className="flex justify-between items-start">
                  <div className="flex flex-col">
                    <h4 className="font-bold text-slate-900 text-[20px] md:text-[24px]">
                      {firstTank.name}
                    </h4>
                    <p className="font-medium text-slate-500 text-[14px] md:text-[16px] mt-[2px]">
                      {firstDevice?.name}
                    </p>
                    <p
                      className={`font-medium text-[14px] md:text-[16px] mt-[4px] flex items-center gap-[6px] ${firstDevice?.is_online ? "text-sky-600" : "text-slate-400"}`}
                    >
                      <span
                        className={`w-[8px] h-[8px] rounded-full ${firstDevice?.is_online ? "bg-sky-500" : "bg-slate-300"}`}
                      ></span>
                      {firstDevice?.is_online ? "Connected" : "Disconnected"}
                    </p>
                  </div>
                  <div className="bg-sky-50 rounded-[16px] w-[48px] h-[48px] md:w-[56px] md:h-[56px] flex items-center justify-center group-hover:bg-sky-100 transition-colors">
                    <img
                      src={powerButtonIcon}
                      alt="Power"
                      className="w-[23px] h-[23px] md:w-[28px] md:h-[28px]"
                      style={{
                        filter:
                          "invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)",
                      }}
                    />
                  </div>
                </div>

                <div className="mt-auto flex justify-between items-end">
                  <div className="flex flex-col mb-4 md:mb-6">
                    <p className="font-bold text-slate-400 text-[12px] md:text-[14px] tracking-[0.8px] uppercase">
                      Sensors Active
                    </p>
                    <p className="font-bold text-sky-600 text-[48px] md:text-[56px] leading-[48px] md:leading-[56px] tracking-[-1.2px] mt-1 md:mt-2">
                      3{" "}
                      <span className="text-[24px] md:text-[28px] text-slate-300">
                        / 3
                      </span>
                    </p>
                  </div>
                  <img
                    src={imgImageAquasenseProDevice}
                    alt="Device"
                    className="w-[140px] h-[120px] md:w-[180px] md:h-[160px] object-contain drop-shadow-xl group-hover:scale-105 transition-transform duration-500 origin-bottom-right"
                  />
                </div>
              </div>
              <div className="px-[24px] md:px-[32px] pb-[24px] md:pb-[32px] pt-[8px] md:pt-[12px] relative z-10">
                <div className="bg-slate-100 h-[8px] md:h-[10px] rounded-full w-full overflow-hidden">
                  <div className="bg-sky-500 h-full w-[100%] rounded-full"></div>
                </div>
              </div>
            </Link>
          </div>

          {/* Live Readings */}
          <div className="flex flex-col gap-[12px] md:gap-[20px]">
            <h3 className="font-bold text-slate-900 text-[18px] md:text-[22px] leading-[28px]">
              Live Readings
            </h3>
            <div className="grid grid-cols-2 grid-rows-2 gap-[16px] md:gap-[24px] h-[280px] md:h-[340px]">
              {/* Temperature Card */}
              <div className="bg-sky-600 hover:bg-sky-700 transition-colors rounded-[24px] p-[20px] md:p-[28px] shadow-[0_4px_20px_rgba(2,132,199,0.2)] flex flex-col justify-between overflow-hidden relative min-h-[140px] cursor-pointer">
                <div className="flex justify-between items-start z-10">
                  <img
                    src={imgIcon4}
                    alt="Temp"
                    className="w-[16px] h-[16px] md:w-[20px] md:h-[20px] brightness-0 invert"
                  />
                  <span className="bg-white/20 text-white text-[11px] md:text-[13px] font-bold px-[10px] md:px-[12px] py-[4px] md:py-[6px] rounded-full backdrop-blur-md shadow-sm">
                    Avg
                  </span>
                </div>
                <div className="flex flex-col z-10 mt-auto">
                  <div className="flex items-end gap-[2px]">
                    <span className="font-bold text-white text-[40px] md:text-[48px] leading-[40px] md:leading-[48px] tracking-[-1px]">
                      {displayLog.temp}
                    </span>
                    <span className="font-semibold text-white text-[20px] md:text-[24px] leading-[28px] pb-[4px]">
                      °C
                    </span>
                  </div>
                  <span className="font-medium text-sky-100 text-[13px] md:text-[15px] mt-1 md:mt-2">
                    Temperature
                  </span>
                </div>
              </div>

              {/* pH Card */}
              <div className="bg-white hover:bg-slate-50 transition-colors rounded-[24px] p-[20px] md:p-[28px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] flex flex-col justify-between overflow-hidden relative min-h-[140px] cursor-pointer">
                <div className="flex justify-between items-start z-10">
                  <img
                    src={imgIcon5}
                    alt="pH"
                    className="w-[16px] h-[20px] md:w-[20px] md:h-[24px]"
                    style={{
                      filter:
                        "invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)",
                    }}
                  />
                  <span className="bg-sky-50 text-sky-700 text-[11px] md:text-[13px] font-bold px-[10px] md:px-[12px] py-[4px] md:py-[6px] rounded-full">
                    Optimal
                  </span>
                </div>
                <div className="flex flex-col z-10 mt-auto">
                  <span className="font-bold text-slate-900 text-[40px] md:text-[48px] leading-[40px] md:leading-[48px] tracking-[-1px]">
                    {displayLog.ph}
                  </span>
                  <span className="font-medium text-slate-500 text-[13px] md:text-[15px] mt-1 md:mt-2">
                    pH Level
                  </span>
                </div>
              </div>

              {/* Turbidity Card */}
              <div className="col-span-2 bg-white hover:bg-slate-50 transition-colors rounded-[24px] p-[24px] md:p-[32px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] flex justify-between items-end min-h-[140px] cursor-pointer">
                <div className="flex flex-col justify-between h-full z-10 w-full">
                  <div className="bg-sky-50 w-[32px] h-[32px] md:w-[48px] md:h-[48px] rounded-[10px] md:rounded-[14px] flex items-center justify-center mb-[12px] md:mb-[16px]">
                    <img
                      src={imgIcon6}
                      alt="Turbidity"
                      className="w-[16px] h-[14px] md:w-[24px] md:h-[20px]"
                      style={{
                        filter:
                          "invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)",
                      }}
                    />
                  </div>
                  <div className="flex justify-between items-end w-full mt-auto">
                    <div className="flex flex-col">
                      <div className="flex items-end gap-[4px]">
                        <span className="font-bold text-slate-900 text-[40px] md:text-[56px] leading-[40px] md:leading-[56px] tracking-[-1px]">
                          {displayLog.turbidity}
                        </span>
                        <span className="font-semibold text-slate-500 text-[20px] md:text-[24px] leading-[28px] pb-[4px]">
                          NTU
                        </span>
                      </div>
                      <span className="font-medium text-slate-500 text-[13px] md:text-[15px] mt-1">
                        Turbidity
                      </span>
                    </div>
                    <div className="flex items-end gap-[6px] md:gap-[8px] h-[40px] md:h-[56px] opacity-80 pb-[2px] md:pb-[4px] z-10">
                      <div className="w-[14px] md:w-[18px] h-[12px] md:h-[16px] bg-slate-100 rounded-[4px] md:rounded-[6px]"></div>
                      <div className="w-[14px] md:w-[18px] h-[20px] md:h-[28px] bg-slate-100 rounded-[4px] md:rounded-[6px]"></div>
                      <div className="w-[14px] md:w-[18px] h-[28px] md:h-[40px] bg-slate-100 rounded-[4px] md:rounded-[6px]"></div>
                      <div className="w-[14px] md:w-[18px] h-[40px] md:h-[56px] bg-sky-500 rounded-[4px] md:rounded-[6px]"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
