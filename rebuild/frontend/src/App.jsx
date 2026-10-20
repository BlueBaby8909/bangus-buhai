import { lazy, Suspense, useEffect, useRef, useSyncExternalStore } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import BottomNav from './original/components/BottomNav.jsx'
import { PreviewToolbar } from './components/PreviewToolbar.jsx'
import { subscribe, getRevision, getScenario, getResetKey, setScenario, resetSamples, getDataMode } from './services/dataSource.js'

const Dashboard=lazy(()=>import('./original/pages/Dashboard.jsx'))
const TankDetail=lazy(()=>import('./original/pages/TankDetail.jsx'))
const Tanks=lazy(()=>import('./original/pages/Tanks.jsx'))
const Alerts=lazy(()=>import('./original/pages/Alerts.jsx'))
const DataExport=lazy(()=>import('./original/pages/DataExport.jsx'))

export default function App() {
  useSyncExternalStore(subscribe,getRevision)
  const scenario=getScenario()
  const location=useLocation()
  const mainRef=useRef(null)
  const lastPath=useRef(location.pathname)
  useEffect(()=>{
    if(lastPath.current!==location.pathname){
      mainRef.current?.focus({preventScroll:true})
      window.scrollTo({top:0,left:0,behavior:'instant'})
      lastPath.current=location.pathname
    }
  },[location.pathname])
  return (
    <div className="original-preview bg-slate-50 min-h-screen flex flex-col md:flex-row pb-[72px] md:pb-0">
      <a className="skip-link" href="#main-content" onClick={(event)=>{event.preventDefault();mainRef.current?.focus()}}>Skip to main content</a>
      <BottomNav />
      <main id="main-content" ref={mainRef} tabIndex={-1} className="flex-1 min-w-0 w-full md:pl-[240px]">
        <div className="max-w-7xl mx-auto w-full h-full">
          {getDataMode()==='sample' && new URLSearchParams(location.search).get('tools')==='1' && <PreviewToolbar scenario={scenario} onChange={setScenario}
            onReset={()=>{mainRef.current?.focus();resetSamples()}} />}
          <Suspense fallback={<p role="status" className="p-10 text-slate-600">Loading…</p>}>
          <Routes key={`${scenario}:${getResetKey()}`}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/tanks" element={<Tanks />} />
            <Route path="/tanks/:id" element={<TankDetail />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/data" element={<DataExport />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </Suspense>
        </div>
      </main>
    </div>
  )
}
