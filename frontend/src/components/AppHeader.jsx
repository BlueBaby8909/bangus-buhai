import bellIcon from '../assets/Header/Bell.svg';

export default function AppHeader({ title, leftNode, rightNode }) {
  return (
    <div className="bg-white/80 backdrop-blur-md flex items-center justify-between h-[64px] md:h-[80px] px-[16px] md:px-[40px] w-full border-b border-slate-100 sticky top-0 z-40">
      <div className="flex items-center w-[40px] md:w-[60px]">
        {leftNode}
      </div>
      <h1 className="font-bold text-slate-900 text-[18px] md:text-[22px] tracking-[-0.45px]">
        {title}
      </h1>
      <div className="flex items-center justify-end min-w-[40px] md:min-w-[60px]">
        {rightNode !== undefined ? (
          rightNode
        ) : (
          <div className="relative p-[8px] md:p-[10px] bg-slate-50 rounded-full flex justify-center items-center hover:bg-slate-100 transition-colors cursor-pointer">
            <img src={bellIcon} alt="Alerts" className="w-[16px] h-[20px] md:w-[20px] md:h-[24px]" />
            <div className="absolute top-[8px] right-[8px] md:top-[10px] md:right-[10px] w-[8px] h-[8px] bg-cyan-400 border-[1.2px] border-solid border-white rounded-full shadow-[0_0_8px_rgba(34,211,238,0.8)]"></div>
          </div>
        )}
      </div>
    </div>
  );
}
