import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import bellIcon from '../assets/Header/Bell.svg'
import { getDataMode } from '../../services/dataSource.js'

const destinations = [['/', 'Dashboard'], ['/tanks', 'Tanks'], ['/alerts', 'Alerts'], ['/data', 'Data']]
export default function AppHeader({ title, leftNode, rightNode }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuButton = useRef(null)
  const location = useLocation()
  const sampleMode=getDataMode()==='sample'
  useEffect(() => { document.title = `${title} · Bangus BuhAI${sampleMode?' · Sample preview':''}` }, [title,sampleMode])
  const backAction = leftNode?.props?.onClick
  const settingsAction = rightNode?.props?.onClick
  return (
    <header className="bg-white/95 backdrop-blur-md flex items-center justify-between min-h-[64px] md:min-h-[80px] px-[16px] md:px-[40px] w-full border-b border-slate-100 sticky top-0 z-40 gap-3">
      <button ref={menuButton} type="button" aria-label={backAction ? 'Back to tanks' : 'Open navigation'}
        aria-expanded={backAction ? undefined : menuOpen} onClick={backAction || (() => setMenuOpen(!menuOpen))}
        className="w-11 h-11 shrink-0 rounded-full border border-slate-100 bg-slate-50 flex items-center justify-center text-slate-600">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d={backAction ? 'M19 12H5M12 19l-7-7 7-7' : 'M3 6h18M3 12h18M3 18h18'} /></svg>
      </button>
      <div className="text-center min-w-0"><h1 className="font-bold text-slate-900 text-[18px] md:text-[22px] tracking-tight">{title}</h1></div>
      {settingsAction ? <button type="button" onClick={settingsAction} aria-label="Tank settings" className="w-11 h-11 shrink-0 rounded-full bg-slate-50 text-xl">⚙</button> : (
        <Link to="/alerts" aria-label="Open alerts" className="relative w-11 h-11 shrink-0 rounded-full bg-slate-50 flex items-center justify-center"><img src={bellIcon} alt="" className="w-5 h-6" /><span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-cyan-400 border border-white" /></Link>
      )}
      {menuOpen && <nav aria-label="Quick navigation" className="absolute top-full left-4 right-4 md:right-auto md:w-64 rounded-2xl bg-white border border-slate-200 p-2 shadow-xl" onKeyDown={(event) => {if(event.key==='Escape'){setMenuOpen(false);menuButton.current?.focus()}}}>
        {destinations.map(([path,label]) => <Link key={path} to={path} aria-current={location.pathname===path?'page':undefined} onClick={()=>setMenuOpen(false)} className="block px-4 py-3 rounded-xl hover:bg-sky-50 text-slate-700 font-semibold">{label}</Link>)}
      </nav>}
    </header>
  )
}
