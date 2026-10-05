import { useEffect, useRef, useState } from "react";
import { ArrowUp, Check, Loader2, Mic, ShieldCheck, Square, X } from "lucide-react";
import { api } from "../api";
import { isRecordingSupported, startRecording, type Recorder } from "../recorder";

const MAX_RECORDING_SECONDS = 60;

type VoiceState = "idle" | "starting" | "recording" | "transcribing";

interface Props {
  disabled: boolean;
  busy: boolean;
  onStop: () => void;
  placeholder: string;
  onSend: (text: string) => void;
}

function formatClock(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export function Composer({ disabled, busy, onStop, placeholder, onSend }: Props) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  const [voice, setVoice] = useState<VoiceState>("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [level, setLevel] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const recorderRef = useRef<Recorder | null>(null);
  const voiceSupported = isRecordingSupported();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [text]);

  // Recording timer + auto-stop
  useEffect(() => {
    if (voice !== "recording") return;
    const started = Date.now();
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 250);
    return () => clearInterval(t);
  }, [voice]);

  useEffect(() => {
    if (voice === "recording" && elapsed >= MAX_RECORDING_SECONDS) void finishRecording();
  }, [elapsed, voice]);

  // Release the microphone if the component unmounts mid-recording
  useEffect(() => () => recorderRef.current?.cancel(), []);

  const submit = () => {
    const value = text.trim();
    if (!value || disabled || busy || voice !== "idle") return;
    onSend(value);
    setText("");
  };

  const beginRecording = async () => {
    setVoiceError(null);
    setVoice("starting");
    try {
      recorderRef.current = await startRecording(setLevel);
      setElapsed(0);
      setVoice("recording");
    } catch (err) {
      const name = (err as DOMException).name;
      setVoiceError(
        name === "NotAllowedError"
          ? "Microphone access was blocked. Allow it in your browser's site settings."
          : name === "NotFoundError"
            ? "No microphone was found."
            : "Couldn't start recording.",
      );
      setVoice("idle");
    }
  };

  async function finishRecording() {
    const recorder = recorderRef.current;
    recorderRef.current = null;
    if (!recorder) return;
    setVoice("transcribing");
    setLevel(0);
    try {
      const wav = await recorder.stop();
      const transcript = await api.speechToText(wav);
      if (transcript) {
        setText((prev) => (prev.trim() ? `${prev.trimEnd()} ${transcript}` : transcript));
        requestAnimationFrame(() => ref.current?.focus());
      } else {
        setVoiceError("No speech was detected. Try again a little closer to the mic.");
      }
    } catch {
      setVoiceError("Transcription failed. Please try again or type your question.");
    } finally {
      setVoice("idle");
    }
  }

  const cancelRecording = () => {
    recorderRef.current?.cancel();
    recorderRef.current = null;
    setLevel(0);
    setVoice("idle");
  };

  const recording = voice === "recording";

  return (
    <div className="composer-wrap">
      <div className={`composer ${recording ? "recording" : ""}`}>
        {recording ? (
          <div className="voice-bar" role="status" aria-live="polite">
            <span className="rec-dot" />
            <span className="voice-time">{formatClock(elapsed)}</span>
            <div className="voice-meter" aria-hidden>
              {Array.from({ length: 24 }, (_, i) => (
                <span key={i} style={{ transform: `scaleY(${0.15 + level * (0.6 + 0.4 * Math.sin(i * 1.7 + elapsed))})` }} />
              ))}
            </div>
            <span className="muted small voice-hint">Listening… English or Arabic</span>
          </div>
        ) : (
          <textarea
            ref={ref}
            rows={1}
            value={text}
            disabled={disabled || voice === "transcribing"}
            placeholder={voice === "transcribing" ? "Transcribing…" : placeholder}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                submit();
              }
            }}
          />
        )}

        {recording ? (
          <>
            <button className="icon-btn" onClick={cancelRecording} aria-label="Cancel recording" title="Cancel">
              <X size={18} />
            </button>
            <button className="send-btn" onClick={() => void finishRecording()} aria-label="Finish recording" title="Done">
              <Check size={18} />
            </button>
          </>
        ) : (
          <>
            {voiceSupported && (
              <button
                className="icon-btn mic-btn"
                onClick={() => void beginRecording()}
                disabled={disabled || busy || voice !== "idle"}
                aria-label="Voice input"
                title="Voice input"
              >
                {voice === "transcribing" || voice === "starting" ? (
                  <Loader2 size={18} className="spin" />
                ) : (
                  <Mic size={18} />
                )}
              </button>
            )}
            {busy ? (
              <button className="send-btn stop" onClick={onStop} aria-label="Stop generating" title="Stop generating">
                <Square size={14} fill="currentColor" />
              </button>
            ) : (
              <button
                className="send-btn"
                onClick={submit}
                disabled={disabled || !text.trim() || voice !== "idle"}
                aria-label="Send"
              >
                <ArrowUp size={18} />
              </button>
            )}
          </>
        )}
      </div>
      {voiceError ? (
        <div className="composer-hint error" role="alert">
          {voiceError}
          <button className="link-btn" onClick={() => setVoiceError(null)}>
            Dismiss
          </button>
        </div>
      ) : (
        <div className="composer-hint">
          <ShieldCheck size={13} />
          Account numbers are masked and UTRs are never shown. AI-generated answers — verify before acting.
        </div>
      )}
    </div>
  );
}
