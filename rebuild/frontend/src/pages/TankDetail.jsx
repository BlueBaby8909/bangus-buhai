import { useState, useEffect, useCallback, useRef } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useParams, useNavigate } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import { api } from "../api/client";
import imgImage from "../assets/DeviceDetail/Device (Front).png";
import imgIconTurb from "../assets/DashBoard/Turb(Gray).svg";
import imgIconBluePh from "../assets/DeviceDetail/Ph(LightBlue).svg";
import imgIconBlueTemp from "../assets/DeviceDetail/Temp(Blue).svg";
import EditTankModal from "../components/EditTankModal";
import PredictionHistoryModal from "../components/PredictionHistoryModal";
import ReadingStatus from "../components/ReadingStatus.jsx";
import { phProvenanceLabel } from "../presentation.js";
import { createRequestGate } from '../services/requestGate.js';
import { LoadingState, RequestError } from '../components/RequestState.jsx';
import ForecastCard from '../components/ForecastCard.jsx';
import MetricCard from '../components/MetricCard.jsx';
import ManualReadingModal from '../components/ManualReadingModal.jsx';

export default function TankDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [tank, setTank] = useState(null);
  const [device, setDevice] = useState(null);
  const [latest, setLatest] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [relayIsOn, setRelayIsOn] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState("temperature");
  const [showEditModal, setShowEditModal] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [showManualReading, setShowManualReading] = useState(false);
  const [partialErrors, setPartialErrors] = useState([]);
  const gate = useRef(createRequestGate());

  const loadData = useCallback(async () => {
    const isCurrent = gate.current.begin();
    setLoading(true);
    setError(null);
    const failures = [];
    try {
      const [summary, pred, devices, logsResponse] = await Promise.all([
        api.getTankSummary(id),
        api.getLatestPrediction(id).catch(() => { failures.push('Forecast could not be loaded.'); return null }),
        api.listDevices(),
        api.listWaterLogs(id, { limit: 48 }).catch(() => { failures.push('History could not be loaded.'); return [] })
      ]);
      if (!isCurrent()) return;
      setTank(summary.tank);
      setLatest(summary.latest_water_log || null);
      setRelayIsOn(typeof summary.latest_water_log?.relay_on === 'boolean' ? summary.latest_water_log.relay_on : null);
      setPrediction(pred);
      const dev = devices.find(d => String(d.tank_id) === String(summary.tank.id));
      setDevice(dev || { name: "No device assigned", connection_state: 'unknown' });
      setHistory(logsResponse.slice().sort((a,b) => Date.parse(a.recorded_at) - Date.parse(b.recorded_at)));
      setPartialErrors(failures);
      setError(null);
    } catch (error) {
      if (isCurrent()) setError(error.message || "Unable to load tank details.");
    } finally {
      if (isCurrent()) setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    const requestGate = gate.current;
    void Promise.resolve().then(loadData);
    return () => requestGate.cancel();
  }, [loadData]);

  if (loading) {
    return (
      <><AppHeader title="Tank details" /><LoadingState /></>
    );
  }

  if (error || !tank) {
    return (
      <><AppHeader title="Tank details" /><RequestError message={error || "Tank not found."} onRetry={loadData} /></>
    );
  }

  return (
    <div className="bg-slate-50 flex flex-col min-h-screen relative pb-[100px] md:pb-[40px]">
      {showManualReading && <ManualReadingModal tankId={tank.id} onClose={() => setShowManualReading(false)}
        onSuccess={() => {setShowManualReading(false);loadData()}} />}
      {showEditModal && (
        <EditTankModal 
          tank={tank} 
          onClose={() => setShowEditModal(false)} 
          onSuccess={() => {
            setShowEditModal(false);
            setLoading(true);
            loadData();
          }}
        />
      )}
      {showHistoryModal && (
        <PredictionHistoryModal 
          tankId={tank.id} 
          onClose={() => setShowHistoryModal(false)} 
        />
      )}
      <AppHeader title={tank.name} onBack={() => navigate("/tanks")} onSettings={() => setShowEditModal(true)} />
      
      <div className="flex-1 w-full px-[16px] md:px-[40px] py-[20px] md:py-[32px] flex flex-col gap-[24px] md:gap-[32px]">
        
        {/* Device Status Header */}
        <div className="bg-white rounded-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] p-[20px] md:p-[24px] flex items-center gap-[16px]">
          <div className="bg-slate-50 rounded-[16px] w-[56px] h-[56px] md:w-[64px] md:h-[64px] flex items-center justify-center border border-slate-100">
            <img src={imgImage} alt="Aquasense Pro" className="w-[48px] h-[48px] md:w-[56px] md:h-[56px] object-contain" />
          </div>
          <div className="flex flex-col flex-1">
            <p className="font-bold text-slate-900 text-[16px] md:text-[20px] leading-[22px] md:leading-[26px]">{device?.name}</p>
            <p className="font-medium text-slate-500 text-[13px] md:text-[15px] leading-[18px] md:leading-[22px] mt-[2px] md:mt-[4px]">pH · Temperature · Turbidity<span className="block mt-1 font-semibold text-slate-700">{device?.connection_state === "unknown" ? "Device status unknown" : device?.is_online ? "Device online" : "Device offline"}</span></p>
          </div>
          <div className={`w-[12px] h-[12px] md:w-[16px] md:h-[16px] rounded-full shadow-sm ${device?.is_online ? "bg-sky-500" : "bg-slate-400"}`}></div>
        </div>

        <ReadingStatus tank={tank} />
        {partialErrors.length > 0 && <RequestError message={partialErrors.join(' ')} onRetry={loadData} />}

        {/* 2-Column Responsive Layout */}
        <div className="flex flex-col lg:grid lg:grid-cols-12 gap-[24px] md:gap-[32px]">
          
          {/* Left Column: Live Readings */}
          <div className="flex flex-col gap-[24px] lg:col-span-7">
            
            <div className="flex gap-[16px] md:gap-[24px] w-full">
              <MetricCard label="pH" value={latest?.pH} icon={imgIconBluePh}
                description={latest?.pH != null ? phProvenanceLabel(latest.ph_provenance) : 'No pH reading'} />
              <MetricCard label="Temp" value={latest?.temperature} unit="°C" icon={imgIconBlueTemp} tone="teal"
                description={latest?.freshness === 'stale' ? 'Last known · stale' : latest?.temperature != null ? 'Temperature' : 'No temperature reading'} />
            </div>

            <div className="bg-white rounded-[24px] p-[24px] md:p-[32px] flex items-center justify-between w-full shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition-shadow">
              <div className="flex flex-col gap-[16px] md:gap-[24px]">
                <div className="flex items-center gap-[10px] md:gap-[14px]">
                  <div className="bg-sky-50 w-[32px] h-[32px] md:w-[48px] md:h-[48px] rounded-[10px] md:rounded-[14px] flex items-center justify-center">
                    <img src={imgIconTurb} alt="Turbidity" className="w-[16px] h-[13px] md:w-[24px] md:h-[20px] brightness-0" style={{ filter: 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)' }} />
                  </div>
                  <span className="font-bold text-[16px] md:text-[20px] text-slate-900">Turbidity</span>
                </div>
                <div className="flex flex-col">
                  <div className="flex items-end gap-[6px]">
                    <span className="font-bold text-slate-900 text-[36px] md:text-[48px] leading-[36px] md:leading-[48px] tracking-[-1px]">{latest?.turbidity?.toFixed(1) ?? "--"}</span>
                    <span className="font-medium text-slate-500 text-[16px] md:text-[20px] pb-[4px]">NTU</span>
                  </div>
                  <span className="font-medium text-[13px] md:text-[15px] text-slate-500 mt-[8px]">{latest?.turbidity != null ? "Turbidity · NTU" : "No turbidity reading"}</span>
                </div>
              </div>
              <div className="flex items-end gap-[6px] md:gap-[8px] h-[48px] md:h-[64px] opacity-70">
                <div className="bg-slate-200 w-[14px] md:w-[18px] h-[20px] md:h-[26px] rounded-[4px] md:rounded-[6px]"></div>
                <div className="bg-slate-200 w-[14px] md:w-[18px] h-[36px] md:h-[48px] rounded-[4px] md:rounded-[6px]"></div>
                <div className="bg-sky-500 w-[14px] md:w-[18px] h-[48px] md:h-[64px] rounded-[4px] md:rounded-[6px]"></div>
                <div className="bg-slate-200 w-[14px] md:w-[18px] h-[18px] md:h-[24px] rounded-[4px] md:rounded-[6px]"></div>
              </div>
            </div>

          </div>

          {/* Right Column: Controls & Forecast */}
          <div className="flex flex-col gap-[24px] lg:col-span-5">
            
            <div className="bg-white rounded-[24px] p-[24px] md:p-[32px] flex flex-col shadow-[0_4px_20px_rgba(15,23,42,0.04)]">
              <p className="font-bold text-slate-400 text-[12px] md:text-[14px] tracking-[0.8px] uppercase">Relay Control</p>
              <div className="flex items-center justify-between mt-[16px] md:mt-[24px]">
                <div className="flex flex-col">
                  <p className="font-bold text-slate-900 text-[18px] md:text-[20px] leading-[22px] md:leading-[26px]">{tank.name} — Relay</p>
                  <p className="font-medium text-slate-500 text-[14px] md:text-[15px] mt-[4px]">{typeof relayIsOn === 'boolean' ? `Last reported: ${relayIsOn ? 'ON' : 'OFF'}` : 'Reported state unavailable'}</p>
                </div>
                <button type="button" role="switch" aria-label="Relay control" aria-checked={relayIsOn === true} disabled title="Relay commands are unavailable"
                  className={`w-[56px] h-[32px] md:w-[64px] md:h-[36px] rounded-full relative cursor-pointer transition-colors duration-300 ${relayIsOn ? 'bg-sky-500' : 'bg-slate-200'}`}
                >
                  <div 
                    className={`absolute w-[26px] h-[26px] md:w-[30px] md:h-[30px] bg-white rounded-full top-[3px] transition-all shadow-sm ${relayIsOn ? 'left-[27px] md:left-[31px]' : 'left-[3px]'}`}
                  ></div>
                </button>
              </div>
              <p className="mt-3 text-sm text-slate-500">Relay commands are unavailable.</p>
            </div>

            <div className="flex flex-col gap-[16px] md:gap-[20px]">
              <div className="flex flex-wrap gap-3 justify-between items-center">
                <h3 className="font-bold text-slate-900 text-[20px] md:text-[22px]">4-Hour Forecast</h3>
                <button 
                  onClick={() => setShowHistoryModal(true)}
                  className="text-sky-500 font-bold text-[13px] hover:text-sky-600 transition-colors"
                >
                  View History
                </button>
              </div>
              <div className="grid grid-cols-2 gap-[16px] md:gap-[20px]">
                {!prediction ? (
                  <div className="col-span-2 text-slate-500 bg-white rounded-[24px] p-6 text-center">No forecast available.</div>
                ) : (
                  [1, 2, 3, 4].map(hour => <ForecastCard key={hour} hour={hour} prediction={prediction} />)
                )}
              </div>
            </div>

          </div>
        </div>

        {/* Historical Data Section */}
        <div className="bg-white rounded-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] p-[24px] md:p-[32px] flex flex-col gap-[24px]">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-[16px]">
            <h3 className="font-bold text-slate-900 text-[20px] md:text-[22px]">Recent History and Forecast</h3>
            <button type="button" onClick={() => setShowManualReading(true)} className="rounded-full bg-sky-600 text-white px-5 py-3 font-bold text-sm">Add Reading</button>
            <div className="flex bg-slate-50 p-[4px] rounded-full w-full md:w-auto">
              <button 
                aria-pressed={activeTab === "temperature"} onClick={() => setActiveTab("temperature")}
                className={`flex-1 md:flex-none px-[16px] py-[6px] rounded-full font-bold text-[13px] md:text-[14px] transition-colors ${activeTab === "temperature" ? "bg-white text-sky-600 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
              >
                Temp
              </button>
              <button 
                aria-pressed={activeTab === "pH"} onClick={() => setActiveTab("pH")}
                className={`flex-1 md:flex-none px-[16px] py-[6px] rounded-full font-bold text-[13px] md:text-[14px] transition-colors ${activeTab === "pH" ? "bg-white text-teal-600 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
              >
                pH
              </button>
              <button 
                aria-pressed={activeTab === "turbidity"} onClick={() => setActiveTab("turbidity")}
                className={`flex-1 md:flex-none px-[16px] py-[6px] rounded-full font-bold text-[13px] md:text-[14px] transition-colors ${activeTab === "turbidity" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
              >
                Turbidity
              </button>
            </div>
          </div>
          
          <div className="h-[250px] md:h-[300px] w-full mt-[8px]">
            {history.length === 0 || !history.some((item) => Number.isFinite(item[activeTab])) ? (
              <div className="w-full h-full flex items-center justify-center text-slate-500 font-medium bg-slate-50 rounded-[16px]">No readings available for this parameter.</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis 
                    dataKey="recorded_at"
                    type="category"
                    allowDuplicatedCategory={false}
                    tickFormatter={(tick) => {
                      if (!tick) return "";
                      const date = new Date(tick);
                      return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
                    }}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                    dy={10}
                    minTickGap={30}
                  />
                  <YAxis 
                    domain={['auto', 'auto']} 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                    dx={-10}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(15,23,42,0.08)' }}
                    labelFormatter={(label) => {
                      if (!label) return "";
                      return new Date(label).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    }}
                  />
                  {/* Historical Line */}
                  <Line 
                    data={history}
                    type="monotone" 
                    dataKey={activeTab} 
                    stroke={activeTab === "temperature" ? "#0ea5e9" : activeTab === "pH" ? "#14b8a6" : "#475569"} 
                    strokeWidth={3}
                    dot={false}
                    activeDot={{ r: 6, fill: activeTab === "temperature" ? "#0ea5e9" : activeTab === "pH" ? "#14b8a6" : "#475569", stroke: "#fff", strokeWidth: 2 }}
                    isAnimationActive={false}
                  />
                  {/* Prediction Line */}
                  {prediction && (
                    <Line 
                      data={[
                        // Connect to the last historical point
                        history[history.length - 1],
                        ...[1, 2, 3, 4].map(hr => {
                          const date = new Date(prediction[`target_${hr}h`]);
                          return {
                            recorded_at: date.toISOString(),
                            temperature: prediction[`temperature_${hr}h`],
                            pH: prediction[`pH_${hr}h`],
                            turbidity: prediction[`turbidity_${hr}h`]
                          };
                        })
                      ]}
                      type="monotone" 
                      dataKey={activeTab} 
                      stroke={activeTab === "temperature" ? "#0ea5e9" : activeTab === "pH" ? "#14b8a6" : "#475569"} 
                      strokeWidth={3}
                      strokeDasharray="5 5"
                      dot={{ r: 4, fill: "#fff", stroke: activeTab === "temperature" ? "#0ea5e9" : activeTab === "pH" ? "#14b8a6" : "#475569", strokeWidth: 2 }}
                      activeDot={{ r: 6 }}
                      isAnimationActive={false}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
