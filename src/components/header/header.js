import { NavLink, useNavigate } from "react-router-dom";
import axios from "axios";
import "./header.css";
import { CircleUser, Home, FileWarning, RotateCcw, LogOut } from "lucide-react";
import userManager from "../../utils/userManager";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5000";

const Header = () => {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      userManager.applyAuthHeader(axios);
      await axios.post(`${API_BASE}/api/auth/logout`, {}, { withCredentials: true });
    } catch (err) {
      // ignore logout errors
    } finally {
      userManager.clearAuth();
      navigate("/login");
    }
  };
  return (
    <header>
      <img src="logo.png" alt="LearnX" height={40} className="logo" />
      <div className="nav-actions">
        <NavLink to="/" className={"nav-icon"} title="主页">
          <Home size={32} strokeWidth={1} color="white" />
        </NavLink>
        <NavLink to="/wrong" className={"nav-icon"} title="错题集">
          <FileWarning size={30} strokeWidth={1} color="white" />
        </NavLink>
        <NavLink to="/redo" className={"nav-icon"} title="重做列表">
          <RotateCcw size={30} strokeWidth={1} color="white" />
        </NavLink>
        <NavLink to="/profile" className={"nav-icon"} title="个人中心">
          <CircleUser size={36} strokeWidth={1} color="white" />
        </NavLink>
        <button type="button" className="nav-icon" title="退出登录" onClick={handleLogout}>
          <LogOut size={30} strokeWidth={1} color="white" />
        </button>
      </div>
    </header>
  );
};

export default Header;
