import { X } from "lucide-react";
import "./modal.css";
import { useEffect, useState } from "react";
const Modal = ({ children, open = false, onClose, simple = false }) => {
  if (simple) {
    return (
      <div className="flexbox modal" style={{ display: open ? "flex" : "none" }} onClick={onClose}>
        <div onClick={(e) => e.stopPropagation()}>
          {children}
        </div>
      </div>
    );
  }

  return (
    <div className="flexbox modal" style={{ display: open ? "flex" : "none" }}>
      <div className="modal-content">
        <button className="cross" onClick={onClose}>
          <X size={30} strokeWidth={1} color="white"></X>
        </button>
        {children}
      </div>
    </div>
  );
};

export default Modal;
