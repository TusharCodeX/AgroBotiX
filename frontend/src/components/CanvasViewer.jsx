import React, { useRef, useEffect, useState } from 'react';
import { Layers, Eye, EyeOff, Flag, Crosshair, ShieldAlert, Sparkles, CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react';

export default function CanvasViewer({
  imageSrc,
  detections = [],
  plan = null,
  simPose = null,
  calibratingTwoPoint = false,
  onTwoPointClick = null,
  onWrongDetection = null,
  calibrator = null,
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  // Layer Visibility Toggles
  const [layers, setLayers] = useState({
    crops: true,
    weeds: true,
    uncertain: true,
    rejected: false,
    safetyBuffers: true,
    path: true,
    waypoints: true,
    footprint: true,
    bladeZone: true,
  });

  const [selectedPlant, setSelectedPlant] = useState(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (!imageSrc) {
      canvas.width = 800;
      canvas.height = 500;
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#475569';
      ctx.font = '16px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Capture or upload Indian crop field image to begin', canvas.width / 2, canvas.height / 2);
      return;
    }

    const img = new Image();
    img.src = imageSrc;
    img.onload = () => {
      canvas.width = img.naturalWidth || 800;
      canvas.height = img.naturalHeight || 600;
      const w = canvas.width;
      const h = canvas.height;

      // 1. Draw original field image
      ctx.drawImage(img, 0, 0, w, h);

      const cmScale = calibrator?.cm_per_pixel || 0.15;

      // Helper for converting cm to canvas pixel
      const cmToPx = (xCm, yCm) => {
        const frontY = (calibrator?.robot_length_cm || 30.0) / 2 + (calibrator?.ground_y_offset_cm || 10.0);
        const px = (xCm / cmScale) + w / 2;
        const py = h - ((yCm - frontY) / cmScale);
        return [px, py];
      };

      // 2. Draw Crop Safety Buffers (Dashed Circles around Crops)
      if (layers.safetyBuffers) {
        detections.forEach((det) => {
          if (det.status === 'CROP') {
            const [cx, cy] = det.center_px;
            const [x1, y1, x2, y2] = det.bbox_px;
            const plantRadiusPx = Math.max(x2 - x1, y2 - y1) / 2.0;
            // Default 5cm buffer in pixels: 5.0 / cmScale
            const bufferPx = plantRadiusPx + (5.0 / cmScale);

            ctx.save();
            ctx.beginPath();
            ctx.arc(cx, cy, bufferPx, 0, Math.PI * 2);
            ctx.setLineDash([6, 6]);
            ctx.strokeStyle = 'rgba(234, 179, 8, 0.45)'; // Amber warning boundary
            ctx.lineWidth = 2;
            ctx.fillStyle = 'rgba(234, 179, 8, 0.05)';
            ctx.fill();
            ctx.stroke();
            ctx.restore();
          }
        });
      }

      // 3. Draw Bounding Boxes and Status Overlays
      detections.forEach((det) => {
        const [x1, y1, x2, y2] = det.bbox_px;
        const [cx, cy] = det.center_px;
        const bw = x2 - x1;
        const bh = y2 - y1;

        const isActionableWeed = det.status === 'ACTIONABLE_WEED' || (det.status === 'WEED' && det.is_target);
        const isCrop = det.status === 'CROP';
        const isUncertain = det.status === 'UNCERTAIN';
        const isRejected = det.status === 'REJECTED';

        if (isCrop && !layers.crops) return;
        if (isActionableWeed && !layers.weeds) return;
        if (isUncertain && !layers.uncertain) return;
        if (isRejected && !layers.rejected) return;

        let color = '#22c55e'; // Green for Crop
        let label = `CROP #${det.id}`;
        let tag = 'PROTECT';

        if (isActionableWeed) {
          color = '#ef4444'; // Red for Actionable Weed
          label = `WEED #${det.id}`;
          tag = 'TARGET';
        } else if (isUncertain) {
          color = '#eab308'; // Yellow for Uncertain / Safety Buffer
          label = `UNCERTAIN #${det.id}`;
          tag = 'DO NOT CUT';
        } else if (isRejected) {
          color = '#94a3b8'; // Gray for Soil/Stone/Shadow
          label = `REJECTED #${det.id}`;
          tag = 'SOIL/REJECT';
        }

        const isSelected = selectedPlant && selectedPlant.id === det.id;

        // Bounding box fill and stroke
        ctx.lineWidth = isSelected ? 3.5 : 2.0;
        ctx.strokeStyle = color;
        ctx.fillStyle = color + (isSelected ? '44' : '22');
        ctx.fillRect(x1, y1, bw, bh);
        ctx.strokeRect(x1, y1, bw, bh);

        // Center crosshair / dot
        ctx.beginPath();
        ctx.arc(cx, cy, 4.5, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Label pill at top
        ctx.font = 'bold 11px JetBrains Mono, monospace';
        const text = `${label} (${(det.confidence * 100).toFixed(0)}%)`;
        const textWidth = ctx.measureText(text).width;

        ctx.fillStyle = color;
        ctx.fillRect(x1, Math.max(0, y1 - 20), textWidth + 10, 20);
        ctx.fillStyle = '#000000';
        ctx.fillText(text, x1 + 5, Math.max(14, y1 - 5));

        // Draw distance line from weed to nearest crop
        if (det.dist_to_nearest_crop_cm !== null && det.dist_to_nearest_crop_cm !== undefined && det.dist_to_nearest_crop_cm < 15.0) {
          ctx.font = '9px monospace';
          ctx.fillStyle = color;
          ctx.fillText(`${det.dist_to_nearest_crop_cm.toFixed(1)}cm to crop`, x1, y2 + 12);
        }
      });

      // 4. Draw Planned Path & Waypoints
      if (plan && plan.waypoints && layers.path) {
        const waypoints = plan.waypoints;

        // Draw Waypoint Rover Footprints & Blade Zones
        waypoints.forEach((wp) => {
          if (layers.footprint && wp.footprint) {
            ctx.beginPath();
            wp.footprint.forEach((pt, idx) => {
              const [cpx, cpy] = cmToPx(pt[0], pt[1]);
              if (idx === 0) ctx.moveTo(cpx, cpy);
              else ctx.lineTo(cpx, cpy);
            });
            ctx.closePath();
            ctx.strokeStyle = 'rgba(59, 130, 246, 0.4)';
            ctx.lineWidth = 1.5;
            ctx.fillStyle = 'rgba(59, 130, 246, 0.05)';
            ctx.fill();
            ctx.stroke();
          }

          if (layers.bladeZone && wp.blade_zone) {
            ctx.beginPath();
            wp.blade_zone.forEach((pt, idx) => {
              const [cpx, cpy] = cmToPx(pt[0], pt[1]);
              if (idx === 0) ctx.moveTo(cpx, cpy);
              else ctx.lineTo(cpx, cpy);
            });
            ctx.closePath();
            ctx.strokeStyle = 'rgba(249, 115, 22, 0.7)';
            ctx.lineWidth = 2;
            ctx.fillStyle = 'rgba(249, 115, 22, 0.15)';
            ctx.fill();
            ctx.stroke();
          }
        });

        // Path Polyline
        ctx.beginPath();
        ctx.lineWidth = 3.5;
        ctx.strokeStyle = '#38bdf8';
        ctx.setLineDash([6, 4]);

        waypoints.forEach((wp, idx) => {
          const [cpx, cpy] = cmToPx(wp.x, wp.y);
          if (idx === 0) ctx.moveTo(cpx, cpy);
          else ctx.lineTo(cpx, cpy);
        });
        ctx.stroke();
        ctx.setLineDash([]); // Reset dash

        // Draw Waypoint Markers
        if (layers.waypoints) {
          waypoints.forEach((wp) => {
            const [cpx, cpy] = cmToPx(wp.x, wp.y);
            ctx.beginPath();
            ctx.arc(cpx, cpy, 7, 0, Math.PI * 2);
            ctx.fillStyle = wp.step === 0 ? '#10b981' : '#0284c7';
            ctx.fill();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.stroke();

            ctx.font = 'bold 9px JetBrains Mono, monospace';
            ctx.fillStyle = '#ffffff';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(wp.step.toString(), cpx, cpy);
          });
        }
      }

      // 5. Draw Animated Rover Avatar
      if (simPose) {
        const [cpx, cpy] = cmToPx(simPose.x, simPose.y);
        ctx.save();
        ctx.translate(cpx, cpy);
        ctx.rotate((simPose.heading * Math.PI) / 180);

        const rw = 25;
        const rl = 30;
        ctx.fillStyle = 'rgba(30, 41, 59, 0.9)';
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 2;
        ctx.fillRect(-rw / 2, -rl / 2, rw, rl);
        ctx.strokeRect(-rw / 2, -rl / 2, rw, rl);

        // Heading arrow
        ctx.beginPath();
        ctx.moveTo(0, -rl / 2);
        ctx.lineTo(-6, -rl / 2 + 10);
        ctx.lineTo(6, -rl / 2 + 10);
        ctx.closePath();
        ctx.fillStyle = '#38bdf8';
        ctx.fill();

        // 6 Wheels
        ctx.fillStyle = '#0f172a';
        ctx.strokeStyle = '#64748b';
        ctx.lineWidth = 1;
        const wheelW = 4;
        const wheelL = 7;
        [-rl / 3, 0, rl / 3].forEach((offsetY) => {
          ctx.fillRect(-rw / 2 - wheelW, offsetY - wheelL / 2, wheelW, wheelL);
          ctx.strokeRect(-rw / 2 - wheelW, offsetY - wheelL / 2, wheelW, wheelL);
          ctx.fillRect(rw / 2, offsetY - wheelL / 2, wheelW, wheelL);
          ctx.strokeRect(rw / 2, offsetY - wheelL / 2, wheelW, wheelL);
        });

        // Dual Front Cutting Blades
        const bladeOffset = 18;
        const bladeWidth = 16;
        ctx.fillStyle = simPose.bladeActive ? '#ef4444' : '#f97316';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.fillRect(-bladeWidth / 2, -rl / 2 - bladeOffset + 12, bladeWidth, 4);
        ctx.strokeRect(-bladeWidth / 2, -rl / 2 - bladeOffset + 12, bladeWidth, 4);

        ctx.restore();
      }
    };
  }, [imageSrc, detections, plan, simPose, layers, selectedPlant, calibrator]);

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const clickX = (e.clientX - rect.left) * scaleX;
    const clickY = (e.clientY - rect.top) * scaleY;

    if (calibratingTwoPoint && onTwoPointClick) {
      onTwoPointClick(clickX, clickY);
      return;
    }

    // Check if clicked inside a plant detection box
    let clickedDet = null;
    for (let i = detections.length - 1; i >= 0; i--) {
      const d = detections[i];
      const [x1, y1, x2, y2] = d.bbox_px;
      if (clickX >= x1 && clickX <= x2 && clickY >= y1 && clickY <= y2) {
        clickedDet = d;
        break;
      }
    }
    setSelectedPlant(clickedDet);
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Layer Visibility Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-xs">
        <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
          <Layers className="w-4 h-4 text-blue-400" />
          <span>Indian Field Overlays:</span>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setLayers((l) => ({ ...l, crops: !l.crops }))}
            className={`px-2.5 py-1 rounded font-medium border transition ${
              layers.crops
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                : 'bg-slate-800 text-slate-500 border-slate-700'
            }`}
          >
            Crops (Green)
          </button>

          <button
            onClick={() => setLayers((l) => ({ ...l, weeds: !l.weeds }))}
            className={`px-2.5 py-1 rounded font-medium border transition ${
              layers.weeds
                ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                : 'bg-slate-800 text-slate-500 border-slate-700'
            }`}
          >
            Actionable Weeds (Red)
          </button>

          <button
            onClick={() => setLayers((l) => ({ ...l, uncertain: !l.uncertain }))}
            className={`px-2.5 py-1 rounded font-medium border transition ${
              layers.uncertain
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                : 'bg-slate-800 text-slate-500 border-slate-700'
            }`}
          >
            Uncertain (Yellow)
          </button>

          <button
            onClick={() => setLayers((l) => ({ ...l, safetyBuffers: !l.safetyBuffers }))}
            className={`px-2.5 py-1 rounded font-medium border transition ${
              layers.safetyBuffers
                ? 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40'
                : 'bg-slate-800 text-slate-500 border-slate-700'
            }`}
          >
            Safety Rings (5cm)
          </button>

          <button
            onClick={() => setLayers((l) => ({ ...l, rejected: !l.rejected }))}
            className={`px-2.5 py-1 rounded font-medium border transition ${
              layers.rejected
                ? 'bg-slate-500/20 text-slate-300 border-slate-500/40'
                : 'bg-slate-800 text-slate-500 border-slate-700'
            }`}
          >
            Soil / Rejected (Gray)
          </button>

          <button
            onClick={() => setLayers((l) => ({ ...l, path: !l.path }))}
            className={`px-2.5 py-1 rounded font-medium border transition ${
              layers.path
                ? 'bg-sky-500/20 text-sky-300 border-sky-500/40'
                : 'bg-slate-800 text-slate-500 border-slate-700'
            }`}
          >
            Rover Path
          </button>

          <button
            onClick={() => setLayers((l) => ({ ...l, bladeZone: !l.bladeZone }))}
            className={`px-2.5 py-1 rounded font-medium border transition ${
              layers.bladeZone
                ? 'bg-orange-500/20 text-orange-300 border-orange-500/40'
                : 'bg-slate-800 text-slate-500 border-slate-700'
            }`}
          >
            Blade Zone
          </button>
        </div>
      </div>

      {/* Main Canvas Viewport */}
      <div className="relative border border-slate-800 rounded-xl overflow-hidden bg-slate-950 flex items-center justify-center min-h-[450px]">
        {calibratingTwoPoint && (
          <div className="absolute top-4 left-4 z-20 bg-amber-600/90 text-white px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 shadow-lg">
            <Crosshair className="w-4 h-4 animate-spin" />
            <span>Calibration Active: Click 2 points on image</span>
          </div>
        )}

        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          className={`max-w-full h-auto object-contain cursor-${calibratingTwoPoint ? 'crosshair' : 'pointer'}`}
        />
      </div>

      {/* Selected Plant Telemetry & Inspection Card */}
      {selectedPlant ? (
        <div className="bg-slate-900/95 border border-slate-700 p-4 rounded-xl shadow-xl flex flex-col gap-3 text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              {selectedPlant.status === 'CROP' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
              {selectedPlant.status === 'ACTIONABLE_WEED' && <XCircle className="w-4 h-4 text-rose-400" />}
              {selectedPlant.status === 'UNCERTAIN' && <AlertTriangle className="w-4 h-4 text-amber-400" />}
              {selectedPlant.status === 'REJECTED' && <Info className="w-4 h-4 text-slate-400" />}
              <span className="font-bold text-sm text-white">
                Plant #{selectedPlant.id}: {selectedPlant.status.replace('_', ' ')}
              </span>
            </div>
            <button
              onClick={() => setSelectedPlant(null)}
              className="text-slate-400 hover:text-white text-xs underline"
            >
              Close
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-slate-300 font-mono">
            <div className="bg-slate-950 p-2 rounded border border-slate-800">
              <span className="text-[10px] text-slate-500 block">Class:</span>
              <span className="font-semibold text-emerald-300 uppercase">{selectedPlant.raw_class_name || selectedPlant.status}</span>
            </div>
            <div className="bg-slate-950 p-2 rounded border border-slate-800">
              <span className="text-[10px] text-slate-500 block">Model Confidence:</span>
              <span className="font-semibold text-white">{(selectedPlant.confidence * 100).toFixed(1)}%</span>
            </div>
            <div className="bg-slate-950 p-2 rounded border border-slate-800">
              <span className="text-[10px] text-slate-500 block">Canopy Area:</span>
              <span className="font-semibold text-white">{selectedPlant.area_cm2 ? `${selectedPlant.area_cm2.toFixed(1)} cm²` : `${selectedPlant.area_px.toFixed(0)} px²`}</span>
            </div>
            <div className="bg-slate-950 p-2 rounded border border-slate-800">
              <span className="text-[10px] text-slate-500 block">Distance to Nearest Crop:</span>
              <span className={`font-semibold ${selectedPlant.dist_to_nearest_crop_cm !== null && selectedPlant.dist_to_nearest_crop_cm < 5.0 ? 'text-amber-400' : 'text-slate-200'}`}>
                {selectedPlant.dist_to_nearest_crop_cm !== null ? `${selectedPlant.dist_to_nearest_crop_cm.toFixed(1)} cm` : 'No crop nearby'}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-950 p-2.5 rounded border border-slate-800 text-[11px]">
            <div>
              <span className="text-slate-400">Centroid Coordinates: </span>
              <span className="font-mono text-sky-400">
                {selectedPlant.center_cm ? `X: ${selectedPlant.center_cm[0].toFixed(1)} cm, Y: ${selectedPlant.center_cm[1].toFixed(1)} cm` : `px: (${selectedPlant.center_px[0]}, ${selectedPlant.center_px[1]})`}
              </span>
            </div>

            <div>
              <span className="text-slate-400">Blade Action: </span>
              <span className={`font-bold font-mono px-2 py-0.5 rounded ${
                selectedPlant.action === 'CUT' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                selectedPlant.action === 'PROTECT' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
                'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              }`}>
                {selectedPlant.action}
              </span>
            </div>
          </div>

          {selectedPlant.rejection_reason && (
            <div className="bg-amber-950/40 border border-amber-500/30 p-2.5 rounded text-amber-200 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>Safety Note: {selectedPlant.rejection_reason}</span>
            </div>
          )}

          <div className="flex justify-end">
            <button
              onClick={() => onWrongDetection && onWrongDetection(selectedPlant)}
              className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs transition"
            >
              Report Misclassification for Active Learning
            </button>
          </div>
        </div>
      ) : (
        <div className="text-xs text-slate-400 flex items-center justify-between px-1">
          <span>Click any plant detection box to inspect botanical species, area, and crop distance.</span>
          <span>Green = Crop (5cm safety buffer) | Red = Actionable Weed | Yellow = Protected/Uncertain</span>
        </div>
      )}
    </div>
  );
}
