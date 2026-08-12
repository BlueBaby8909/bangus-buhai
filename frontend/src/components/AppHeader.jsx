import bellIcon from '../assets/Header/Bell.svg';

export default function AppHeader({ title, leftNode }) {
  return (
    <div className="bg-white flex items-center justify-between h-[64px] px-[16px] w-full drop-shadow-[0px_1px_0.5px_rgba(0,0,0,0.05)] sticky top-0 z-50">
      <div className="flex items-center w-[40px]">
        {leftNode}
      </div>
      <h1 className="font-bold text-[#003fb1] text-[18px] tracking-[-0.45px]">
        {title}
      </h1>
      <div className="flex items-center justify-end w-[40px]">
        <div className="relative p-[8px] bg-gray-50 rounded-full flex justify-center items-center">
          <img src={bellIcon} alt="Alerts" className="w-[16px] h-[20px]" />
          <div className="absolute top-[8px] right-[8px] w-[8px] h-[8px] bg-[#00bc7d] border-[1.2px] border-solid border-white rounded-full"></div>
        </div>
      </div>
    </div>
  );
}
