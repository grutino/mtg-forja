/* MTG Forja — guía extensa: una página larga con cada sinergia desarrollada.
   Única implementación: la usa la web y la incrusta src/mtg_forja/render/guia.py. */
(function (global) {
  "use strict";

  const C = global.ForjaComun;

  const CSS = C.PALETA + C.PIPS + C.CSS_CURVA + `
*{box-sizing:border-box}
body{margin:0;background:var(--pergamino);color:var(--tinta);font-family:var(--serif);
 font-size:15px;line-height:1.5}
.wrap{max-width:1000px;margin:0 auto;padding:0 28px 64px}
header{background:var(--ceniza);color:var(--papel);position:relative;overflow:hidden;margin-bottom:44px}
header .wrap{padding:46px 28px 44px;position:relative;z-index:2}
.sol{position:absolute;left:50%;bottom:-260px;transform:translateX(-50%);width:620px;height:620px;
 border-radius:50%;background:radial-gradient(circle,rgba(230,196,120,.30) 0%,
 rgba(168,50,26,.20) 42%,rgba(27,23,20,0) 68%);z-index:1}
.eyebrow{font-family:var(--cond);text-transform:uppercase;letter-spacing:.20em;font-size:11px;
 font-weight:700;color:var(--laton)}
header .eyebrow{color:#D8B15E}
h1{font-size:clamp(38px,7vw,60px);line-height:.96;margin:10px 0 6px;font-weight:700;letter-spacing:-.01em}
h1 em{font-style:normal;color:#D8B15E}
.dek{color:#B9AE9C;max-width:56ch;margin:0}
.c{margin:0;width:118px;position:relative;flex:0 0 auto}
.c .marco{display:block;position:relative;aspect-ratio:488/680;border-radius:6px;overflow:hidden;
 background:linear-gradient(160deg,#3a332c,#191512);box-shadow:0 2px 6px rgba(30,22,14,.28)}
.c img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;z-index:2}
.c .ph{position:absolute;inset:0;z-index:1;display:flex;align-items:center;justify-content:center;
 text-align:center;padding:8px;font-family:var(--cond);font-size:11px;font-weight:700;
 letter-spacing:.04em;color:#C9BFA8;text-transform:uppercase}
.c figcaption{font-size:11.5px;line-height:1.25;margin-top:5px;font-weight:700;display:flex;
 flex-wrap:wrap;gap:4px;align-items:center}
.c .n{position:absolute;top:-7px;left:-7px;z-index:3;background:var(--brasa);color:#fff;
 font-family:var(--cond);font-weight:700;font-size:13px;line-height:1;width:27px;height:27px;
 border-radius:50%;display:flex;align-items:center;justify-content:center;
 box-shadow:0 1px 3px rgba(0,0,0,.35)}
.c .n small{font-size:9px;margin-left:1px}
.piezas{display:flex;flex-wrap:wrap;align-items:flex-start;gap:14px;margin:16px 0 18px}
.mas{font-family:var(--cond);color:var(--humo);font-size:18px;font-weight:700;align-self:center;
 margin-top:-14px}
.seccion{margin-top:48px}
.seccion h2{font-size:26px;margin:2px 0 4px;font-weight:700;letter-spacing:-.015em;
 border-bottom:2px solid var(--tinta);padding-bottom:10px}
.seccion .intro{color:var(--humo);margin:12px 0 0;font-size:14px;max-width:70ch}
.combo{margin-top:28px;padding-left:74px;position:relative;break-inside:avoid}
.turno{position:absolute;left:0;top:2px;width:64px;text-align:center;font-family:var(--cond);
 font-weight:700;font-size:11px;letter-spacing:.05em;color:var(--brasa);border:1px solid var(--brasa);
 border-radius:3px;padding:3px 2px;text-transform:uppercase}
.combo.conflicto .turno,.combo.aviso .turno{color:var(--humo);border-color:var(--lin)}
.combo h3{margin:0;font-size:19px;font-weight:700;letter-spacing:-.01em}
.combo h3 .que{color:var(--humo);font-weight:400;font-size:15px;display:block;margin-top:2px}
ol.sec{margin:0;padding:0;list-style:none;counter-reset:paso}
ol.sec li{counter-increment:paso;position:relative;padding-left:26px;margin-bottom:7px;font-size:14.5px}
ol.sec li::before{content:counter(paso);position:absolute;left:0;top:1px;font-family:var(--cond);
 font-size:11px;font-weight:700;width:17px;height:17px;border-radius:50%;background:var(--tinta);
 color:var(--papel);display:flex;align-items:center;justify-content:center}
.ojo{margin-top:12px;padding:9px 13px;background:rgba(168,50,26,.07);border-left:3px solid var(--brasa);
 font-size:13.5px;line-height:1.45}
.ojo b{font-family:var(--cond);text-transform:uppercase;letter-spacing:.08em;font-size:11px;
 color:var(--brasa);display:block;margin-bottom:2px}
.grupo{margin-top:26px;break-inside:avoid}
.grupo .eyebrow span{color:var(--tinta);margin-left:6px}
.rejilla{display:flex;flex-wrap:wrap;gap:14px;margin-top:12px}

.citas{margin:12px 0 0;padding:0;list-style:none;font-size:12.5px;color:var(--humo)}
.citas li{margin:3px 0;padding-left:12px;border-left:2px solid var(--lin)}
.citas q{font-style:italic;color:var(--tinta)}
.citas .org{font-family:var(--cond);font-size:10px;letter-spacing:.08em;text-transform:uppercase;
 margin-left:4px}
.ref{font-family:var(--cond);font-size:11px;font-weight:700;color:var(--brasa);text-decoration:none;
 margin-left:3px}
.veredicto{background:var(--papel);border:1px solid var(--lin);border-left:4px solid var(--laton);
 padding:18px 22px;margin-top:18px}
.veredicto p{margin:0 0 10px}
.veredicto .cols{display:flex;gap:28px;flex-wrap:wrap;margin-top:6px}
.veredicto .cols div{flex:1 1 260px}
.veredicto h4{font-family:var(--cond);text-transform:uppercase;letter-spacing:.12em;font-size:11px;
 margin:6px 0 4px;color:var(--laton)}
.veredicto ul{margin:0;padding-left:18px;font-size:14px}
.firma{font-family:var(--cond);font-size:11px;letter-spacing:.1em;text-transform:uppercase;
 color:#D8B15E;margin-top:16px}
ol.fuentes{font-size:13px;padding-left:22px}ol.fuentes a{color:var(--brasa)}
.mejora{background:var(--papel);border:1px solid var(--lin);border-left:4px solid var(--laton);
 padding:16px 20px;margin-top:18px}
.mejora h3{margin:0 0 6px;font-size:18px}
.mejora .nivel{font-family:var(--cond);text-transform:uppercase;letter-spacing:.1em;font-size:10.5px;
 padding:2px 8px;margin-left:10px;vertical-align:3px;border:1px solid currentColor;color:var(--laton)}
.mejora .nivel.clara{color:var(--brasa)}
.mejora p{margin:0 0 10px;max-width:75ch}
.cambio{display:flex;gap:22px;flex-wrap:wrap;align-items:flex-start;margin:6px 0 4px}
.cambio .lado{flex:0 1 auto}
.cambio .lado h4{font-family:var(--cond);text-transform:uppercase;letter-spacing:.12em;font-size:11px;
 margin:0 0 6px;color:var(--humo)}
.cambio .lado .rejilla{display:flex;gap:10px;flex-wrap:wrap}
.cambio .flecha{align-self:center;font-size:26px;color:var(--humo)}
.tierra{display:flex;gap:18px;align-items:flex-start;margin-top:18px;padding-top:14px;
 border-top:1px solid var(--lin)}
.tierra .c{flex:0 0 auto;margin-left:10px}
.tierra h3{margin:0 0 4px;font-size:17px}
.tierra p{margin:0 0 8px;max-width:70ch}
.tierra .k{font-family:var(--cond);text-transform:uppercase;letter-spacing:.1em;font-size:11px;
 color:var(--humo);margin-right:6px}
.porque{margin:8px 0 0;font-size:14.5px;line-height:1.5;max-width:75ch}
.arena{background:var(--papel);border:1px solid var(--lin);padding:14px 18px;margin-top:12px;
 font-size:13px;line-height:1.45;white-space:pre-wrap;overflow-x:auto}
.copiar{margin-top:16px;font-family:var(--cond);text-transform:uppercase;letter-spacing:.1em;
 font-size:12px;padding:7px 14px;border:1px solid var(--tinta);background:var(--tinta);color:var(--papel);
 cursor:pointer}
.plan{margin-top:20px}.plan h3{margin:0 0 4px;font-size:18px}.plan p{margin:0;max-width:75ch}
footer{margin-top:52px;padding-top:18px;border-top:2px solid var(--tinta);font-size:12.5px;
 color:var(--humo);display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}
footer span{font-family:var(--cond);letter-spacing:.06em;text-transform:uppercase;font-size:11px}
@media (max-width:680px){.wrap{padding:0 16px 48px}.combo{padding-left:0}
 .turno{position:static;display:inline-block;margin-bottom:8px;width:auto;padding:3px 10px}
 .c{width:96px}}
@media print{@page{size:A4;margin:12mm}body{background:#fff;font-size:10.5pt}
 *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
 .sol{display:none}.wrap{max-width:none;padding:0}header .wrap{padding:24px 18px}
 .c{width:92px}.seccion{margin-top:24px}.combo{margin-top:18px}}
`;

  function ficha(carta, nombre, contar) {
    if (contar === undefined) contar = true;
    const copias = carta ? carta.copias : null;
    const coste = carta ? (carta.coste || "") : "";
    const tipo = carta ? (carta.tipo || "") : "";
    const badge = (contar && copias) ? `<span class="n">${copias}<small>×</small></span>` : "";
    const sub = C.pips(coste) || (tipo.includes("Land")
      ? '<span style="font-family:var(--cond);font-size:10px;letter-spacing:.08em;' +
        'text-transform:uppercase;color:var(--humo)">tierra</span>'
      : "");
    return `<figure class="c">${badge}<span class="marco"><span class="ph">${C.e(nombre)}</span>` +
      `<img loading="lazy" alt="${C.e(nombre)}" src="${C.imagen(nombre)}"></span>` +
      `<figcaption>${C.e(nombre)}<span class="coste">${sub}</span></figcaption></figure>`;
  }

  /** Devuelve el contenido de <body> a partir del documento. */
  function cuerpo(doc) {
    const idx = C.indice(doc);
    const partes = [];

    const rev = doc.revision_experta || {};
    if (rev.veredicto) {
      const lista = (xs) => (xs || []).map((x) => `<li>${x}</li>`).join("");
      const cols = (rev.fortalezas || rev.debilidades)
        ? `<div class="cols"><div><h4>Puntos fuertes</h4><ul>${lista(rev.fortalezas)}</ul></div>` +
          `<div><h4>Puntos débiles</h4><ul>${lista(rev.debilidades)}</ul></div></div>` : "";
      partes.push('<section class="seccion"><p class="eyebrow">Valoración del experto</p>' +
        `<h2>${C.e(rev.titular || "Qué tal es el mazo")}</h2><div class="veredicto">` +
        `<p>${rev.veredicto}${C.refs(rev.fuentes, doc)}</p>${cols}` +
        `<p style="margin:12px 0 0;font-size:12.5px;color:var(--humo)">${C.firma(doc)}` +
        (rev.confianza ? ` · confianza ${C.e(rev.confianza)}` : "") + "</p></div></section>");
    }
    if ((doc.planes || []).length) {
      partes.push('<section class="seccion"><p class="eyebrow">Cómo gana</p><h2>Planes de juego</h2>' +
        doc.planes.map((p) => `<div class="plan"><h3>${C.e(p.titulo || "")}</h3>` +
          `<p>${p.texto || ""}${C.refs(p.fuentes, doc)}</p></div>`).join("") + "</section>");
    }

    if (doc.curva && Object.keys(doc.curva).length) {
      partes.push(
        '<section class="seccion"><p class="eyebrow">Punto de partida</p>' +
        "<h2>La curva del mazo</h2>" +
        `<p class="intro">${C.e(doc.subtitulo || "")}</p>` +
        `<div style="margin-top:26px">${C.curvaSvg(doc.curva, 140)}</div>` +
        '<p style="margin-top:26px;font-size:13px;color:var(--humo)">Valor de maná de los ' +
        "hechizos. Las tierras no cuentan.</p></section>");
    }

    for (const [bloque, lista] of C.bloques(doc)) {
      const combos = lista.map((s) => {
        const piezas = (s.piezas || []).map((n, i) =>
          (i ? '<span class="mas">+</span>' : "") + ficha(idx[n], n)).join("");
        const pasos = (s.pasos || []).map((p) => `<li>${p}</li>`).join("");
        let aviso = "";
        if (s.aviso) {
          aviso = `<div class="ojo"><b>Ojo</b>${s.aviso}</div>`;
        } else if (s.tipo === "conflicto") {
          aviso = '<div class="ojo"><b>Conflicto</b>Estas cartas se estorban entre sí: ' +
            "revisa el orden en que las juegas.</div>";
        }
        const citas = (s.citas || []).length || (s.fuentes || []).length
          ? '<ul class="citas">' + (s.citas || []).map((ct) =>
              `<li><b>${C.e(ct.carta)}</b>: <q>${C.e(ct.texto)}</q>` +
              `<span class="org">${C.e(ct.origen || "")}</span></li>`).join("") +
            ((s.fuentes || []).length ? `<li>Fuentes ${C.refs(s.fuentes, doc)}</li>` : "") +
            "</ul>" : "";
        return `<div class="combo ${C.e(s.tipo || "")}">` +
          `<div class="turno">${C.e(s.turno || "—")}</div>` +
          `<h3>${C.e(s.nombre || "")}<span class="que">${s.resumen || ""}</span></h3>` +
          `<div class="piezas">${piezas}</div><ol class="sec">${pasos}</ol>${aviso}${citas}</div>`;
      }).join("");
      partes.push(`<section class="seccion"><p class="eyebrow">${C.e(bloque)}</p>` +
        `<h2>${C.e(bloque)}</h2>` + combos + "</section>");
    }

    if ((doc.orden || []).length) {
      const filas = doc.orden.map((o) =>
        `<div class="combo"><div class="turno">${C.e(o.turno || "")}</div>` +
        `<h3>${C.e(o.carta || "")}<span class="que">${o.resumen || o.que || ""}</span></h3>` +
        `<div class="piezas">${ficha(idx[o.carta], o.carta)}</div>` +
        (o.porque ? `<p class="porque">${o.porque}</p>` : "") + "</div>").join("");
      partes.push('<section class="seccion"><p class="eyebrow">Secuencia</p>' +
        "<h2>Orden de aparición</h2>" + filas + "</section>");
    }

    const grupos = new Map();
    for (const c of doc.cartas || []) {
      const rol = c.rol || "sin clasificar";
      if (!grupos.has(rol)) grupos.set(rol, []);
      grupos.get(rol).push(c);
    }
    const rejillas = [...grupos.entries()].map(([rol, cartas]) =>
      `<div class="grupo"><p class="eyebrow">${C.e(C.NOMBRE_ROL[rol] || rol)} ` +
      `<span>${cartas.reduce((a, c) => a + (c.copias || 0), 0)}</span></p>` +
      `<div class="rejilla">${cartas.map((c) => ficha(c, c.nombre)).join("")}</div></div>`).join("");
    if (doc.tierras_guia) {
      const t = doc.tierras_guia;
      const filas = (t.detalle || []).map((d) => {
        const citas = (d.citas || []).length ? '<ul class="citas">' + d.citas.map((ct) =>
          `<li><b>${C.e(ct.carta)}</b>: <q>${C.e(ct.texto)}</q>` +
          `<span class="org">${C.e(ct.origen || "")}</span></li>`).join("") + "</ul>" : "";
        return `<div class="tierra">${ficha(idx[d.nombre] || d, d.nombre)}<div>` +
          `<h3>${C.e(d.nombre)}</h3>` +
          `<p><span class="k">Qué hace</span>${d.que_hace}</p>` +
          `<p><span class="k">Cómo jugarla</span>${d.como_jugarla}</p>${citas}</div></div>`;
      }).join("");
      const sec = (t.secuencia || []).length
        ? `<h3 style="margin-top:22px">En qué orden bajarlas</h3><ol class="sec">` +
          t.secuencia.map((x) => `<li>${x}</li>`).join("") + "</ol>" : "";
      partes.push('<section class="seccion"><p class="eyebrow">La base de maná</p><h2>Las tierras</h2>' +
        (t.resumen ? `<p class="intro">${t.resumen}${C.refs(t.fuentes, doc)}</p>` : "") +
        sec + filas + "</section>");
    }
    function barrasMull(m, st) {
      if (!(st.dist7 || []).length) return "";
      const [lo, hi] = m.tierras || [-1, -1];
      const max = Math.max(...st.dist7);
      const b = st.dist7.map((p, k) => {
        const ok = k >= lo && k <= hi;
        return `<span style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;` +
          `width:34px;font-family:var(--cond);font-size:11px;color:${ok ? "var(--tinta)" : "var(--humo)"}">` +
          `${Math.round(p * 100)}%<b style="display:block;width:24px;height:${Math.round(60 * p / max)}px;` +
          `background:${ok ? "#3E6B3A" : "var(--lin)"};margin-top:2px"></b>${k}</span>`;
      }).join("");
      return `<div style="margin-top:16px"><div style="display:flex;gap:4px;align-items:flex-end;height:92px">${b}</div>` +
        `<p style="margin:4px 0 0;font-size:12px;color:var(--humo)">Cuántas tierras trae la mano de 7 ` +
        `(en verde, las que te quedas). Si la mano tiene menos o más, mira los criterios de arriba.</p></div>`;
    }
    if (doc.mulligan) {
      const m = doc.mulligan, st = m.estadisticas || {};
      const li = (l) => (l || []).map((it) =>
        `<li>${typeof it === "string" ? it : (it.texto || "")}</li>`).join("");
      const pct = (p) => `${Math.round(p * 100)} %`;
      const datos = [];
      if (st.en_rango_7 !== undefined) {
        datos.push(`Mano de 7 con ${m.tierras[0]}–${m.tierras[1]} tierras: <b>${pct(st.en_rango_7)}</b>; ` +
          `tras mulligan a 6: <b>${pct(st.en_rango_6)}</b>.`);
      }
      for (const k of st.claves || []) datos.push(`${C.e(k.nombre)}: <b>${pct(k.p7)}</b> en la mano de 7.`);
      partes.push('<section class="seccion"><p class="eyebrow">Antes de empezar</p><h2>Mulligan</h2>' +
        (m.resumen ? `<p class="intro">${m.resumen}${C.refs(m.fuentes, doc)}</p>` : "") +
        '<div class="veredicto"><div class="cols">' +
        `<div><h4>Quédate</h4><ul>${li(m.quedarse)}</ul></div>` +
        `<div><h4>Mulligan</h4><ul>${li(m.mulligan)}</ul></div></div>` +
        barrasMull(m, st) +
        (datos.length ? `<p style="margin:12px 0 0;font-size:13px;color:var(--humo)">${datos.join(" ")} ` +
          `Calculado con ${st.tierras} tierras en ${st.cartas} cartas.</p>` : "") +
        (m.tras_mulligan ? `<div class="ojo"><b>Si haces mulligan</b>${m.tras_mulligan}</div>` : "") +
        "</div></section>");
    }
    if ((doc.mejoras || []).length) {
      const lado = (titulo, lista, signo) =>
        `<div class="lado"><h4>${titulo}</h4><div class="rejilla">` +
        lista.map((x) => {
          const f = ficha(Object.assign({}, idx[x.carta] || {}, x), x.carta);
          return f.replace(/<span class="n">[^]*?<\/span>/, "")
            .replace('<figure class="c">',
              `<figure class="c"><span class="n">${signo}${x.copias}<small>×</small></span>`);
        }).join("") + "</div></div>";
      partes.push('<section class="seccion"><p class="eyebrow">Si quieres afinarlo</p>' +
        "<h2>Mejoras propuestas</h2>" +
        '<p class="intro">Solo cambios muy claros o muy razonables. Las cartas que entran son ' +
        `legales${doc.formato ? " en " + C.e(doc.formato) : ""} según Scryfall y el mazo queda ` +
        "con el mismo número de cartas.</p>" +
        doc.mejoras.map((m) => {
          const citas = (m.citas || []).length || (m.fuentes || []).length
            ? '<ul class="citas">' + (m.citas || []).map((ct) =>
                `<li><b>${C.e(ct.carta)}</b>: <q>${C.e(ct.texto)}</q>` +
                `<span class="org">${C.e(ct.origen || "")}</span></li>`).join("") +
              ((m.fuentes || []).length ? `<li>Fuentes ${C.refs(m.fuentes, doc)}</li>` : "") +
              "</ul>" : "";
          return `<div class="mejora"><h3>${C.e(m.titulo || "")}` +
            `<span class="nivel ${C.e(m.nivel || "")}">${C.e(m.nivel || "")}</span></h3>` +
            `<div class="cambio">${lado("Sale", m.sale || [], "−")}<span class="flecha">→</span>` +
            `${lado("Entra", m.entra || [], "+")}</div><p>${m.motivo || ""}</p>` +
            (m.aviso ? `<div class="ojo"><b>Ojo</b>${m.aviso}</div>` : "") + citas + "</div>";
        }).join("") + "</section>");
    }
    if ((doc.reglas_oro || []).length) {
      partes.push('<section class="seccion"><p class="eyebrow">Para no olvidar</p>' +
        '<h2>Reglas de oro</h2><ol class="sec" style="margin-top:18px">' +
        doc.reglas_oro.map((r) => typeof r === "string" ? `<li>${r}</li>` :
          `<li><b>${r.texto || ""}</b>${r.porque ? `<p class="porque">${r.porque}</p>` : ""}</li>`).join("") +
        "</ol></section>");
    }
    partes.push('<section class="seccion"><p class="eyebrow">Referencia</p>' +
      "<h2>El mazo completo</h2>" + rejillas + "</section>");

    if (doc.arena) {
      partes.push('<section class="seccion"><p class="eyebrow">Para jugarlo</p><h2>El mazo para Arena</h2>' +
        '<p class="intro">Copia la lista y pégala en MTG Arena: Mazos → Importar.</p>' +
        '<button type="button" class="copiar" onclick="navigator.clipboard &amp;&amp; ' +
        'navigator.clipboard.writeText(document.getElementById(\'arena-txt\').textContent)' +
        '.then(()=>{this.textContent=\'Copiado\'})">Copiar lista</button>' +
        `<pre id="arena-txt" class="arena">${C.e(doc.arena)}</pre></section>`);
    }
    const fuentesHtml = (doc.fuentes || []).length
      ? '<section class="seccion"><p class="eyebrow">De dónde sale</p><h2>Fuentes</h2>' +
        '<ol class="fuentes">' + doc.fuentes.map((f) =>
          `<li><a href="${C.e(f.url)}" target="_blank" rel="noopener">${C.e(f.titulo || f.url)}</a></li>`)
          .join("") + "</ol></section>" : "";
    return `<header><div class="sol"></div><div class="wrap">
<p class="eyebrow">${C.e(doc.subtitulo || "")}</p>
<h1>${C.e(doc.titulo || "")}<br><em>guía de sinergias</em></h1>
<p class="dek">Cada jugada del mazo con sus cartas a la vista y el orden en que se ejecuta.
Pasa el ratón por encima de cualquier carta para verla grande.</p>
<p class="firma">${C.firma(doc)}</p>
</div></header><div class="wrap">${partes.join("")}${fuentesHtml}${C.pie(doc)}</div>`;
  }

  global.ForjaGuia = {
    css: CSS,
    cuerpo,
    montar: (doc) => C.montar(CSS, cuerpo(doc)),
  };
})(typeof window !== "undefined" ? window : globalThis);
