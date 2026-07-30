import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import TankDetail from "./pages/TankDetail";
import Users from "./pages/Users";

export default function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tanks/:id" element={<TankDetail />} />
          <Route path="/users" element={<Users />} />
        </Routes>
      </main>
    </div>
  );
}
