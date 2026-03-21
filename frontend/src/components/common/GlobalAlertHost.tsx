import { useEffect, useRef, useState } from "react";
import { CustomAlert } from "./CustomAlert";

type AlertItem = {
  id: number;
  message: string;
};

export const GlobalAlertHost = () => {
  const queueRef = useRef<AlertItem[]>([]);
  const originalAlertRef = useRef<typeof window.alert | null>(null);
  const [currentAlert, setCurrentAlert] = useState<AlertItem | null>(null);

  useEffect(() => {
    originalAlertRef.current = window.alert.bind(window);

    const openNextAlert = () => {
      setCurrentAlert((prev) => {
        if (prev) return prev;
        const next = queueRef.current.shift() ?? null;
        return next;
      });
    };

    window.alert = (message?: string) => {
      queueRef.current.push({
        id: Date.now() + Math.floor(Math.random() * 1000),
        message: String(message ?? ""),
      });
      openNextAlert();
    };

    return () => {
      if (originalAlertRef.current) {
        window.alert = originalAlertRef.current;
      }
    };
  }, []);

  const closeAlert = () => {
    setCurrentAlert(null);
    window.setTimeout(() => {
      const next = queueRef.current.shift() ?? null;
      setCurrentAlert(next);
    }, 0);
  };

  return (
    <CustomAlert
      open={Boolean(currentAlert)}
      title="알림"
      message={currentAlert?.message || ""}
      confirmText="확인"
      cancelText={null}
      onConfirm={closeAlert}
      onCancel={closeAlert}
    />
  );
};
