// Page markup adapted directly from frontend/src/pages/Tanks.jsx.
import { Link } from "react-router-dom";
import imgImageAquasensePro from "../prototype-assets/Tanks/Device (Angled).png";
import arrowBlue from "../prototype-assets/Tanks/Arrow(Blue).svg";
import arrowGray from "../prototype-assets/Tanks/Arrow(Gray).svg";
import imgImage from "../prototype-assets/Tanks/Device (Front).png";
export default function Tanks({ overview, onEdit, onClaim, recovery }) {
  const { loading, error } = overview;
  const displayTanks = overview.data.items.map(({ tank, devices }) => ({
    ...tank,
    _count: devices.length,
  }));
  return (
    <div className="bg-slate-50 flex flex-col min-h-screen">
      <div className="flex-1 w-full pb-[32px] pt-[16px] px-[16px] md:px-[40px] md:py-[32px] flex flex-col gap-[24px] md:gap-[32px]">
        {/* Header Hero */}
        <div className="bg-white rounded-[32px] shadow-[0_4px_24px_rgba(15,23,42,0.05)] flex flex-col overflow-hidden relative">
          <div className="h-[180px] md:h-[240px] relative w-full p-[24px] md:p-[40px] z-10 flex items-center">
            <div className="absolute left-[24px] md:left-[40px] w-[180px] md:w-[300px] flex flex-col">
              <div className="bg-sky-50 rounded-[12px] w-[44px] h-[44px] md:w-[56px] md:h-[56px] flex items-center justify-center mb-[16px] shadow-sm">
                <img
                  src={arrowBlue}
                  alt=""
                  className="w-[20px] h-[17px] md:w-[24px] md:h-[20px] brightness-0 invert filter hue-rotate-180"
                  style={{
                    filter:
                      "invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)",
                  }}
                />
              </div>
              <h2 className="font-bold text-slate-900 text-[26px] md:text-[36px] leading-[30px] md:leading-[40px] tracking-[-0.6px]">
                Tank
                <br />
                Management
              </h2>
            </div>
            <div className="absolute right-[-20px] md:right-[40px] top-[10px] md:top-[20px] w-[200px] md:w-[260px] h-[170px] md:h-[220px] drop-shadow-xl">
              <img
                src={imgImageAquasensePro}
                alt="Aquasense Pro"
                className="w-full h-full object-contain"
              />
            </div>
          </div>
          <div className="bg-sky-600 px-[24px] md:px-[40px] py-[20px] flex justify-between items-center z-10">
            <div className="flex items-center gap-[12px] md:gap-[16px]">
              <div className="bg-sky-300 w-[10px] h-[10px] rounded-full shadow-[0_0_8px_rgba(125,211,252,0.8)]"></div>
              <div className="flex flex-col">
                <span className="font-bold text-white text-[14px] md:text-[16px] leading-[18px] md:leading-[20px]">
                  Monitoring devices
                </span>
                <span className="font-medium text-sky-100 text-[12px] md:text-[14px] leading-[16px] md:leading-[18px]">
                  Assignments and history
                </span>
              </div>
            </div>
            <button
              onClick={onClaim}
              className="bg-white hover:bg-sky-50 transition-colors rounded-full px-[16px] py-[8px] md:px-[20px] md:py-[10px] flex items-center gap-[6px] shadow-sm"
            >
              <span className="font-bold text-sky-700 text-[13px] md:text-[14px]">
                Add device
              </span>
              <img
                src={arrowBlue}
                alt=""
                className="w-[12px] h-[12px] md:w-[14px] md:h-[14px]"
                style={{
                  filter:
                    "invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)",
                }}
              />
            </button>
          </div>
        </div>

        <div className="toolbar">
          <label className="check">
            <input
              type="checkbox"
              checked={overview.archived}
              onChange={(e) => overview.setArchived(e.target.checked)}
            />
            Include archived tanks
          </label>
          <button onClick={overview.refresh}>Refresh tanks</button>
        </div>
        {/* Tanks List */}
        <div className="flex flex-col gap-[16px] md:gap-[24px]">
          <div className="flex justify-between items-center px-[4px]">
            <h3 className="font-bold text-slate-900 text-[20px] md:text-[24px] leading-[28px]">
              Your Tanks
            </h3>
            <div className="flex items-center gap-[16px] md:gap-[24px]">
              <button
                onClick={() => onEdit(null)}
                className="bg-slate-900 hover:bg-slate-800 text-white rounded-full px-[16px] py-[8px] font-bold text-[13px] md:text-[14px] flex items-center gap-[6px] shadow-sm transition-colors"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M7 1V13M1 7H13"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                New tank
              </button>
            </div>
          </div>

          <div className="flex flex-col md:grid md:grid-cols-2 lg:grid-cols-3 gap-[16px] md:gap-[24px]">
            {loading ? (
              <div className="col-span-full py-10 flex justify-center">
                <div className="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : error ? (
              <div className="col-span-full py-10 text-center text-slate-500">
                Could not load tanks. Try Refresh tanks.
              </div>
            ) : displayTanks.length === 0 ? (
              <div className="col-span-full py-10 text-center text-slate-500">
                No tanks found.
              </div>
            ) : (
              displayTanks.map((tank) => {
                const statusInfo = {
                  text: tank.archived_at ? "Archived" : "Registered",
                  dot: "bg-slate-300",
                  color: "#64748b",
                };

                return (
                  <Link
                    key={tank.id}
                    to={`/tanks/${tank.id}`}
                    className={`tank-card bg-white rounded-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.08)] min-h-[116px] md:min-h-[132px] p-[20px] md:p-[24px] flex items-center gap-[16px] overflow-hidden relative block group transition-all duration-300`}
                  >
                    <div
                      className={`bg-slate-50 border border-slate-100 rounded-[16px] w-[72px] h-[72px] md:w-[84px] md:h-[84px] flex items-center justify-center shrink-0`}
                    >
                      <img
                        src={imgImage}
                        alt="Tank"
                        className="w-[64px] h-[64px] md:w-[72px] md:h-[72px] object-contain"
                      />
                    </div>
                    <div className="flex flex-col flex-1 min-w-0">
                      <h4 className="font-bold text-slate-900 text-[18px] md:text-[20px] leading-[22px]">
                        {tank.name}
                      </h4>
                      <p className="font-medium text-slate-500 text-[14px] md:text-[15px] leading-[20px] mt-[2px]">
                        {tank._count} assigned{" "}
                        {tank._count === 1 ? "device" : "devices"}
                      </p>
                      <div className="flex items-center gap-[6px] mt-[6px] md:mt-[8px]">
                        <div
                          className={`w-[8px] h-[8px] rounded-full ${statusInfo.dot}`}
                        ></div>
                        <span
                          className={`font-bold text-[13px] md:text-[14px] leading-[19px]`}
                          style={{ color: statusInfo.color }}
                        >
                          {statusInfo.text}
                        </span>
                      </div>
                    </div>
                    <div className="w-[32px] h-[32px] md:w-[40px] md:h-[40px] rounded-full bg-slate-50 flex items-center justify-center group-hover:bg-slate-100 transition-colors">
                      <img
                        src={arrowGray}
                        alt="Go"
                        className="w-[6px] h-[10px] md:w-[8px] md:h-[12px]"
                      />
                    </div>
                  </Link>
                );
              })
            )}
          </div>
        </div>
        {overview.data.next_cursor && (
          <button disabled={loading} onClick={overview.more}>
            Load more tanks
          </button>
        )}
        {recovery}
      </div>
    </div>
  );
}
