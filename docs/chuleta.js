/* MTG Forja — chuleta: dos caras A4 densas, pensadas para imprimir.
   Única implementación: la usa la web y la incrusta src/mtg_forja/render/chuleta.py. */
(function (global) {
  "use strict";

  const C = global.ForjaComun;

  const CSS = C.PALETA + C.CSS_CURVA + `
*{box-sizing:border-box}
body{margin:0;background:#D9D2C4;font-family:var(--serif);color:var(--tinta)}
.hoja{width:210mm;min-height:297mm;margin:14px auto;background:var(--papel);padding:9mm 9mm 7mm;
 box-shadow:0 3px 14px rgba(0,0,0,.2);display:flex;flex-direction:column}
h1{font-size:20pt;margin:0;line-height:1;letter-spacing:-.01em}
h1 em{font-style:normal;color:var(--brasa)}
.sub{font-family:var(--cond);text-transform:uppercase;letter-spacing:.14em;font-size:6.6pt;
 color:var(--humo);margin:3px 0 0}
.cab{display:flex;justify-content:space-between;align-items:flex-end;
 border-bottom:1.6pt solid var(--tinta);padding-bottom:5px;margin-bottom:7px}
.cab .curva{height:34px}
.cab .cb{width:13px}
.cab .cb i{font-size:5.6pt;bottom:-9px}
.cab .cb u{font-size:6pt}
.curva-w{text-align:right}
.curva-w p{font-family:var(--cond);font-size:5.8pt;text-transform:uppercase;letter-spacing:.1em;
 color:var(--humo);margin:11px 0 0}
.cols{column-count:2;column-gap:6mm;flex:1}
.bl{break-inside:avoid-column;margin-bottom:5px}
h2{font-family:var(--cond);font-size:7.4pt;text-transform:uppercase;letter-spacing:.16em;
 color:var(--brasa);margin:6px 0 4px;padding-bottom:2px;border-bottom:.8pt solid var(--lin)}
.r{display:flex;gap:5px;break-inside:avoid;margin-bottom:6px;align-items:flex-start}
.ts{display:flex;gap:2px;flex:0 0 auto;padding-top:1px}
.t{position:relative;width:29px;display:block}
.t img{width:100%;aspect-ratio:488/680;object-fit:cover;display:block;border-radius:2px;
 background:#2b241d;position:relative;z-index:2}
.t em{position:absolute;inset:0;z-index:1;display:flex;align-items:center;justify-content:center;
 text-align:center;font-family:var(--cond);font-size:4.4pt;font-style:normal;color:#CBBFA6;
 padding:2px;line-height:1.05;text-transform:uppercase}
.t .n{position:absolute;top:-3px;left:-3px;z-index:3;background:var(--brasa);color:#fff;
 font-family:var(--cond);font-style:normal;font-weight:700;font-size:6.2pt;width:12px;height:12px;
 border-radius:50%;display:flex;align-items:center;justify-content:center}
.d{flex:1;min-width:0}
p{margin:0}
.h{font-size:8.4pt;font-weight:700;line-height:1.15}
.tn{font-family:var(--cond);font-size:6pt;font-weight:700;letter-spacing:.06em;color:#fff;
 background:var(--tinta);padding:1px 4px;border-radius:2px;margin-right:5px;vertical-align:1px;
 text-transform:uppercase}
.r.conflicto .tn,.r.aviso .tn{background:var(--brasa)}
.x{font-size:7.8pt;line-height:1.3;margin-top:1px}
.o{font-size:7pt;line-height:1.25;color:var(--brasa);margin-top:1px;padding-left:7px;
 border-left:1.4pt solid var(--brasa)}
.orden{display:flex;gap:4px;justify-content:space-between;margin-top:4px}
.ob{flex:1;text-align:center;font-size:7pt;line-height:1.2}
.ob .t{width:100%;margin:0 auto 3px}
.ob i{display:block;font-style:normal;font-family:var(--cond);font-weight:700;font-size:6.4pt;
 color:var(--brasa);letter-spacing:.06em}
.ob em{font-style:normal;display:block;font-size:6.8pt}
.mull{display:flex;gap:5mm;margin-top:3px}
.mull>div{flex:1;min-width:0;padding:4px 7px 5px;border:.8pt solid var(--lin);border-top-width:2.4pt}
.mull .si{border-top-color:#3E6B3A}.mull .no{border-top-color:var(--brasa)}
.mull h3{margin:0 0 3px;font-family:var(--cond);font-size:6.8pt;text-transform:uppercase;
 letter-spacing:.14em}
.mull .si h3{color:#3E6B3A}.mull .no h3{color:var(--brasa)}
.mull ul{margin:0;padding-left:11px}.mull li{font-size:7.6pt;line-height:1.28;margin-bottom:2px}
.prob{display:flex;gap:6mm;align-items:flex-end;margin-top:6px}
.barras{display:flex;gap:2px;align-items:flex-end;height:40px}
.barras span{width:17px;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;
 height:100%;font-family:var(--cond);font-size:5.6pt;color:var(--humo)}
.barras b{display:block;width:100%;background:var(--lin);border-radius:1px 1px 0 0}
.barras .ok b{background:#3E6B3A}.barras .ok{color:var(--tinta);font-weight:700}
.barras i{font-style:normal;margin-top:2px}
.cifras{flex:1;font-size:7.4pt;line-height:1.35}
.cifras b{font-family:var(--cond);font-size:8.6pt}
.pie{margin-top:auto;padding-top:5px;border-top:1pt solid var(--tinta);display:flex;
 justify-content:space-between;font-family:var(--cond);font-size:5.8pt;text-transform:uppercase;
 letter-spacing:.1em;color:var(--humo)}
@media print{@page{size:A4;margin:0}body{background:#fff}
 .hoja{margin:0;box-shadow:none;page-break-after:always;min-height:0;height:297mm}
 .hoja:last-child{page-break-after:auto}
 *{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
`;

  function mini(nombre, copias) {
    const n = copias ? `<i class="n">${copias}</i>` : "";
    return `<span class="t">${n}<img loading="lazy" alt="${C.e(nombre)}" ` +
      `src="${C.imagen(nombre, "small")}"><em>${C.e(nombre)}</em></span>`;
  }

  /** Devuelve el contenido de <body> a partir del documento. */
  function cuerpo(doc) {
    const idx = C.indice(doc);

    const columnas = C.bloques(doc).map(([bloque, lista]) => {
      const filas = lista.map((s) => {
        const minis = (s.piezas || []).map((n) => mini(n, (idx[n] || {}).copias)).join("");
        const aviso = s.aviso ? `<p class="o">${s.aviso}</p>` : "";
        return `<div class="r ${C.e(s.tipo || "")}"><div class="ts">${minis}</div><div class="d">` +
          `<p class="h"><span class="tn">${C.e(s.turno || "—")}</span>` +
          `${C.e(s.nombre || "")}</p>` +
          `<p class="x">${s.resumen || ""}</p>${aviso}</div></div>`;
      }).join("");
      return `<section class="bl"><h2>${C.e(bloque)}</h2>${filas}</section>`;
    }).join("");

    const orden = (doc.orden || []).map((o) =>
      `<span class="ob">${mini(o.carta || "")}<i>${C.e(o.turno || "")}</i>` +
      `<em>${C.e(o.resumen || o.que || "")}</em></span>`).join("");

    const reglas = (doc.reglas_oro || []).map((r, i) =>
      `<p class="x" style="margin-bottom:4px"><b>${i + 1}.</b> ${typeof r === "string" ? r : (r.texto || "")}</p>`).join("");

    const m = doc.mulligan;
    let mull = "";
    if (m) {
      const items = (l) => (l || []).map((it) =>
        `<li>${typeof it === "string" ? it : (it.texto || "")}</li>`).join("");
      const st = m.estadisticas || {};
      const [lo, hi] = m.tierras || [-1, -1];
      const max = Math.max(...(st.dist7 || [1]));
      const barras = (st.dist7 || []).map((p, k) =>
        `<span class="${k >= lo && k <= hi ? "ok" : ""}">${Math.round(p * 100)}%` +
        `<b style="height:${Math.round(28 * p / max)}px"></b><i>${k}</i></span>`).join("");
      const pct = (p) => `<b>${Math.round(p * 100)} %</b>`;
      const cifras = [];
      if (st.en_rango_7 !== undefined) {
        cifras.push(`Mano de 7 con ${lo}–${hi} tierras: ${pct(st.en_rango_7)}`);
        cifras.push(`Tras mulligan a 6 (robas 7, una al fondo): ${pct(st.en_rango_6)}`);
      }
      for (const k of st.claves || []) {
        cifras.push(`${C.e(k.nombre)} (${k.copias} cartas) en la mano de 7: ${pct(k.p7)}`);
      }
      mull = '<h2 style="margin-top:12px">Mulligan</h2>' +
        (m.resumen ? `<p class="x">${m.resumen}</p>` : "") +
        `<div class="mull"><div class="si"><h3>Quédate</h3><ul>${items(m.quedarse)}</ul></div>` +
        `<div class="no"><h3>Mulligan</h3><ul>${items(m.mulligan)}</ul></div></div>` +
        (barras ? `<div class="prob"><div><div class="barras">${barras}</div>` +
          `<p class="sub" style="margin-top:3px">Tierras en la mano de 7 · ${st.tierras} de ${st.cartas}</p></div>` +
          `<div class="cifras">${cifras.map((c) => `<p>${c}</p>`).join("")}</div></div>` : "") +
        (m.tras_mulligan ? `<p class="o" style="margin-top:6px"><b>Si haces mulligan:</b> ${m.tras_mulligan}</p>` : "");
    }

    let tierras = "";
    if (doc.tierras_guia) {
      const t = doc.tierras_guia;
      tierras = '<h2 style="margin-top:12px">Tierras</h2>' +
        ((t.secuencia || []).length ? '<p class="x" style="margin-bottom:5px"><b>Orden:</b> ' +
          t.secuencia.join(" · ") + "</p>" : "") +
        '<div class="cols">' + (t.detalle || []).map((d) =>
          `<div class="r"><div class="ts">${mini(d.nombre, d.copias)}</div><div class="d">` +
          `<p class="h">${C.e(d.nombre)}</p><p class="x">${d.como_jugarla}</p></div></div>`).join("") +
        "</div>";
    }

    let cara2 = "";
    if (orden || reglas || mull || tierras) {
      cara2 = `<div class="hoja">
<div class="cab"><div><h1>Orden <em>· mulligan, tierras y reglas</em></h1>
<p class="sub">La secuencia por defecto, qué mano jugar, cómo usar cada tierra y los principios que no cambian</p></div></div>
${orden ? '<h2>Orden de aparición</h2><div class="orden">' + orden + "</div>" : ""}
${mull}
${tierras}
${reglas ? '<h2 style="margin-top:12px">Reglas de oro</h2><div class="cols">' + reglas + "</div>" : ""}
<div class="pie"><span>Cara 2 · secuencia</span><span>${C.firma(doc)} · MTG Forja</span></div></div>`;
    }

    return `<div class="hoja">
<div class="cab">
 <div><h1>${C.e(doc.titulo || "")} <em>· chuleta de combos</em></h1>
 <p class="sub">${C.e(doc.subtitulo || "")}</p></div>
 <div class="curva-w">${C.curvaSvg(doc.curva || {})}<p>Curva por valor de maná</p></div>
</div>
<div class="cols">${columnas}</div>
<div class="pie"><span>Cara 1 · sinergias</span>
<span>${C.firma(doc)} · los números rojos son copias en el mazo</span></div>
</div>${cara2}`;
  }

  global.ForjaChuleta = {
    css: CSS,
    cuerpo,
    montar: (doc) => C.montar(CSS, cuerpo(doc)),
  };
})(typeof window !== "undefined" ? window : globalThis);
