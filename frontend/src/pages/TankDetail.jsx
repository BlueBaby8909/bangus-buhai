import { useState, useEffect } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useParams, useNavigate } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import { api, getWsUrl } from "../api/client";
import imgImage from "../assets/DeviceDetail/Device (Front).png";
import imgIconPh from "../assets/DeviceDetail/Ph(White).svg";
import imgIconTemp from "../assets/DeviceDetail/Temp(White).svg";
import imgIconTurb from "../assets/DashBoard/Turb(Gray).svg";
import imgIconBluePh from "../assets/DeviceDetail/Ph(LightBlue).svg";
import imgIconBlueTemp from "../assets/DeviceDetail/Temp(Blue).svg";
import EditTankModal from "../components/EditTankModal";
import PredictionHistoryModal from "../components/PredictionHistoryModal";

export default function TankDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [tank, setTank] = useState(null);
  const [device, setDevice] = useState(null);
  const [latest, setLatest] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [relayIsOn, setRelayIsOn] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState("temperature");
  const [showEditModal, setShowEditModal] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);

  const loadData = async () => {
    try {
      const [summary, pred, devices, logsResponse] = await Promise.all([
        api.getTankSummary(id),
        api.getLatestPrediction(id).catch(() => null),
        api.listDevices(),
        api.listWaterLogs(id, { limit: 48 }).catch(() => [])
      ]);
      setTank(summary.tank);
      setLatest(summary.latest_water_log || { temperature: 0, pH: 0, turbidity: 0, relay_on: false });
      setRelayIsOn(summary.latest_water_log?.relay_on ?? false);
      setPrediction(pred);
      const dev = devices.find(d => d.tank_id === summary.tank.id);
      setDevice(dev || { name: "Unknown Device", is_online: false });
      setHistory(logsResponse.slice().reverse());
      setError(null);
    } catch (err) {
      setError("Failed to load tank details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  useEffect(() => {
    if (!tank) return;
    const ws = new WebSocket(getWsUrl(`/ws/tanks/${tank.id}`));
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "new_reading") {
        setLatest(data.water_log);
        setRelayIsOn(data.water_log.relay_on);
        setHistory(prev => {
          const newHistory = [...prev, data.water_log];
          if (newHistory.length > 48) newHistory.shift();
          return newHistory;
        });
      } else if (data.type === "device_status") {
        setDevice(prev => prev ? { ...prev, is_online: data.is_online } : prev);
      } else if (data.type === "new_prediction") {
        setPrediction(data.prediction);
      }
    };
    return () => ws.close();
  }, [tank]);

  const handleToggleRelay = async () => {
    if (!device) return;
    const newState = !relayIsOn;
    setRelayIsOn(newState); // Optimistic UI
    try {
      await api.sendCommand(device.id, { relay: "heater", state: newState });
    } catch (err) {
      setRelayIsOn(!newState); // Revert on failure
      alert("Failed to send command to device.");
    }
  };

  const getPredictionStatus = (temp, ph) => {
    if (!temp || !ph) return { label: "Unknown", color: "bg-[#e5e7eb]", text: "text-[#5c666e]" };
    const isTempIdeal = temp >= 26 && temp <= 32;
    const isPhIdeal = ph >= 7.5 && ph <= 8.5;
    if (isTempIdeal && isPhIdeal) return { label: "Optimal", color: "bg-[#d0fae5]", text: "text-[#009966]" };
    return { label: "Caution", color: "bg-[#fef3c6]", text: "text-[#bb4d00]" };
  };

  if (loading) {
    return (
      <div className="bg-slate-50 flex flex-col min-h-screen items-center justify-center">
        <div className="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error || !tank) {
    return (
      <div className="bg-slate-50 flex flex-col min-h-screen p-10 items-center justify-center">
        <p className="text-slate-500">{error || "Tank not found."}</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-50 flex flex-col min-h-screen relative pb-[100px] md:pb-[40px]">
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
      <AppHeader 
        title={tank.name} 
        leftNode={
          <div 
            onClick={() => navigate("/tanks")}
            className="w-[40px] h-[40px] rounded-full bg-white shadow-sm border border-slate-100 flex items-center justify-center cursor-pointer hover:bg-slate-50 transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </div>
        } 
        rightNode={
          <div 
            onClick={() => setShowEditModal(true)}
            className="w-[40px] h-[40px] rounded-full bg-white shadow-sm border border-slate-100 flex items-center justify-center cursor-pointer hover:bg-slate-50 transition-colors"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
          </div>
        }
      />
      
      <div className="flex-1 w-full px-[16px] md:px-[40px] py-[20px] md:py-[32px] flex flex-col gap-[24px] md:gap-[32px]">
        
        {/* Device Status Header */}
        <div className="bg-white rounded-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] p-[20px] md:p-[24px] flex items-center gap-[16px]">
          <div className="bg-slate-50 rounded-[16px] w-[56px] h-[56px] md:w-[64px] md:h-[64px] flex items-center justify-center border border-slate-100">
            <img src={imgImage} alt="Aquasense Pro" className="w-[48px] h-[48px] md:w-[56px] md:h-[56px] object-contain" />
          </div>
          <div className="flex flex-col flex-1">
            <p className="font-bold text-slate-900 text-[16px] md:text-[20px] leading-[22px] md:leading-[26px]">{device?.name}</p>
            <p className="font-medium text-slate-500 text-[13px] md:text-[15px] leading-[18px] md:leading-[22px] mt-[2px] md:mt-[4px]">Monitoring pH · Temp · Turbidity</p>
          </div>
          <div className={`w-[12px] h-[12px] md:w-[16px] md:h-[16px] rounded-full shadow-sm ${device?.is_online ? "bg-sky-500" : "bg-slate-400"}`}></div>
        </div>

        {/* 2-Column Responsive Layout */}
        <div className="flex flex-col lg:grid lg:grid-cols-12 gap-[24px] md:gap-[32px]">
          
          {/* Left Column: Live Readings */}
          <div className="flex flex-col gap-[24px] lg:col-span-7">
            
            <div className="flex gap-[16px] md:gap-[24px] w-full">
              <div className="bg-white flex-1 rounded-[24px] p-[20px] md:p-[28px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition-shadow flex flex-col justify-between h-[180px] md:h-[220px] border-t-4 border-sky-500 relative overflow-hidden">
                <div className="flex items-center gap-[8px] md:gap-[12px] z-10">
                  <div className="bg-sky-50 p-[6px] md:p-[8px] rounded-[8px] md:rounded-[10px]">
                    <img src={imgIconBluePh} alt="pH" className="w-[12px] h-[16px] md:w-[16px] md:h-[20px]" style={{ filter: 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)' }} />
                  </div>
                  <span className="font-bold text-[15px] md:text-[18px] text-slate-900">pH</span>
                </div>
                <div className="flex flex-col z-10">
                  <span className="font-bold text-slate-900 text-[32px] md:text-[44px] leading-[32px] md:leading-[44px] tracking-[-1px]">{latest?.pH?.toFixed(1) ?? "--"}</span>
                  <span className="font-medium text-[12px] md:text-[14px] text-slate-500 mt-[8px] md:mt-[12px]">Normal 6.5 – 7.5</span>
                </div>
              </div>
              
              <div className="bg-white flex-1 rounded-[24px] p-[20px] md:p-[28px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition-shadow flex flex-col justify-between h-[180px] md:h-[220px] border-t-4 border-teal-500 relative overflow-hidden">
                <div className="flex items-center gap-[8px] md:gap-[12px] z-10">
                  <div className="bg-teal-50 p-[6px] md:p-[8px] rounded-[8px] md:rounded-[10px]">
                    <img src={imgIconBlueTemp} alt="Temp" className="w-[12px] h-[16px] md:w-[16px] md:h-[20px]" style={{ filter: 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(145deg) brightness(96%) contrast(97%)' }} />
                  </div>
                  <span className="font-bold text-[15px] md:text-[18px] text-slate-900">Temp</span>
                </div>
                <div className="flex flex-col z-10">
                  <span className="font-bold text-slate-900 text-[32px] md:text-[44px] leading-[32px] md:leading-[44px] tracking-[-1px]">{latest?.temperature?.toFixed(1) ?? "--"}°C</span>
                  <span className="font-medium text-[12px] md:text-[14px] text-slate-500 mt-[8px] md:mt-[12px]">Optimal 25°C – 30°C</span>
                </div>
              </div>
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
                  <span className="font-medium text-[13px] md:text-[15px] text-slate-500 mt-[8px]">{"Normal < 20 NTU"}</span>
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
                  <p className="font-bold text-slate-900 text-[18px] md:text-[20px] leading-[22px] md:leading-[26px]">{tank.name} — Heater</p>
                  <p className="font-medium text-slate-500 text-[14px] md:text-[15px] mt-[4px]">Send command via MQTT</p>
                </div>
                <div 
                  onClick={handleToggleRelay}
                  className={`w-[56px] h-[32px] md:w-[64px] md:h-[36px] rounded-full relative cursor-pointer transition-colors duration-300 ${relayIsOn ? 'bg-sky-500' : 'bg-slate-200'}`}
                >
                  <div 
                    className={`absolute w-[26px] h-[26px] md:w-[30px] md:h-[30px] bg-white rounded-full top-[3px] transition-all shadow-sm ${relayIsOn ? 'left-[27px] md:left-[31px]' : 'left-[3px]'}`}
                  ></div>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-[16px] md:gap-[20px]">
              <div className="flex justify-between items-center">
                <h3 className="font-bold text-slate-900 text-[20px] md:text-[22px]">4-Hour AI Forecast</h3>
                <button 
                  onClick={() => setShowHistoryModal(true)}
                  className="text-sky-500 font-bold text-[13px] hover:text-sky-600 transition-colors"
                >
                  View History
                </button>
              </div>
              <div className="grid grid-cols-2 gap-[16px] md:gap-[20px]">
                {!prediction ? (
                  <div className="col-span-2 text-slate-500 bg-white rounded-[24px] p-6 text-center">No AI prediction available yet. Data requires a sequence of 48 readings.</div>
                ) : (
                  [1, 2, 3, 4].map(hr => {
                    const temp = prediction[`temperature_${hr}h`];
                    const ph = prediction[`pH_${hr}h`];
                    const status = getPredictionStatus(temp, ph);
                    
                    return (
                      <div key={hr} className="bg-white rounded-[24px] p-[20px] md:p-[24px] flex flex-col items-center gap-[16px] md:gap-[20px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition-shadow">
                        <div className="bg-sky-50 text-sky-700 font-bold text-[11px] md:text-[12px] tracking-[1px] uppercase px-[12px] py-[6px] md:px-[14px] md:py-[8px] rounded-full w-max">
                          +{hr} HR
                        </div>
                        <div className="flex flex-col gap-[12px] items-center w-full">
                          <div className="flex items-center gap-[6px]">
                            <img src={imgIconBlueTemp} alt="Temp" className="w-[8px] h-[16px] md:w-[10px] md:h-[18px]" style={{ filter: 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)' }} />
                            <span className="font-bold text-slate-900 text-[22px] md:text-[26px] tracking-[-0.5px]">{temp?.toFixed(1) ?? "--"}°C</span>
                          </div>
                          <div className="flex items-center gap-[6px]">
                            <img src={imgIconBluePh} alt="pH" className="w-[12px] h-[16px] md:w-[14px] md:h-[18px]" style={{ filter: 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)' }} />
                            <span className="font-bold text-slate-900 text-[22px] md:text-[26px] tracking-[-0.5px]">{ph?.toFixed(1) ?? "--"}</span>
                          </div>
                          <div className="flex items-center gap-[6px]">
                            <img src={imgIconTurb} alt="Turbidity" className="w-[12px] h-[10px] md:w-[14px] md:h-[12px] brightness-0" style={{ filter: 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)' }} />
                            <span className="font-bold text-slate-900 text-[22px] md:text-[26px] tracking-[-0.5px]">{prediction[`turbidity_${hr}h`]?.toFixed(1) ?? "--"} <span className="text-[12px] md:text-[14px] text-slate-500 font-medium">NTU</span></span>
                          </div>
                        </div>
                        <div className={`px-[16px] py-[8px] md:px-[20px] md:py-[10px] rounded-full w-full flex justify-center mt-1 md:mt-2 ${status.label === "Optimal" ? "bg-emerald-50" : status.color}`}>
                          <span className={`font-bold text-[13px] md:text-[14px] ${status.label === "Optimal" ? "text-emerald-700" : status.text}`}>{status.label}</span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

          </div>
        </div>

        {/* Historical Data Section */}
        <div className="bg-white rounded-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] p-[24px] md:p-[32px] flex flex-col gap-[24px]">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-[16px]">
            <h3 className="font-bold text-slate-900 text-[20px] md:text-[22px]">Historical Data (Last 4 Hours)</h3>
            <div className="flex bg-slate-50 p-[4px] rounded-full w-full md:w-auto">
              <button 
                onClick={() => setActiveTab("temperature")}
                className={`flex-1 md:flex-none px-[16px] py-[6px] rounded-full font-bold text-[13px] md:text-[14px] transition-colors ${activeTab === "temperature" ? "bg-white text-sky-600 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
              >
                Temp
              </button>
              <button 
                onClick={() => setActiveTab("pH")}
                className={`flex-1 md:flex-none px-[16px] py-[6px] rounded-full font-bold text-[13px] md:text-[14px] transition-colors ${activeTab === "pH" ? "bg-white text-teal-600 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
              >
                pH
              </button>
              <button 
                onClick={() => setActiveTab("turbidity")}
                className={`flex-1 md:flex-none px-[16px] py-[6px] rounded-full font-bold text-[13px] md:text-[14px] transition-colors ${activeTab === "turbidity" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
              >
                Turbidity
              </button>
            </div>
          </div>
          
          <div className="h-[250px] md:h-[300px] w-full mt-[8px]">
            {history.length === 0 ? (
              <div className="w-full h-full flex items-center justify-center text-slate-500 font-medium bg-slate-50 rounded-[16px]">No historical data available.</div>
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
                          const date = new Date(prediction.predicted_from);
                          date.setHours(date.getHours() + hr);
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
