import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "../pages/Home";
import Login from "../pages/Login/Login";
import Register from "../pages/Register";
import StartupView from "../pages/StartupView";
import InvestorDashboard from "../pages/InvestorDashboard";
import Inbox from "../pages/Inbox";
import PasswordResetRequest from "../pages/PasswordReset/PasswordResetRequest";
import PasswordResetConfirm from "../pages/PasswordReset/PasswordResetConfirm";

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/startups/:id" element={<StartupView />} />
        <Route path="/dashboard" element={<InvestorDashboard />} />
        <Route path="/messages" element={<Inbox />} />
        <Route path="/password-reset" element={<PasswordResetRequest />} />
        <Route path="/reset-password" element={<PasswordResetConfirm />} />
      </Routes>
    </BrowserRouter>
  );
}
