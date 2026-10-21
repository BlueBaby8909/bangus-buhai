import { lazy, Suspense, useEffect, useRef, useSyncExternalStore } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import BottomNav from './components/BottomNav.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import { LoadingState } from './components/RequestState.jsx'
import { subscribe, getRevision, getScenario, getResetKey, setScenario, resetSamples, getDataMode } from './services/dataSource.js'

const Dashboard=lazy(()=>import('./pages/Dashboard.jsx'))
const TankDetail=lazy(()=>import('./pages/TankDetail.jsx'))
const Tanks=lazy(()=>import('./pages/Tanks.jsx'))
const Alerts=lazy(()=>import('./pages/Alerts.jsx'))
const DataExport=lazy(()=>import('./pages/DataExport.jsx'))
const PreviewToolbar=import.meta.env.DEV ? lazy(()=>import('./development/PreviewToolbar.jsx').then(module=>({default:module.PreviewToolbar}))) : null

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
    <div className="app-shell bg-slate-50 min-h-screen flex flex-col md:flex-row pb-[72px] md:pb-0">
      <a className="skip-link" href="#main-content" onClick={(event)=>{event.preventDefault();mainRef.current?.focus()}}>Skip to main content</a>
      <BottomNav />
      <main id="main-content" ref={mainRef} tabIndex={-1} className="flex-1 min-w-0 w-full md:pl-[240px]">
        <div className="max-w-7xl mx-auto w-full h-full">
          <Suspense fallback={<LoadingState />}>
          {import.meta.env.DEV && getDataMode()==='sample' && new URLSearchParams(location.search).get('tools')==='1' && <PreviewToolbar scenario={scenario} onChange={setScenario}
            onReset={()=>{mainRef.current?.focus();resetSamples()}} />}
          <ErrorBoundary key={`${location.pathname}:${scenario}:${getResetKey()}`}>
          <Routes key={`${location.pathname}:${scenario}:${getResetKey()}`}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/tanks" element={<Tanks />} />
            <Route path="/tanks/:id" element={<TankDetail />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/data" element={<DataExport />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </ErrorBoundary>
          </Suspense>
        </div>
      </main>
    </div>
  )
}
