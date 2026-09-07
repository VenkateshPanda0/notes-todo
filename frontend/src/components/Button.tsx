import type { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
}

const variantClasses: Record<string, string> = {
  primary:
    "bg-primary text-white hover:bg-primary-hover disabled:opacity-50",
  secondary:
    "bg-transparent border border-[var(--border)] text-[var(--text)] hover:bg-[var(--border)]/40",
  danger: "bg-red-50 text-danger hover:bg-red-100 dark:bg-red-950 dark:hover:bg-red-900",
  ghost: "bg-transparent text-[var(--text-secondary)] hover:bg-[var(--border)]/40",
};

export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
