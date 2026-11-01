import type { ButtonHTMLAttributes, ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";

export function Button({
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className="button" {...props}>
      {children}
    </button>
  );
}

export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`panel ${className}`}>{children}</section>;
}

export function HealthBar({
  name,
  value,
  max = 100,
}: {
  name: string;
  value: number;
  max?: number;
}) {
  const health = Math.max(0, Math.min(value, max));
  return (
    <div className="health">
      <div>
        <strong>{name}</strong>
        <span>
          {health} / {max} HP
        </span>
      </div>
      <progress aria-label={`${name} health`} max={max} value={health} />
    </div>
  );
}

export function PetAvatar({
  name,
  rival = false,
}: {
  name: string;
  rival?: boolean;
}) {
  const reduceMotion = useReducedMotion();
  return (
    <motion.div
      className={`pet ${rival ? "rival" : ""}`}
      role="img"
      aria-label={`${name}, placeholder pet`}
      animate={{ y: reduceMotion ? 0 : [0, -10, 0] }}
      transition={{ repeat: Infinity, duration: 2.5 }}
    >
      <span className="ears" />
      <span className="eyes">• •</span>
      <span className="mouth">⌣</span>
    </motion.div>
  );
}

export function SkillCard({
  name,
  symbol,
  selected,
  onClick,
}: {
  name: string;
  symbol: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`skill ${selected ? "selected" : ""}`}
      aria-pressed={selected}
      onClick={onClick}
    >
      <span>{symbol}</span>
      {name}
    </button>
  );
}
