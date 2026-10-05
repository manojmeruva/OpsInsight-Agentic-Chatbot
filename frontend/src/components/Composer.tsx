import { useEffect, useRef, useState } from "react";
import { ArrowUp, ShieldCheck, Square } from "lucide-react";

interface Props {
  disabled: boolean;
  busy: boolean;
  onStop: () => void;
  placeholder: string;
  onSend: (text: string) => void;
}

export function Composer({ disabled, busy, onStop, placeholder, onSend }: Props) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [text]);

  const submit = () => {
    const value = text.trim();
    if (!value || disabled || busy) return;
    onSend(value);
    setText("");
  };

  return (
    <div className="composer-wrap">
      <div className="composer">
        <textarea
          ref={ref}
          rows={1}
          value={text}
          disabled={disabled}
          placeholder={placeholder}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
        />
        {busy ? (
          <button className="send-btn stop" onClick={onStop} aria-label="Stop generating" title="Stop generating">
            <Square size={14} fill="currentColor" />
          </button>
        ) : (
          <button className="send-btn" onClick={submit} disabled={disabled || !text.trim()} aria-label="Send">
            <ArrowUp size={18} />
          </button>
        )}
      </div>
      <div className="composer-hint">
        <ShieldCheck size={13} />
        Account numbers are masked and UTRs are never shown. AI-generated answers — verify before acting.
      </div>
    </div>
  );
}
