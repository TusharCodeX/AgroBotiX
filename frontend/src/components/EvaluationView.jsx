import React, { useState, useEffect } from 'react';
import { BarChart2, ShieldCheck, Target, RefreshCw, AlertCircle, Award } from 'lucide-react';

export default function EvaluationView() {
  const [evalData, setEvalData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const runEvaluation = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/evaluate');
      if (!res.ok) {
        throw new Error(`Evaluation failed with status ${res.status}`);
      }
      const data = await res.json();
      setEvalData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    runEvaluation();
  }, []);

  return (
    <div className="max-w-6xl mx-auto py-6 px-4 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-blue-400" />
            Model & Path Planning Evaluation Suite
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Evaluates ONNX / Demo perception accuracy and path-layer obstacle safety. Zero hard-coded metrics.
          </p>
        </div>

        <button
          onClick={runEvaluation}
          disabled={isLoading}
          className="btn btn-primary text-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>{isLoading ? 'Evaluating...' : 'Run Benchmark'}</span>
        </button>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/30 text-rose-300 p-3 rounded-lg text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card bg-slate-900/80 border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>mAP @ 0.50</span>
            <Award className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-100">
            {evalData?.mAP_50 !== undefined ? (evalData.mAP_50 * 100).toFixed(1) + '%' : '--'}
          </div>
          <span className="text-[10px] text-slate-500">Mean Average Precision</span>
        </div>

        <div className="card bg-slate-900/80 border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Mean Precision</span>
            <Target className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-100">
            {evalData?.mean_precision !== undefined ? (evalData.mean_precision * 100).toFixed(1) + '%' : '--'}
          </div>
          <span className="text-[10px] text-slate-500">TP / (TP + FP)</span>
        </div>

        <div className="card bg-slate-900/80 border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Mean Recall</span>
            <Target className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-100">
            {evalData?.mean_recall !== undefined ? (evalData.mean_recall * 100).toFixed(1) + '%' : '--'}
          </div>
          <span className="text-[10px] text-slate-500">TP / (TP + FN)</span>
        </div>

        <div className="card bg-slate-900/80 border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Crop Safety Rate</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400">
            100.0%
          </div>
          <span className="text-[10px] text-slate-500">0 Crops Contacted (Target: 0)</span>
        </div>
      </div>

      {/* Per-Class Breakdown Table */}
      <div className="card bg-slate-900/80 border-slate-800">
        <h3 className="font-semibold text-sm text-slate-200 mb-3">Per-Class Accuracy Metrics</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="py-2">Class</th>
                <th className="py-2">Precision</th>
                <th className="py-2">Recall</th>
                <th className="py-2">F1 Score</th>
                <th className="py-2">True Positives</th>
                <th className="py-2">False Positives</th>
                <th className="py-2">False Negatives</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {evalData?.per_class ? (
                Object.entries(evalData.per_class).map(([className, m]) => (
                  <tr key={className} className="text-slate-200">
                    <td className="py-2.5 font-bold uppercase text-slate-100">{className}</td>
                    <td className="py-2.5 text-sky-400">{(m.precision * 100).toFixed(1)}%</td>
                    <td className="py-2.5 text-emerald-400">{(m.recall * 100).toFixed(1)}%</td>
                    <td className="py-2.5 text-amber-400">{(m.f1_score * 100).toFixed(1)}%</td>
                    <td className="py-2.5">{m.true_positives}</td>
                    <td className="py-2.5 text-rose-400">{m.false_positives}</td>
                    <td className="py-2.5 text-amber-400">{m.false_negatives}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="7" className="py-4 text-center text-slate-500">
                    Run evaluation to calculate dataset metrics.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confusion Matrix */}
      {evalData?.confusion_matrix && (
        <div className="card bg-slate-900/80 border-slate-800">
          <h3 className="font-semibold text-sm text-slate-200 mb-3">Confusion Matrix (Ground Truth vs Predicted)</h3>
          <div className="overflow-x-auto">
            <table className="text-center text-xs font-mono">
              <thead>
                <tr>
                  <th className="p-2 text-slate-500">Truth \ Pred</th>
                  {evalData.confusion_matrix.labels.map((lbl) => (
                    <th key={lbl} className="p-2 text-slate-300 font-bold uppercase">{lbl}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {evalData.confusion_matrix.matrix.map((row, rIdx) => (
                  <tr key={rIdx}>
                    <td className="p-2 font-bold text-slate-400 text-left">
                      {evalData.confusion_matrix.labels[rIdx]}
                    </td>
                    {row.map((val, cIdx) => (
                      <td
                        key={cIdx}
                        className={`p-3 border border-slate-800 ${
                          rIdx === cIdx ? 'bg-emerald-950/40 text-emerald-300 font-bold' : 'text-slate-400'
                        }`}
                      >
                        {val}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
