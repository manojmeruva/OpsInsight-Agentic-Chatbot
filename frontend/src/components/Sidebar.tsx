import { Landmark, LineChart, MessageSquare, Plus, ShoppingCart, Trash2, Users, X, type LucideIcon } from "lucide-react";
import type { Domain, SessionGroups } from "../types";

const ICONS: Record<string, LucideIcon> = {
  landmark: Landmark,
  "shopping-cart": ShoppingCart,
  users: Users,
};

export function DomainIcon({ name, size = 16 }: { name: string; size?: number }) {
  const Icon = ICONS[name] ?? LineChart;
  return <Icon size={size} />;
}

interface Props {
  open: boolean;
  onClose: () => void;
  domains: Domain[];
  activeModule: string;
  onSelectDomain: (d: Domain) => void;
  sessions: SessionGroups;
  activeSessionId: string;
  onSelectSession: (sessionId: string, module: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onNewChat: () => void;
  userId: string;
  onChangeUser: (id: string) => void;
}

export function Sidebar(p: Props) {
  const groups = Object.entries(p.sessions).filter(([, list]) => list.length);

  return (
    <>
      <div className={`scrim ${p.open ? "show" : ""}`} onClick={p.onClose} />
      <aside className={`sidebar ${p.open ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <LineChart size={18} />
          </div>
          <div>
            <div className="brand-name">OpsInsight</div>
            <div className="brand-sub">Agentic analytics</div>
          </div>
          <button className="icon-btn mobile-only" onClick={p.onClose} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>

        <button className="btn-primary new-chat" onClick={p.onNewChat}>
          <Plus size={16} /> New analysis
        </button>

        <div className="side-section">
          <div className="side-label">Domains</div>
          {p.domains.map((d) => {
            const disabled = d.status !== "active";
            return (
              <button
                key={d.module}
                className={`side-item ${p.activeModule === d.module ? "active" : ""}`}
                onClick={() => !disabled && p.onSelectDomain(d)}
                disabled={disabled}
                title={disabled ? `${d.short_name} — coming soon` : d.description}
              >
                <DomainIcon name={d.icon} />
                <span className="side-item-text">{d.short_name}</span>
                {disabled && <span className="badge">Soon</span>}
              </button>
            );
          })}
        </div>

        <div className="side-section grow">
          <div className="side-label">History</div>
          {groups.length === 0 && <div className="side-empty">No conversations yet</div>}
          {groups.map(([label, list]) => (
            <div key={label} className="history-group">
              <div className="history-label">{label}</div>
              {list.map((s) => (
                <div
                  key={s.sessionId}
                  className={`side-item history ${p.activeSessionId === s.sessionId ? "active" : ""}`}
                  onClick={() => p.onSelectSession(s.sessionId, s.module_name)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && p.onSelectSession(s.sessionId, s.module_name)}
                >
                  <MessageSquare size={14} />
                  <span className="side-item-text" title={s.sessionName}>
                    {s.sessionName || "Untitled"}
                  </span>
                  <button
                    className="icon-btn xs delete"
                    title="Delete conversation"
                    onClick={(e) => {
                      e.stopPropagation();
                      p.onDeleteSession(s.sessionId);
                    }}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          ))}
        </div>

        <div className="user-box">
          <div className="user-avatar">{(p.userId[0] ?? "U").toUpperCase()}</div>
          <input
            className="user-input"
            value={p.userId}
            onChange={(e) => p.onChangeUser(e.target.value)}
            aria-label="User email"
            spellCheck={false}
          />
        </div>
      </aside>
    </>
  );
}
