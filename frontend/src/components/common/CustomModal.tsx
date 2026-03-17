import React from 'react';
import './CustomModal.scss';

interface Props {
  title: string;
  message: React.ReactNode;
  onCancel: () => void;
  onConfirm: () => void;
}

export const CustomModal = ({ title, message, onCancel, onConfirm }: Props) => {
  return (
    <div className="custom-modal-overlay">
      <div className="custom-modal-content">
        <h3>{title}</h3>
        <div className="modal-message">{message}</div>
        
        <div className="modal-actions">
          <button className="btn-cancel" onClick={onCancel}>취소</button>
          <button className="btn-confirm" onClick={onConfirm}>확인</button>
        </div>
      </div>
    </div>
  );
};