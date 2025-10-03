import { AlertCircle, X } from "lucide-react";
import { Button } from "./button";

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "warning" | "info";
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmText = "Confirmar",
  cancelText = "Cancelar",
  variant = "warning",
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  const variantStyles = {
    danger: "text-red-600 bg-red-50 border-red-200",
    warning: "text-amber-600 bg-amber-50 border-amber-200",
    info: "text-blue-600 bg-blue-50 border-blue-200",
  };

  const buttonStyles = {
    danger: "bg-red-600 hover:bg-red-700",
    warning: "bg-amber-600 hover:bg-amber-700",
    info: "bg-blue-600 hover:bg-blue-700",
  };

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 animate-in zoom-in-95 duration-200">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-lg hover:bg-slate-100 transition-colors"
        >
          <X className="w-4 h-4 text-slate-500" />
        </button>

        {/* Content */}
        <div className="p-6">
          {/* Icon */}
          <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-4 ${variantStyles[variant]}`}>
            <AlertCircle className="w-6 h-6" />
          </div>

          {/* Title */}
          <h3 className="text-xl font-bold text-slate-900 mb-2">{title}</h3>

          {/* Description */}
          <p className="text-slate-600 leading-relaxed mb-6">{description}</p>

          {/* Actions */}
          <div className="flex gap-3">
            <Button
              onClick={onClose}
              className="flex-1 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-xl h-11"
            >
              {cancelText}
            </Button>
            <Button
              onClick={handleConfirm}
              className={`flex-1 text-white rounded-xl h-11 ${buttonStyles[variant]}`}
            >
              {confirmText}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
