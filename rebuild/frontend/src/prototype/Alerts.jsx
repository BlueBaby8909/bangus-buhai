// Summary markup adapted from frontend/src/pages/Alerts.jsx; no invented counts.
import { Link } from "react-router-dom";
import { Badge } from "../components";
export default function Alerts() {
  return (
    <div className="px-[16px] md:px-[40px] py-[24px] md:py-[40px] flex flex-col gap-[24px] md:gap-[32px]">
      <div className="grid grid-cols-3 gap-[12px] md:gap-[24px]">
        <div className="bg-white rounded-[20px] md:rounded-[24px] p-[16px] md:p-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition-shadow flex flex-col gap-[6px] md:gap-[12px] items-center text-center">
          <div className="flex items-center gap-[6px]">
            <div className="bg-slate-400 w-[8px] h-[8px] md:w-[10px] md:h-[10px] rounded-full"></div>
            <span className="font-bold text-slate-500 text-[10px] md:text-[12px] tracking-[0.5px] uppercase">
              Critical
            </span>
          </div>
          <p className="font-bold text-slate-400 text-[28px] md:text-[40px] leading-[32px] md:leading-[48px]">
            —
          </p>
        </div>

        <div className="bg-white rounded-[20px] md:rounded-[24px] p-[16px] md:p-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition-shadow flex flex-col gap-[6px] md:gap-[12px] items-center text-center">
          <div className="flex items-center gap-[6px]">
            <div className="bg-slate-400 w-[8px] h-[8px] md:w-[10px] md:h-[10px] rounded-full"></div>
            <span className="font-bold text-slate-500 text-[10px] md:text-[12px] tracking-[0.5px] uppercase">
              Warning
            </span>
          </div>
          <p className="font-bold text-slate-400 text-[28px] md:text-[40px] leading-[32px] md:leading-[48px]">
            —
          </p>
        </div>

        <div className="bg-white rounded-[20px] md:rounded-[24px] p-[16px] md:p-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition-shadow flex flex-col gap-[6px] md:gap-[12px] items-center text-center">
          <div className="flex items-center gap-[6px]">
            <div className="bg-slate-400 w-[8px] h-[8px] md:w-[10px] md:h-[10px] rounded-full"></div>
            <span className="font-bold text-slate-500 text-[10px] md:text-[12px] tracking-[0.5px] uppercase">
              Forecast
            </span>
          </div>
          <p className="font-bold text-slate-400 text-[28px] md:text-[40px] leading-[32px] md:leading-[48px]">
            —
          </p>
        </div>
      </div>

      <h2 className="text-[18px] md:text-[24px] font-bold text-slate-900">
        Alerts
      </h2>
      <section className="bg-white rounded-[24px] p-[24px] md:p-[40px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] text-center flex flex-col items-center gap-4">
        <Badge>Not available yet</Badge>
        <p className="text-slate-500 text-sm">
          Alerts will appear here when monitoring is enabled.
        </p>
        <Link className="button primary pill" to="/tanks">
          View tank readings
        </Link>
      </section>
    </div>
  );
}
