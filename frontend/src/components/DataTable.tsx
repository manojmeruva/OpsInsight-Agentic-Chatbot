import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, Download } from "lucide-react";

type Row = Record<string, unknown>;

const MONEY_HINT = /(inr|amount|balance|credit|debit|flow|₹)/i;
const inr = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const num = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });

function isNumeric(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function formatCell(col: string, v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (isNumeric(v)) return MONEY_HINT.test(col) ? inr.format(v) : num.format(v);
  return String(v);
}

function toCsv(columns: string[], rows: Row[]): string {
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [columns.map(esc).join(","), ...rows.map((r) => columns.map((c) => esc(r[c])).join(","))].join("\n");
}

export function DataTable({ rows }: { rows: Row[] }) {
  const columns = useMemo(() => (rows.length ? Object.keys(rows[0]) : []), [rows]);
  const numericCols = useMemo(
    () => new Set(columns.filter((c) => rows.every((r) => r[c] == null || isNumeric(r[c])))),
    [columns, rows],
  );
  const [sort, setSort] = useState<{ col: string; dir: 1 | -1 } | null>(null);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const { col, dir } = sort;
    return [...rows].sort((a, b) => {
      const x = a[col], y = b[col];
      if (x == null) return 1;
      if (y == null) return -1;
      if (isNumeric(x) && isNumeric(y)) return (x - y) * dir;
      return String(x).localeCompare(String(y)) * dir;
    });
  }, [rows, sort]);

  const download = () => {
    const blob = new Blob([toCsv(columns, sorted)], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `opsinsight-export-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  if (!rows.length) return null;

  return (
    <div className="table-card">
      <div className="table-toolbar">
        <span className="muted">
          {rows.length} row{rows.length === 1 ? "" : "s"} · {columns.length} column{columns.length === 1 ? "" : "s"}
        </span>
        <button className="btn-ghost sm" onClick={download} title="Download CSV">
          <Download size={14} /> CSV
        </button>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {columns.map((c) => {
                const active = sort?.col === c;
                const Icon = active ? (sort!.dir === 1 ? ArrowUp : ArrowDown) : ArrowUpDown;
                return (
                  <th
                    key={c}
                    className={numericCols.has(c) ? "num" : ""}
                    onClick={() => setSort(active && sort!.dir === -1 ? null : { col: c, dir: active ? -1 : 1 })}
                  >
                    <span className="th-inner">
                      {c}
                      <Icon size={12} className={active ? "" : "faint"} />
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => (
              <tr key={i}>
                {columns.map((c) => {
                  const v = r[c];
                  const neg = isNumeric(v) && v < 0;
                  return (
                    <td key={c} className={`${numericCols.has(c) ? "num" : ""} ${neg ? "neg" : ""}`}>
                      {formatCell(c, v)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
