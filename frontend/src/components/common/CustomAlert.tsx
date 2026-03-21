import { createPortal } from "react-dom";
import { AlertCircle } from "lucide-react";
import "./CustomAlert.scss";

interface CustomAlertProps {
  open: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

export const CustomAlert = ({
  open,
  title,
  message,
  confirmText = "로그인하러 가기",
  cancelText = "닫기",
  onConfirm,
  onCancel,
}: CustomAlertProps) => {
  if (!open) return null;

  return createPortal(
    <div className="custom-alert-overlay" onClick={onCancel}>
      <div
        className="custom-alert-card"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="custom-alert-icon">
          <AlertCircle size={22} />
        </div>
        <h3>{title}</h3>
        <p>{message}</p>

        <div className="custom-alert-actions">
          {cancelText !== null && (
            <button className="secondary-btn" onClick={onCancel}>
              {cancelText}
            </button>
          )}
          <button className="primary-btn" onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
};
