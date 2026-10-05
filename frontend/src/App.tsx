import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Database, Menu, Moon, Sun } from "lucide-react";
import { api, uid } from "./api";
import type { ChatTurn, Domain, SessionGroups } from "./types";
import { Sidebar } from "./components/Sidebar";
import { ChatMessage } from "./components/ChatMessage";
import { Composer } from "./components/Composer";
import { EmptyState } from "./components/EmptyState";

const store = {
  get(key: string, fallback: string) {
    try {
      return localStorage.getItem(key) ?? fallback;
    } catch {
      return fallback;
    }
  },
  set(key: string, value: string) {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* storage unavailable */
    }
  },
};

type Theme = "light" | "dark";

export default function App() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [dataEngine, setDataEngine] = useState("");
  const [backendError, setBackendError] = useState<string | null>(null);
  const [activeModule, setActiveModule] = useState("FINANCE");
  const [sessionId, setSessionId] = useState(uid);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [sessions, setSessions] = useState<SessionGroups>({});
  const [userId, setUserId] = useState(() => store.get("opsinsight.user", "analyst@local"));
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = store.get("opsinsight.theme", "");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const domain = useMemo(() => domains.find((d) => d.module === activeModule), [domains, activeModule]);
  const busy = turns.some((t) => t.status === "pending" || t.status === "streaming");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    store.set("opsinsight.theme", theme);
  }, [theme]);

  useEffect(() => {
    api
      .modules()
      .then((res) => {
        setDomains(res.modules);
        setDataEngine(res.data_engine);
        const first = res.modules.find((m) => m.status === "active");
        if (first) setActiveModule(first.module);
        setBackendError(null);
      })
      .catch((e: Error) => setBackendError(e.message));
  }, []);

  const refreshSessions = useCallback(() => {
    if (!userId.trim()) return;
    api.sessions(userId.trim()).then(setSessions).catch(() => setSessions({}));
  }, [userId]);

  useEffect(() => {
    store.set("opsinsight.user", userId);
    const t = setTimeout(refreshSessions, 300);
    return () => clearTimeout(t);
  }, [userId, refreshSessions]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  const newChat = (module = activeModule) => {
    abortRef.current?.abort();
    setActiveModule(module);
    setSessionId(uid());
    setTurns([]);
    setSidebarOpen(false);
  };

  const send = async (question: string) => {
    if (!domain || domain.status !== "active") return;
    const turn: ChatTurn = {
      id: uid(),
      question,
      askedAt: new Date().toISOString(),
      status: "pending",
      stage: "Connecting…",
      parts: [],
    };
    setTurns((prev) => [...prev, turn]);
    const started = performance.now();
    const controller = new AbortController();
    abortRef.current = controller;

    const update = (fn: (t: ChatTurn) => ChatTurn) =>
      setTurns((prev) => prev.map((t) => (t.id === turn.id ? fn(t) : t)));

    try {
      await api.queryStream(
        {
          user_input: question,
          session_id: sessionId,
          message_id: turn.id,
          module_name: activeModule,
          request_timestamp: new Date().toISOString(),
          user_id: userId.trim() || "analyst@local",
        },
        (e) => {
          switch (e.event) {
            case "start":
              update((t) => ({ ...t, responseId: e.data.response_id }));
              break;
            case "status":
              update((t) => ({ ...t, stage: e.data.message }));
              break;
            case "delta":
              update((t) => {
                const parts = [...(t.parts ?? [])];
                const current = parts[e.data.index];
                parts[e.data.index] = {
                  type: "text",
                  content: (current?.type === "text" ? current.content : "") + e.data.text,
                };
                return { ...t, status: "streaming", parts };
              });
              break;
            case "part":
              update((t) => {
                const parts = e.data.replace_all ? [] : [...(t.parts ?? [])];
                parts[e.data.index] = e.data.part;
                return { ...t, status: "streaming", parts };
              });
              break;
            case "sql":
              update((t) => ({ ...t, sql: e.data.sql }));
              break;
            case "done":
              update((t) => ({
                ...t,
                status: "done",
                stage: undefined,
                parts: e.data.response,
                responseId: e.data.response_id,
                sql: e.data.sql ?? t.sql,
                elapsedMs: performance.now() - started,
              }));
              break;
          }
        },
        controller.signal,
      );
      // Stream closed without a "done" event (e.g. proxy cut it off)
      update((t) => (t.status === "done" ? t : { ...t, status: t.parts?.length ? "stopped" : "error", stage: undefined }));
      refreshSessions();
    } catch (err) {
      const aborted = (err as Error).name === "AbortError";
      update((t) => ({
        ...t,
        status: aborted ? "stopped" : "error",
        stage: undefined,
        elapsedMs: performance.now() - started,
      }));
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  };

  const stop = () => abortRef.current?.abort();

  const openSession = async (id: string, module: string) => {
    abortRef.current?.abort();
    setSidebarOpen(false);
    setSessionId(id);
    if (module && domains.some((d) => d.module === module)) setActiveModule(module);
    setTurns([]);
    try {
      setTurns(await api.sessionMessages(id));
    } catch {
      setTurns([]);
    }
  };

  const deleteSession = async (id: string) => {
    if (!window.confirm("Delete this conversation? This cannot be undone.")) return;
    await api.deleteSession(id).catch(() => undefined);
    if (id === sessionId) newChat();
    refreshSessions();
  };

  const like = (turn: ChatTurn, value: boolean) => {
    if (!turn.responseId) return;
    setTurns((prev) => prev.map((t) => (t.id === turn.id ? { ...t, like: value } : t)));
    api.like(sessionId, turn.responseId, value).catch(() => undefined);
  };

  const feedback = (turn: ChatTurn, text: string) => {
    if (!turn.responseId) return;
    setTurns((prev) => prev.map((t) => (t.id === turn.id ? { ...t, feedback: text } : t)));
    api.feedback(sessionId, turn.responseId, text).catch(() => undefined);
  };

  return (
    <div className="app">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        domains={domains}
        activeModule={activeModule}
        onSelectDomain={(d) => newChat(d.module)}
        sessions={sessions}
        activeSessionId={sessionId}
        onSelectSession={openSession}
        onDeleteSession={deleteSession}
        onNewChat={() => newChat()}
        userId={userId}
        onChangeUser={setUserId}
      />

      <main className="main">
        <header className="topbar">
          <button className="icon-btn mobile-only" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
            <Menu size={18} />
          </button>
          <div className="topbar-title">
            <span className="topbar-domain">{domain?.display_name ?? "OpsInsight"}</span>
            {turns.length > 0 && <span className="muted small topbar-session">{turns[0].question}</span>}
          </div>
          <div className="topbar-actions">
            {dataEngine && (
              <span className="status-pill" title="Data source the generated SQL runs against">
                <span className="status-dot" />
                <Database size={13} />
                {dataEngine === "sqlite" ? "Local SQLite" : "StarRocks"}
              </span>
            )}
            <button
              className="icon-btn"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              aria-label="Toggle theme"
              title="Toggle theme"
            >
              {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>
          </div>
        </header>

        {backendError && (
          <div className="banner">
            Can't reach the backend ({backendError}). Start it with <code>python main.py</code> in <code>app/src</code>.
          </div>
        )}

        <div className="thread" ref={scrollRef}>
          <div className="thread-inner">
            {turns.length === 0 ? (
              <EmptyState domain={domain} onPick={send} />
            ) : (
              turns.map((t) => <ChatMessage key={t.id} turn={t} onLike={like} onFeedback={feedback} />)
            )}
          </div>
        </div>

        <Composer
          busy={busy}
          onStop={stop}
          disabled={!domain || domain.status !== "active"}
          placeholder={
            domain && domain.status !== "active"
              ? `${domain.short_name} is coming soon`
              : "Ask about balances, transactions, channels, reference numbers…"
          }
          onSend={send}
        />
      </main>
    </div>
  );
}
