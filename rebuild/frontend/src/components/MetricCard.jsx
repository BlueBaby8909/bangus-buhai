export default function MetricCard({ label, value, unit = '', description, icon, tone = 'sky' }) {
  const teal = tone === 'teal'
  return <div className={`bg-white flex-1 min-w-0 rounded-[24px] p-[20px] md:p-[28px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] flex flex-col justify-between h-[180px] md:h-[220px] border-t-4 relative overflow-hidden ${teal ? 'border-teal-500' : 'border-sky-500'}`}>
    <div className="flex items-center gap-[8px] md:gap-[12px]">
      <div className={`p-[6px] md:p-[8px] rounded-[8px] ${teal ? 'bg-teal-50' : 'bg-sky-50'}`}>
        <img src={icon} alt="" className="w-[12px] h-[16px] md:w-[16px] md:h-[20px]" style={{ filter: teal ? 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(145deg) brightness(96%) contrast(97%)' : 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)' }} />
      </div>
      <span className="font-bold text-[15px] md:text-[18px] text-slate-900">{label}</span>
    </div>
    <div className="flex flex-col">
      <span className="font-bold text-slate-900 text-[32px] md:text-[44px] leading-[32px] md:leading-[44px] tracking-[-1px]">{Number.isFinite(value) ? `${value.toFixed(1)}${unit}` : '—'}</span>
      <span className="font-medium text-[12px] md:text-[14px] text-slate-500 mt-[8px] md:mt-[12px]">{description}</span>
    </div>
  </div>
}
