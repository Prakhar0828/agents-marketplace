import { Download, BarChart3 } from "lucide-react";

interface Props {
  title: string;
  columns: string[];
  rows: string[][];
  csvUrl: string | null;
}

export function MediaTable({ title, columns, rows, csvUrl }: Props) {
  return (
    <div className="rounded-2xl border border-neon-violet/20 bg-elevated/60 p-5 shadow-bloom-violet backdrop-blur-sm">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-neon-violet">
            <BarChart3 className="h-3.5 w-3.5" />
            Content Research
          </div>
          <h3 className="mt-2 font-display text-lg font-semibold">
            {title}
          </h3>
          <p className="mt-0.5 text-xs text-muted">
            {rows.length} row{rows.length !== 1 ? "s" : ""}
          </p>
        </div>
        {csvUrl && (
          <a href={csvUrl} download className="btn-ghost shrink-0">
            <Download className="h-4 w-4" />
            CSV
          </a>
        )}
      </div>

      <div className="overflow-x-auto rounded-xl ring-1 ring-white/5">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-base/80">
              {columns.map((col) => (
                <th
                  key={col}
                  className="whitespace-nowrap px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {rows.map((row, i) => (
              <tr
                key={i}
                className="transition-colors hover:bg-white/[0.03]"
              >
                {row.map((cell, j) => (
                  <td
                    key={j}
                    className="max-w-[260px] truncate px-3 py-2.5 text-offwhite/85"
                    title={cell}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
