import { Navigate, Route, Routes } from "react-router-dom";
import Start from "./pages/Start.jsx";
import Chat from "./pages/Chat.jsx";
import Login from "./pages/staff/Login.jsx";
import StaffLayout from "./pages/staff/StaffLayout.jsx";
import Leads from "./pages/staff/Leads.jsx";
import Inbox from "./pages/staff/Inbox.jsx";
import Dashboard from "./pages/staff/Dashboard.jsx";
import Review from "./pages/staff/Review.jsx";
import Admin from "./pages/staff/Admin.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Start />} />
      <Route path="/chat" element={<Chat />} />
      <Route path="/staff/login" element={<Login />} />
      <Route path="/staff" element={<StaffLayout />}>
        <Route index element={<Navigate to="leads" replace />} />
        <Route path="leads" element={<Leads />} />
        <Route path="inbox" element={<Inbox />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="review" element={<Review />} />
        <Route path="admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
