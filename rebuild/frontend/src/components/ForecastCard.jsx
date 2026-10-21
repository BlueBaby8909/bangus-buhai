import temperatureIcon from '../assets/DeviceDetail/Temp(Blue).svg'
import phIcon from '../assets/DeviceDetail/Ph(LightBlue).svg'
import turbidityIcon from '../assets/DashBoard/Turb(Gray).svg'
import { formatTimestamp, phProvenanceLabel } from '../presentation.js'

export default function ForecastCard({ prediction, hour }) {
  const metrics = [
    { key: 'temperature', icon: temperatureIcon, label: 'Temperature', unit: '°C' },
    { key: 'pH', icon: phIcon, label: 'pH', unit: '' },
    { key: 'turbidity', icon: turbidityIcon, label: 'Turbidity', unit: 'NTU' },
  ]
  return <div className="bg-white rounded-[24px] p-[20px] md:p-[24px] flex flex-col items-center gap-[16px] md:gap-[20px] shadow-[0_4px_20px_rgba(15,23,42,0.04)]">
    <div className="bg-sky-50 text-sky-700 font-bold text-[11px] md:text-[12px] tracking-[1px] uppercase px-[12px] py-[6px] rounded-full">+{hour} HR</div>
    <div className="flex flex-col gap-[12px] items-center w-full">{metrics.map(({ key, icon, label, unit }) => {
      const value = prediction[`${key}_${hour}h`]
      return <div key={key} className="flex items-center gap-[6px]">
        <img src={icon} alt={label} className="w-[12px] h-[16px]" style={{ filter: 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)' }} />
        <span className="font-bold text-slate-900 text-[22px] md:text-[26px] tracking-[-0.5px]">{Number.isFinite(value) ? value.toFixed(1) : 'Unavailable'} {unit}</span>
      </div>
    })}</div>
    <p className="text-xs text-amber-800 text-center">{phProvenanceLabel(prediction.ph_provenance)}</p>
    <time className="text-xs text-slate-500 text-center" dateTime={prediction[`target_${hour}h`]}>{formatTimestamp(prediction[`target_${hour}h`])}</time>
    <div className="px-[16px] py-[8px] rounded-full w-full text-center bg-slate-100 text-slate-600 text-[13px] font-bold">Forecast</div>
  </div>
}
