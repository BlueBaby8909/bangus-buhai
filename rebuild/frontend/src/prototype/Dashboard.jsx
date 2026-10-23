// Page markup adapted directly from frontend/src/pages/Dashboard.jsx.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth-context";
import { useTankStream } from "../useTankStream";
import { metric, display, timestamp } from "../readings";
import { ErrorBox, Empty, Future } from "../components";
import powerButtonIcon from "../prototype-assets/DashBoard/PowerButton.svg";
import imgImageAquasenseProDevice from "../prototype-assets/DashBoard/Device (Front).png";
import imgIcon4 from "../prototype-assets/DashBoard/Temp(Orange).svg";
import imgIcon5 from "../prototype-assets/DashBoard/Ph(Blue).svg";
import imgIcon6 from "../prototype-assets/DashBoard/Turb(Gray).svg";
export default function Dashboard({ overview }) {
  const { hatchery } = useAuth(),
    { data } = overview;
  const [tankId, setTankId] = useState(""),
    [deviceId, setDeviceId] = useState(""),
    [now, setNow] = useState(Date.now);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const selected =
    data.items.find((item) => item.tank.id === tankId) ||
    data.items.find((item) => item.devices.length) ||
    data.items[0];
  const firstTank = selected?.tank,
    firstDevice =
      selected?.devices.find((d) => d.device_id === deviceId) ||
      selected?.devices[0];
  const stream = useTankStream(hatchery, firstTank?.id);
  const reading =
    stream.rows.find(
      (r) =>
        r.origin === "device" &&
        r.device_id === firstDevice?.device_id &&
        r.binding_id === firstDevice?.binding?.id,
    ) || firstDevice?.latest;
  const samples = Object.fromEntries(
    ["temperature", "ph", "turbidity"].map((key) => [
      key,
      metric(reading, key, now + (data.serverOffset || 0)),
    ]),
  );
  const displayLog = {
    temp: display(samples.temperature.value),
    ph: display(samples.ph.value),
    turbidity: display(samples.turbidity.value),
  };

  return (
    <div className="bg-slate-50 flex flex-col min-h-screen">
      <div className="flex-1 w-full pb-[32px] pt-[24px] px-[16px] md:px-[40px] md:py-[40px] flex flex-col gap-[24px] md:gap-[40px]">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-[16px]">
          <div className="flex flex-col">
            <h2 className="font-bold text-slate-900 text-[26px] md:text-[36px] leading-[30px] md:leading-[40px] tracking-[-0.5px]">
              Hello, Manager
            </h2>
            <p className="text-slate-500 text-[14px] md:text-[16px] leading-[20px] md:leading-[24px] mt-1 md:mt-2">
              Bangus BuhAI readings at a glance.
            </p>
          </div>
        </div>

        <div className="prototype-selection">
          <label htmlFor="overview-tank">
            Tank
            <select
              id="overview-tank"
              aria-label="Overview tank"
              value={firstTank?.id || ""}
              onChange={(e) => {
                setTankId(e.target.value);
                setDeviceId("");
              }}
            >
              {data.items.map((item) => (
                <option key={item.tank.id} value={item.tank.id}>
                  {item.tank.name}
                </option>
              ))}
            </select>
          </label>
          {firstDevice && (
            <label htmlFor="overview-device">
              Device
              <select
                id="overview-device"
                aria-label="Overview device"
                value={firstDevice.device_id}
                onChange={(e) => setDeviceId(e.target.value)}
              >
                {selected.devices.map((device) => (
                  <option key={device.id} value={device.device_id}>
                    {device.display_name || device.device_id}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button onClick={overview.refresh}>Refresh overview</button>
        </div>
        <ErrorBox error={overview.error || stream.error} />
        {overview.loading && <p role="status">Loading tanks…</p>}
        {!firstTank ? (
          <Empty>No tanks yet. Open Tanks to create your first tank.</Empty>
        ) : (
          <>
            {/* Dashboard Content Grid */}
            <div className="flex flex-col md:grid md:grid-cols-2 md:gap-[32px] gap-[24px]">
              {/* Primary tank */}
              <div className="flex flex-col gap-[12px] md:gap-[20px]">
                <div className="flex justify-between items-center">
                  <h3 className="font-bold text-slate-900 text-[18px] md:text-[22px] leading-[28px]">
                    Primary tank
                  </h3>
                  <Link
                    to="/tanks"
                    className="bg-sky-600 hover:bg-sky-700 transition-colors rounded-full px-[16px] md:px-[20px] py-[8px] md:py-[10px] text-white text-[13px] md:text-[14px] font-bold shadow-sm"
                  >
                    See all tanks
                  </Link>
                </div>

                <Link
                  to={`/tanks/${firstTank.id}`}
                  className="bg-white hover:shadow-[0_8px_30px_rgba(15,23,42,0.08)] transition-all rounded-[32px] overflow-hidden shadow-[0_4px_24px_rgba(15,23,42,0.05)] flex flex-col min-h-[280px] md:min-h-[340px] block group"
                >
                  <div className="p-[24px] md:p-[32px] flex-1 flex flex-col relative z-10">
                    <div className="flex justify-between items-start">
                      <div className="flex flex-col">
                        <h4 className="font-bold text-slate-900 text-[20px] md:text-[24px]">
                          {firstTank.name}
                        </h4>
                        <p className="font-medium text-slate-500 text-[14px] md:text-[16px] mt-[2px]">
                          {firstDevice?.display_name ||
                            firstDevice?.device_id ||
                            "No device assigned"}
                        </p>
                        <p
                          className={`font-medium text-[14px] md:text-[16px] mt-[4px] flex items-center gap-[6px] ${"text-slate-500"}`}
                        >
                          <span
                            className={`w-[8px] h-[8px] rounded-full ${"bg-slate-300"}`}
                          ></span>
                          Device connectivity unknown
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
                          Assigned devices
                        </p>
                        <p className="font-bold text-sky-600 text-[48px] md:text-[56px] leading-[48px] md:leading-[56px] tracking-[-1.2px] mt-1 md:mt-2">
                          {selected.devices.length}
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
                    Assignment {firstDevice?.configuration?.status || "unknown"}
                  </div>
                </Link>
              </div>

              {/* Live readings */}
              <div className="flex flex-col gap-[12px] md:gap-[20px]">
                <h3 className="font-bold text-slate-900 text-[18px] md:text-[22px] leading-[28px]">
                  Live readings
                </h3>
                <p className="muted">{stream.status}</p>
                <div className="metrics grid grid-cols-2 gap-[16px] md:gap-[24px]">
                  {/* Temperature Card */}
                  <div className="metric-temperature bg-sky-600 hover:bg-sky-700 transition-colors rounded-[24px] p-[20px] md:p-[28px] shadow-[0_4px_20px_rgba(2,132,199,0.2)] flex flex-col justify-between overflow-hidden relative min-h-[160px] md:min-h-[180px]">
                    <div className="flex justify-between items-start z-10">
                      <img
                        src={imgIcon4}
                        alt="Temp"
                        className="w-[16px] h-[16px] md:w-[20px] md:h-[20px] brightness-0 invert"
                      />
                      <span className="bg-white/20 text-white text-[11px] md:text-[13px] font-bold px-[10px] md:px-[12px] py-[4px] md:py-[6px] rounded-full backdrop-blur-md shadow-sm">
                        {samples.temperature.label}
                      </span>
                    </div>
                    <div className="flex flex-col z-10 mt-auto">
                      <div className="flex items-end gap-[2px]">
                        <strong className="font-bold text-white text-[40px] md:text-[48px] leading-[40px] md:leading-[48px] tracking-[-1px]">
                          {displayLog.temp}
                        </strong>
                        <span className="font-semibold text-white text-[20px] md:text-[24px] leading-[28px] pb-[4px]">
                          °C
                        </span>
                      </div>
                      <span className="font-medium text-sky-100 text-[13px] md:text-[15px] mt-1 md:mt-2">
                        Temperature · {samples.temperature.source}
                      </span>
                    </div>
                  </div>

                  {/* pH Card */}
                  <div className="metric-ph bg-white hover:bg-slate-50 transition-colors rounded-[24px] p-[20px] md:p-[28px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] flex flex-col justify-between overflow-hidden relative min-h-[160px] md:min-h-[180px]">
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
                      <span
                        title={samples.ph.label}
                        className="bg-sky-50 text-sky-700 text-[11px] md:text-[13px] font-bold px-[10px] md:px-[12px] py-[4px] md:py-[6px] rounded-full"
                      >
                        {samples.ph.label === "Default · unverified"
                          ? "Unverified"
                          : samples.ph.label}
                      </span>
                    </div>
                    <div className="flex flex-col z-10 mt-auto">
                      <strong className="font-bold text-slate-900 text-[40px] md:text-[48px] leading-[40px] md:leading-[48px] tracking-[-1px]">
                        {displayLog.ph}
                      </strong>
                      <span className="font-medium text-slate-500 text-[13px] md:text-[15px] mt-1 md:mt-2">
                        pH · {samples.ph.source}
                      </span>
                    </div>
                  </div>

                  {/* Turbidity Card */}
                  <div className="metric-turbidity col-span-2 bg-white hover:bg-slate-50 transition-colors rounded-[24px] p-[24px] md:p-[32px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] flex justify-between items-end min-h-[160px] md:min-h-[180px]">
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
                            <strong className="font-bold text-slate-900 text-[40px] md:text-[56px] leading-[40px] md:leading-[56px] tracking-[-1px]">
                              {displayLog.turbidity}
                            </strong>
                            <span className="font-semibold text-slate-500 text-[20px] md:text-[24px] leading-[28px] pb-[4px]">
                              NTU
                            </span>
                          </div>
                          <span className="font-medium text-slate-500 text-[13px] md:text-[15px] mt-1">
                            Turbidity · {samples.turbidity.source}
                          </span>
                          <span className="text-xs text-slate-500">
                            {samples.turbidity.label}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <p className="metric-time">
              Measured: {timestamp(reading?.measured_at)}
              <br />
              Received:{" "}
              {reading?.received_at
                ? timestamp(reading.received_at)
                : "No delivery yet"}
            </p>
          </>
        )}
        <Future title="Forecasts">Not available yet.</Future>
        <Future title="Water-quality classification">Not available yet.</Future>
      </div>
    </div>
  );
}
