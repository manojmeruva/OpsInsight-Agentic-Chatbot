import { BarChart3, BookOpen, Search, Table2 } from "lucide-react";
import type { Domain } from "../types";
import { DomainIcon } from "./Sidebar";

const CAPABILITIES = [
  { icon: Table2, label: "Tables you can sort & export" },
  { icon: BarChart3, label: "Charts on demand" },
  { icon: Search, label: "Reference-number lookups" },
  { icon: BookOpen, label: "Glossary & policy answers" },
];

export function EmptyState({ domain, onPick }: { domain?: Domain; onPick: (q: string) => void }) {
  if (!domain) return null;
  const comingSoon = domain.status !== "active";

  return (
    <div className="empty">
      <div className="empty-icon">
        <DomainIcon name={domain.icon} size={26} />
      </div>
      <h1>{domain.display_name}</h1>
      <p className="muted">{domain.description}</p>

      {comingSoon ? (
        <div className="notice">This domain is a placeholder and isn't connected to data yet.</div>
      ) : (
        <>
          <div className="capabilities">
            {CAPABILITIES.map(({ icon: Icon, label }) => (
              <span key={label} className="chip">
                <Icon size={13} /> {label}
              </span>
            ))}
          </div>
          <div className="suggestions">
            {domain.sample_questions.map((q) => (
              <button key={q} className="suggestion" onClick={() => onPick(q)}>
                {q}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
