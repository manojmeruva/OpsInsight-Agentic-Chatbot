import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Check, ChevronDown, ChevronRight, Code2, Copy, Download, Sparkles, ThumbsDown, ThumbsUp } from "lucide-react";
import type { ChatTurn, ResponsePart } from "../types";
import { DataTable } from "./DataTable";

function useCopy() {
  const [copied, setCopied] = useState(false);
  const copy = (text: string) => {
    navigator.clipboard?.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return { copied, copy };
}

function SqlBlock({ sql }: { sql: string }) {
  const [open, setOpen] = useState(false);
  const { copied, copy } = useCopy();
  return (
    <div className="sql-block">
      <button className="sql-toggle" onClick={() => setOpen(!open)}>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <Code2 size={14} /> Generated SQL
      </button>
      {open && (
        <div className="sql-body">
          <button className="btn-ghost sm sql-copy" onClick={() => copy(sql)}>
            {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? "Copied" : "Copy"}
          </button>
          <pre>
            <code>{sql.trim()}</code>
          </pre>
        </div>
      )}
    </div>
  );
}

function Part({ part }: { part: ResponsePart }) {
  if (part.type === "text") {
    if (!part.content?.trim()) return null;
    return (
      <div className="markdown">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{part.content}</ReactMarkdown>
      </div>
    );
  }
  if (part.type === "table") return <DataTable rows={part.content} />;
  if (part.type === "image") {
    const src = `data:${part.mime_type};base64,${part.content}`;
    return (
      <figure className="chart-card">
        <img src={src} alt="Generated chart" />
        <a className="btn-ghost sm chart-download" href={src} download="opsinsight-chart.png">
          <Download size={14} /> PNG
        </a>
      </figure>
    );
  }
  return null;
}

function plainText(parts: ResponsePart[] = []): string {
  return parts
    .map((p) => {
      if (p.type === "text") return p.content;
      if (p.type === "table" && p.content.length) {
        const cols = Object.keys(p.content[0]);
        return [cols.join("\t"), ...p.content.map((r) => cols.map((c) => String(r[c] ?? "")).join("\t"))].join("\n");
      }
      return "";
    })
    .filter(Boolean)
    .join("\n\n");
}

interface Props {
  turn: ChatTurn;
  onLike: (turn: ChatTurn, like: boolean) => void;
  onFeedback: (turn: ChatTurn, text: string) => void;
}

export function ChatMessage({ turn, onLike, onFeedback }: Props) {
  const { copied, copy } = useCopy();
  const [showFeedback, setShowFeedback] = useState(false);
  const [draft, setDraft] = useState("");

  return (
    <div className="turn">
      <div className="msg user">
        <div className="bubble">{turn.question}</div>
      </div>

      <div className="msg assistant">
        <div className="avatar">
          <Sparkles size={16} />
        </div>
        <div className="assistant-body">
          {(turn.status === "pending" || turn.status === "streaming") && (
            <>
              {turn.parts?.map((p, i) => <Part key={i} part={p} />)}
              {turn.sql && <SqlBlock sql={turn.sql} />}
              {turn.status === "streaming" && turn.parts?.length ? (
                <span className="caret" aria-hidden />
              ) : (
                <div className="thinking">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                  <span className="muted">{turn.stage ?? "Analysing your question…"}</span>
                </div>
              )}
            </>
          )}

          {turn.status === "error" && (
            <div className="error-card">Something went wrong while answering. Please try again.</div>
          )}

          {(turn.status === "done" || turn.status === "stopped") && (
            <>
              {turn.status === "stopped" && !turn.parts?.length && (
                <div className="muted small">Response stopped.</div>
              )}
              {turn.parts?.map((p, i) => <Part key={i} part={p} />)}
              {turn.sql && <SqlBlock sql={turn.sql} />}

              <div className="msg-actions">
                <button className="icon-btn" title="Copy answer" onClick={() => copy(plainText(turn.parts))}>
                  {copied ? <Check size={15} /> : <Copy size={15} />}
                </button>
                <button
                  className={`icon-btn ${turn.like === true ? "active" : ""}`}
                  title="Helpful"
                  onClick={() => onLike(turn, true)}
                  disabled={!turn.responseId}
                >
                  <ThumbsUp size={15} />
                </button>
                <button
                  className={`icon-btn ${turn.like === false ? "active neg" : ""}`}
                  title="Not helpful"
                  onClick={() => {
                    onLike(turn, false);
                    setShowFeedback(true);
                  }}
                  disabled={!turn.responseId}
                >
                  <ThumbsDown size={15} />
                </button>
                {turn.elapsedMs !== undefined && (
                  <span className="muted small">
                    {(turn.elapsedMs / 1000).toFixed(1)}s{turn.status === "stopped" ? " · stopped" : ""}
                  </span>
                )}
              </div>

              {turn.feedback && !showFeedback && <div className="feedback-note">Feedback sent: “{turn.feedback}”</div>}

              {showFeedback && (
                <form
                  className="feedback-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (draft.trim()) onFeedback(turn, draft.trim());
                    setShowFeedback(false);
                    setDraft("");
                  }}
                >
                  <input
                    autoFocus
                    placeholder="What was wrong or missing? (optional)"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                  />
                  <button className="btn-primary sm" type="submit">
                    Send
                  </button>
                  <button className="btn-ghost sm" type="button" onClick={() => setShowFeedback(false)}>
                    Cancel
                  </button>
                </form>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
