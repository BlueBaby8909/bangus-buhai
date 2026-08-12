import { Routes, Route, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import TankDetail from "./pages/TankDetail";
import Tanks from "./pages/Tanks";
import Alerts from "./pages/Alerts";
import BottomNav from "./components/BottomNav";

export default function App() {
  return (
    <div className="bg-[#f8f9fa] min-h-screen relative pb-[70px]">
      <main className="w-full">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tanks" element={<Tanks />} />
          <Route path="/tanks/:id" element={<TankDetail />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <BottomNav />
    </div>
  );
}
