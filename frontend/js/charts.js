/* GENOMIND — Motor de gráficos SVG sin dependencias.
   Funciona en cualquier navegador, incluso en hardware modesto. */
"use strict";

const Charts = {
  svg(tag, attrs) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
    return el;
  },

  clear(el) { el.innerHTML = ""; },

  riskColor(ratio) {
    if (ratio < 0.8) return "#34d399";
    if (ratio < 1.5) return "#22d3ee";
    if (ratio < 2.5) return "#fbbf24";
    return "#f87171";
  },

  /* Gauge semicircular 0-100% */
  gauge({ el, value, max = 1, color, label, sublabel, size = 190 }) {
    this.clear(el);
    const w = size, h = size * 0.62;
    const cx = w / 2, cy = h - 6, r = w / 2 - 14;
    const svgEl = this.svg("svg", { viewBox: `0 0 ${w} ${h + 34}`, class: "chart" });
    const frac = Math.max(0, Math.min(1, value / max));

    const arc = (start, end, rIn) => {
      const a0 = Math.PI * (1 + start), a1 = Math.PI * (1 + end);
      const x0 = cx + rIn * Math.cos(a0), y0 = cy - rIn * Math.sin(a0) * 1;
      const x1 = cx + rIn * Math.cos(a1), y1 = cy - rIn * Math.sin(a1) * 1;
      const large = (a1 - a0) > Math.PI ? 1 : 0;
      return `M ${x0} ${y0} A ${rIn} ${rIn} 0 ${large} 1 ${x1} ${y1}`;
    };
    /* Nota: semicírculo superior */
    const halfArc = (start, end, rIn) => {
      const a0 = Math.PI * (1 - start), a1 = Math.PI * (1 - end);
      const x0 = cx + rIn * Math.cos(a0), y0 = cy - rIn * Math.sin(a0);
      const x1 = cx + rIn * Math.cos(a1), y1 = cy - rIn * Math.sin(a1);
      return `M ${x0} ${y0} A ${rIn} ${rIn} 0 0 1 ${x1} ${y1}`;
    };

    svgEl.appendChild(this.svg("path", { d: halfArc(0, 1, r), fill: "none", stroke: "rgba(255,255,255,.08)", "stroke-width": 13, "stroke-linecap": "round" }));
    svgEl.appendChild(this.svg("path", { d: halfArc(0, 1, r), fill: "none", stroke: "url(#gg)", "stroke-width": 13, "stroke-linecap": "round", opacity: .18 }));
    if (frac > 0.004) {
      svgEl.appendChild(this.svg("path", { d: halfArc(0, frac, r), fill: "none", stroke: color || this.riskColor(value / max), "stroke-width": 13, "stroke-linecap": "round" }));
    }

    const defs = this.svg("defs");
    defs.innerHTML = `<linearGradient id="gg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#22d3ee"/><stop offset="1" stop-color="#34d399"/></linearGradient>`;
    svgEl.appendChild(defs);

    const txt = this.svg("text", { x: cx, y: cy - 8, "text-anchor": "middle", fill: "#e6edf6", "font-size": 26, "font-weight": 700, "font-family": "'Space Grotesk',sans-serif" });
    txt.textContent = label;
    svgEl.appendChild(txt);
    const sub = this.svg("text", { x: cx, y: cy + 14, "text-anchor": "middle", fill: "#8fa3bd", "font-size": 11.5 });
    sub.textContent = sublabel || "";
    svgEl.appendChild(sub);
    el.appendChild(svgEl);
    return svgEl;
  },

  /* Radar de estilo de vida */
  radar({ el, labels, values, size = 300, max = 100 }) {
    this.clear(el);
    const cx = size / 2, cy = size / 2, R = size / 2 - 44;
    const n = labels.length;
    const pt = (i, frac) => {
      const a = (Math.PI * 2 * i) / n - Math.PI / 2;
      return [cx + R * frac * Math.cos(a), cy + R * frac * Math.sin(a)];
    };
    const svgEl = this.svg("svg", { viewBox: `0 0 ${size} ${size}`, class: "chart" });

    for (let ring = 1; ring <= 4; ring++) {
      const frac = ring / 4;
      const d = labels.map((_, i) => pt(i, frac)).map((p, j) => (j ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ") + " Z";
      svgEl.appendChild(this.svg("path", { d, fill: ring === 4 ? "rgba(34,211,238,.04)" : "none", stroke: "rgba(255,255,255,.09)", "stroke-width": 1 }));
    }
    labels.forEach((_, i) => {
      const [x, y] = pt(i, 1);
      svgEl.appendChild(this.svg("line", { x1: cx, y1: cy, x2: x, y2: y, stroke: "rgba(255,255,255,.09)" }));
    });

    const poly = values.map((v, i) => pt(i, Math.max(0, Math.min(max, v)) / max));
    const d = poly.map((p, j) => (j ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ") + " Z";
    svgEl.appendChild(this.svg("path", { d, fill: "rgba(52,211,153,.18)", stroke: "#34d399", "stroke-width": 2.2, "stroke-linejoin": "round" }));
    poly.forEach((p) => svgEl.appendChild(this.svg("circle", { cx: p[0], cy: p[1], r: 3.4, fill: "#34d399" })));

    labels.forEach((lab, i) => {
      const [x, y] = pt(i, 1.24);
      const t = this.svg("text", {
        x, y, "text-anchor": x < cx - 6 ? "end" : (x > cx + 6 ? "start" : "middle"),
        "dominant-baseline": "middle", fill: "#8fa3bd", "font-size": 11.5, "font-weight": 600,
      });
      t.textContent = lab;
      svgEl.appendChild(t);
      const [vx, vy] = pt(i, 1.38);
      const v = this.svg("text", {
        x: vx, y: vy + 12, "text-anchor": x < cx - 6 ? "end" : (x > cx + 6 ? "start" : "middle"),
        fill: "#34d399", "font-size": 11, "font-family": "'Space Grotesk',sans-serif", "font-weight": 700,
      });
      v.textContent = Math.round(values[i]);
      svgEl.appendChild(v);
    });
    el.appendChild(svgEl);
  },

  /* Barras horizontales */
  hbars({ el, items, color = "#22d3ee", height = 24, barColor }) {
    this.clear(el);
    const w = 520, rowH = height + 8;
    const svgEl = this.svg("svg", { viewBox: `0 0 ${w} ${items.length * rowH + 6}`, class: "chart", style: "width:100%" });
    items.forEach((it, i) => {
      const y = i * rowH + 4;
      const labelW = 190;
      const barW = Math.max(2, (it.value / Math.max(...items.map(x => x.max || 1), 0.0001)) * (w - labelW - 70));
      const lab = this.svg("text", { x: labelW - 10, y: y + height / 2 + 4, "text-anchor": "end", fill: "#c3d0e0", "font-size": 11.5, "font-weight": 600 });
      lab.textContent = it.label;
      svgEl.appendChild(lab);
      svgEl.appendChild(this.svg("rect", { x: labelW, y, width: w - labelW - 70, height, rx: 6, fill: "rgba(255,255,255,.06)" }));
      svgEl.appendChild(this.svg("rect", { x: labelW, y, width: barW, height, rx: 6, fill: barColor || (it.color || color), opacity: it.faded ? .5 : 1 }));
      const val = this.svg("text", { x: w - 4, y: y + height / 2 + 4, "text-anchor": "end", fill: "#8fa3bd", "font-size": 11.5, "font-family": "'Space Grotesk',sans-serif" });
      val.textContent = it.display != null ? it.display : it.value;
      svgEl.appendChild(val);
    });
    el.appendChild(svgEl);
  },

  /* Dispersión con ejes */
  scatter({ el, points, xLabel, yLabel, highlight, size = 520 }) {
    this.clear(el);
    const w = size, h = size * 0.72;
    const padL = 56, padB = 46, padT = 18, padR = 16;
    const xs = points.map(p => p.x), ys = points.map(p => p.y);
    const xMin = Math.min(...xs), xMax = Math.max(...xs, xMin + 1);
    const yMin = Math.min(...ys) * 0.94, yMax = Math.max(...ys) * 1.03;
    const sx = (x) => padL + ((x - xMin) / (xMax - xMin)) * (w - padL - padR);
    const sy = (y) => h - padB - ((y - yMin) / (yMax - yMin)) * (h - padB - padT);

    const svgEl = this.svg("svg", { viewBox: `0 0 ${w} ${h}`, class: "chart", style: "width:100%" });
    for (let i = 0; i <= 4; i++) {
      const yy = padT + ((h - padB - padT) * i) / 4;
      svgEl.appendChild(this.svg("line", { x1: padL, y1: yy, x2: w - padR, y2: yy, stroke: "rgba(255,255,255,.07)" }));
      const val = yMax - ((yMax - yMin) * i) / 4;
      const t = this.svg("text", { x: padL - 8, y: yy + 4, "text-anchor": "end", fill: "#8fa3bd", "font-size": 10 });
      t.textContent = Math.round(val);
      svgEl.appendChild(t);
    }
    for (let i = 0; i <= 5; i++) {
      const xx = padL + ((w - padL - padR) * i) / 5;
      const t = this.svg("text", { x: xx, y: h - padB + 18, "text-anchor": "middle", fill: "#8fa3bd", "font-size": 10 });
      t.textContent = Math.round(xMin + ((xMax - xMin) * i) / 5);
      svgEl.appendChild(t);
    }
    const xt = this.svg("text", { x: (w + padL) / 2, y: h - 8, "text-anchor": "middle", fill: "#8fa3bd", "font-size": 11.5, "font-weight": 600 });
    xt.textContent = xLabel;
    svgEl.appendChild(xt);
    const yt = this.svg("text", { x: 14, y: (h - padB) / 2, "text-anchor": "middle", fill: "#8fa3bd", "font-size": 11.5, "font-weight": 600, transform: `rotate(-90 14 ${(h - padB) / 2})` });
    yt.textContent = yLabel;
    svgEl.appendChild(yt);

    points.forEach((p) => {
      const isHi = highlight && highlight(p);
      const c = isHi ? "#f87171" : (p.pm25 > 35 ? "#fbbf24" : "#22d3ee");
      const g = this.svg("circle", { cx: sx(p.x), cy: sy(p.y), r: isHi ? 6 : 4.6, fill: c, opacity: .85, stroke: isHi ? "#fff" : "none", "stroke-width": 1.5 });
      const title = this.svg("title");
      title.textContent = `${p.label} — PM2.5: ${p.x} µg/m³ · Esperanza: ${p.y} años`;
      g.appendChild(title);
      g.style.cursor = "pointer";
      svgEl.appendChild(g);
    });
    el.appendChild(svgEl);
  },

  /* Título accesible */
  labelled(el, title) {
    el.setAttribute("role", "img");
    el.setAttribute("aria-label", title);
  },
};
