// Adapted from the original frontend/src/components/AppHeader.jsx.

export default function AppHeader({ title, leftNode, rightNode }) {
  return (
    <header className="bg-white/80 backdrop-blur-md flex items-center justify-between h-[64px] md:h-[80px] px-[16px] md:px-[40px] w-full border-b border-slate-100 sticky top-0 z-40">
      <div className="flex items-center w-[40px] md:w-[60px]">{leftNode}</div>
      <h1 className="header-title font-bold text-slate-900 text-[18px] md:text-[22px] tracking-[-0.45px]">
        {title}
      </h1>
      <div className="flex items-center justify-end min-w-[40px] md:min-w-[60px]">
        {rightNode}
      </div>
    </header>
  );
}
