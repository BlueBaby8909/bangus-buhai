import { Routes, Route, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import TankDetail from "./pages/TankDetail";
import Tanks from "./pages/Tanks";
import Alerts from "./pages/Alerts";
import DataExport from "./pages/DataExport";
import BottomNav from "./components/BottomNav";

export default function App() {
  return (
    <div className="bg-slate-50 min-h-screen flex flex-col md:flex-row pb-[72px] md:pb-0">
      <BottomNav />
      <main className="flex-1 w-full md:pl-[240px]">
        <div className="max-w-7xl mx-auto w-full h-full">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/tanks" element={<Tanks />} />
            <Route path="/tanks/:id" element={<TankDetail />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/data" element={<DataExport />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
