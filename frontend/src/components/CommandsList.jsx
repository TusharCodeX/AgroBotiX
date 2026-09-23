import React, { useState } from 'react';
import { 
  Copy, 
  Download, 
  Check, 
  ArrowUp, 
  RotateCcw, 
  RotateCw, 
  Scissors, 
  PauseCircle, 
  AlertCircle,
  FileSpreadsheet,
  FileCode
} from 'lucide-react';

export default function CommandsList({ plan }) {
  const [copied, setCopied] = useState(false);

  if (!plan || !plan.commands || plan.commands.length === 0) {
    return (
      <div className="card text-center py-10 text-slate-400">
        <p className="text-sm">No path planned yet.</p>
        <p className="text-xs text-slate-500 mt-1">Capture or upload an image and click "Plan Path".</p>
      </div>
    );
  }

  const handleCopy = () => {
    const text = plan.commands.map((c) => `[Step ${c.step}] ${c.action_text}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportJSON = () => {
    const blob = new Blob([JSON.stringify(plan, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agripath_mission_${Date.now()}.json`;
    a.click();
  };

  const handleExportCSV = () => {
    const lines = ["Step,Command,Value,Unit,Weed_ID,Description"];
    plan.commands.forEach((c) => {
      lines.push(`${c.step},${c.cmd_type},${c.value},${c.unit},${c.target_weed_id || ""},"${c.action_text}"`);
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agripath_commands_${Date.now()}.csv`;
    a.click();
  };

  const getCommandIcon = (cmdType) => {
    switch (cmdType) {
      case 'FORWARD':
        return <ArrowUp className="w-4 h-4 text-emerald-400" />;
      case 'TURN_LEFT':
        return <RotateCcw className="w-4 h-4 text-blue-400" />;
      case 'TURN_RIGHT':
        return <RotateCw className="w-4 h-4 text-blue-400" />;
      case 'BLADE_DOWN':
      case 'BLADE_ON':
      case 'BLADE_OFF':
      case 'BLADE_UP':
        return <Scissors className="w-4 h-4 text-amber-400" />;
      case 'STOP':
        return <PauseCircle className="w-4 h-4 text-slate-400" />;
      default:
        return <ArrowUp className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Header & Export Actions */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-sm text-slate-200">Rover Command Queue</h3>
          <span className="badge bg-blue-500/20 text-blue-400 border border-blue-500/30">
            {plan.commands.length} Steps
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleCopy}
            title="Copy command list"
            className="btn btn-secondary text-xs py-1 px-2"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          <button
            onClick={handleExportJSON}
            title="Export full JSON mission"
            className="btn btn-secondary text-xs py-1 px-2"
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>JSON</span>
          </button>

          <button
            onClick={handleExportCSV}
            title="Export CSV commands"
            className="btn btn-secondary text-xs py-1 px-2"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>CSV</span>
          </button>
        </div>
      </div>

      {/* Skipped Weeds Alert Banner */}
      {plan.skipped_weeds && plan.skipped_weeds.length > 0 && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-2.5 text-xs text-rose-300 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">{plan.skipped_weeds.length} Weed(s) Skipped for Safety:</span>
            <ul className="list-disc list-inside mt-1 space-y-0.5 text-rose-200">
              {plan.skipped_weeds.map((s, i) => (
                <li key={i}>Weed #{s.weed_id}: {s.reason}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Scrollable Command Step Cards */}
      <div className="max-h-[380px] overflow-y-auto space-y-1.5 pr-1 font-mono text-xs">
        {plan.commands.map((cmd) => (
          <div
            key={cmd.step}
            className={`p-2 rounded border flex items-center justify-between gap-2 transition ${
              cmd.cmd_type.startsWith('BLADE')
                ? 'bg-amber-950/20 border-amber-800/40 text-amber-200'
                : 'bg-slate-900/60 border-slate-800 text-slate-300'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <span className="text-slate-500 font-semibold w-6 text-right">#{cmd.step}</span>
              <div className="p-1 rounded bg-slate-800 border border-slate-700">
                {getCommandIcon(cmd.cmd_type)}
              </div>
              <div>
                <div className="font-semibold text-slate-100">{cmd.action_text}</div>
                {cmd.target_weed_id && (
                  <span className="text-[10px] text-rose-400 font-sans">
                    Target: Weed #{cmd.target_weed_id}
                  </span>
                )}
              </div>
            </div>

            <div className="text-right shrink-0">
              <span className="text-[11px] font-bold px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400">
                {cmd.cmd_type} {cmd.value > 0 ? `${cmd.value}${cmd.unit}` : ''}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
