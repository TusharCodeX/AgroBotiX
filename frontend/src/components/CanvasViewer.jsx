import React, { useRef, useEffect, useState } from 'react';
import { Layers, Eye, EyeOff, Flag, Crosshair } from 'lucide-react';

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
    path: true,
    waypoints: true,
    footprint: true,
    bladeZone: true,
    gridOverlay: false,
  });

  const [hoveredPlant, setHoveredPlant] = useState(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (!imageSrc) {
      // Draw placeholder
      canvas.width = 800;
      canvas.height = 500;
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#475569';
      ctx.font = '16px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Capture a field image or upload a photo to begin', canvas.width / 2, canvas.height / 2);
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

      // Helper for converting cm to canvas pixel
      const cmToPx = (xCm, yCm) => {
        if (calibrator && calibrator.cm_per_pixel) {
          const scale = calibrator.cm_per_pixel;
          const frontY = (calibrator.robot_length_cm || 30.0) / 2 + (calibrator.ground_y_offset_cm || 10.0);
          const px = (xCm / scale) + w / 2;
          const py = h - ((yCm - frontY) / scale);
          return [px, py];
        }
        return [w / 2 + xCm * 5, h - yCm * 5];
      };

      // 2. Draw Bounding Boxes
      detections.forEach((det) => {
        const [x1, y1, x2, y2] = det.bbox_px;
        const [cx, cy] = det.center_px;
        const bw = x2 - x1;
        const bh = y2 - y1;

        if (det.status === 'CROP' && !layers.crops) return;
        if (det.status === 'WEED' && !layers.weeds) return;
        if (det.status === 'UNCERTAIN' && !layers.uncertain) return;

        let color = '#22c55e'; // Green for Crop
        let label = `CROP #${det.id}`;
        if (det.status === 'WEED') {
          color = '#ef4444'; // Red for Weed
          label = `WEED #${det.id}`;
        } else if (det.status === 'UNCERTAIN') {
          color = '#eab308'; // Yellow for Uncertain
          label = `UNCERTAIN #${det.id}`;
        }

        ctx.lineWidth = 2.5;
        ctx.strokeStyle = color;
        ctx.fillStyle = color + '22';
        ctx.fillRect(x1, y1, bw, bh);
        ctx.strokeRect(x1, y1, bw, bh);

        // Center dot
        ctx.beginPath();
        ctx.arc(cx, cy, 4, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();

        // Label pill
        ctx.font = 'bold 12px JetBrains Mono, monospace';
        const text = `${label} (${(det.confidence * 100).toFixed(0)}%)`;
        const textWidth = ctx.measureText(text).width;
        ctx.fillStyle = color;
        ctx.fillRect(x1, Math.max(0, y1 - 20), textWidth + 12, 20);
        ctx.fillStyle = '#000000';
        ctx.fillText(text, x1 + 6, Math.max(14, y1 - 5));
      });

      // 3. Draw Planned Path & Waypoints
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

            // Step number text
            ctx.font = 'bold 9px JetBrains Mono, monospace';
            ctx.fillStyle = '#ffffff';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(wp.step.toString(), cpx, cpy);
          });
        }
      }

      // 4. Draw Animated Rover Simulation Avatar
      if (simPose) {
        const [cpx, cpy] = cmToPx(simPose.x, simPose.y);
        ctx.save();
        ctx.translate(cpx, cpy);
        // Heading 0 is +Y (upwards on screen, which is -py)
        ctx.rotate((simPose.heading * Math.PI) / 180);

        // Rover body (rectangle)
        const rw = 25; // display width
        const rl = 30; // display length
        ctx.fillStyle = 'rgba(30, 41, 59, 0.9)';
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 3;
        ctx.fillRect(-rw / 2, -rl / 2, rw, rl);
        ctx.strokeRect(-rw / 2, -rl / 2, rw, rl);

        // 6 Skid-steer Wheels (3 left, 3 right)
        ctx.fillStyle = '#64748b';
        [-rl / 2 + 3, 0, rl / 2 - 3].forEach((wy) => {
          ctx.fillRect(-rw / 2 - 4, wy - 3, 4, 6);
          ctx.fillRect(rw / 2, wy - 3, 4, 6);
        });

        // Dual Cutting Blades at Front
        ctx.strokeStyle = simPose.bladeOn ? '#ef4444' : '#f97316';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(-rw / 2 + 2, -rl / 2 - 10);
        ctx.lineTo(rw / 2 - 2, -rl / 2 - 10);
        ctx.stroke();

        // Heading arrow
        ctx.fillStyle = '#38bdf8';
        ctx.beginPath();
        ctx.moveTo(0, -rl / 2 - 5);
        ctx.lineTo(-4, -rl / 2 + 2);
        ctx.lineTo(4, -rl / 2 + 2);
        ctx.closePath();
        ctx.fill();

        ctx.restore();
      }
    };
  }, [imageSrc, detections, plan, simPose, layers]);

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

    // Check if clicked inside a plant box for feedback
    const clickedPlant = detections.find((det) => {
      const [x1, y1, x2, y2] = det.bbox_px;
      return clickX >= x1 && clickX <= x2 && clickY >= y1 && clickY <= y2;
    });

    if (clickedPlant && onWrongDetection) {
      onWrongDetection(clickedPlant);
    }
  };

  return (
    <div className="flex flex-col gap-2 relative" ref={containerRef}>
      {/* Canvas Layer Toggles Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-900/80 backdrop-blur p-2 rounded-lg border border-slate-800 text-xs">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-slate-400" />
          <span className="font-semibold text-slate-300">Layers:</span>
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
            Weeds (Red)
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
            onClick={() => setLayers((l) => ({ ...l, path: !l.path }))}
            className={`px-2.5 py-1 rounded font-medium border transition ${
              layers.path
                ? 'bg-sky-500/20 text-sky-300 border-sky-500/40'
                : 'bg-slate-800 text-slate-500 border-slate-700'
            }`}
          >
            Path Polyline
          </button>

          <button
            onClick={() => setLayers((l) => ({ ...l, footprint: !l.footprint }))}
            className={`px-2.5 py-1 rounded font-medium border transition ${
              layers.footprint
                ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'
                : 'bg-slate-800 text-slate-500 border-slate-700'
            }`}
          >
            Rover Footprint
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

      <div className="text-xs text-slate-400 flex items-center justify-between px-1">
        <span>Click any detection box to report a misclassification for retraining.</span>
        <span>Origin (0,0): Robot Center | +Y: Forward | +X: Right</span>
      </div>
    </div>
  );
}
