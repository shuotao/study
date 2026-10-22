// IV 廣度：三層由遠到近 —— 場次網（環）→ 兩場對照（雙欄連線）→ 卡片圖譜（力導向，Obsidian local graph 式）。
// 資料由 render_iv.py 注入 window.IV = {here, sessions:[{run,label,title}], cards:[{id,run,k,h}], links:[{a,b,t,why}], colors}
(() => {
const D = window.IV, $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const NS = 'http://www.w3.org/2000/svg';
// 其他場次的 IV 網址：預設 ../<run>/iv.html；書裡由 book.py 注入 window.IVBASE 改寫（不在書裡的場次指向已出版網址）
const IVURL = (run, k) => { const b = (window.IVBASE || {})[run] ?? `../${run}/iv.html`; return b.startsWith('http') ? b : b + '#' + k; };   // 書外（已出版）不加 #K
const EXT = new Set(window.IVEXT || []);
const el = (tag, attrs = {}, txt) => { const x = document.createElementNS(NS, tag); for (const k in attrs) x.setAttribute(k, attrs[k]); if (txt != null) x.textContent = txt; return x; };
const card = Object.fromEntries(D.cards.map(c => [c.id, c])), runOf = id => card[id].run;
const S = Object.fromEntries(D.sessions.map(s => [s.run, s]));
const mine = D.links.filter(l => runOf(l.a) === D.here || runOf(l.b) === D.here);
const other = l => runOf(l.a) === D.here ? l.b : l.a, self = l => runOf(l.a) === D.here ? l.a : l.b;
const cnt = {}; mine.forEach(l => { const r = runOf(other(l)); cnt[r] = (cnt[r] || 0) + 1; });
const ring = D.sessions.filter(s => s.run !== D.here).sort((a, b) => (cnt[b.run] || 0) - (cnt[a.run] || 0) || a.label.localeCompare(b.label));
let pick = ring.find(s => cnt[s.run])?.run || ring[0]?.run;

// ── 第 1 層：場次網 ──
function drawRing() {
  const box = $('#ring'), svg = $('svg', box), W = box.clientWidth, H = Math.min(560, Math.max(440, W * 0.62));
  if (W < 600) {                  // 手機：環形放不下，改成依關聯數排序的清單
    svg.style.display = 'none'; let ul = $('ul.rk', box); if (!ul) { ul = document.createElement('ul'); ul.className = 'rk'; box.appendChild(ul); }
    const mx = Math.max(1, ...ring.map(s => cnt[s.run] || 0));
    ul.innerHTML = ring.map(s => `<li><button type="button" data-run="${s.run}" class="${s.run === pick ? 'on' : ''}"><b>${s.label}${EXT.has(s.run) ? '（書外）' : ''}</b><span class="bar" style="width:${(cnt[s.run] || 0) / mx * 100}%"></span><span>${cnt[s.run] ? cnt[s.run] + ' 條' : '沒有關聯'}</span></button></li>`).join('');
    $$('button', ul).forEach(b => b.onclick = () => { pick = b.dataset.run; drawRing(); drawPair(); });
    return;
  }
  svg.style.display = ''; $('ul.rk', box)?.remove();
  svg.setAttribute('width', W); svg.setAttribute('height', H); svg.innerHTML = '';
  const cx = W / 2, cy = H / 2, R = Math.min(W * (W < 600 ? 0.22 : 0.36), H / 2 - 104), pos = {};
  ring.forEach((s, i) => { const a = -Math.PI / 2 + 2 * Math.PI * i / ring.length; pos[s.run] = [cx + R * Math.cos(a), cy + R * Math.sin(a), a]; });
  // 其他場次彼此之間的關聯：細弦（看全局結構）
  const pair = {}; D.links.forEach(l => { const x = runOf(l.a), y = runOf(l.b); if (x === D.here || y === D.here) return; const k = [x, y].sort().join('|'); pair[k] = (pair[k] || 0) + 1; });
  for (const k in pair) { const [x, y] = k.split('|'); if (!pos[x] || !pos[y]) continue;
    svg.appendChild(el('path', {d: (() => { const mx = (pos[x][0] + pos[y][0]) / 2, my = (pos[x][1] + pos[y][1]) / 2; return `M${pos[x][0]},${pos[x][1]} Q${mx + (cx - mx) * .45},${my + (cy - my) * .45} ${pos[y][0]},${pos[y][1]}`; })(), class: 'chord', 'data-a': x, 'data-b': y, 'stroke-width': Math.min(4, .8 + pair[k] * .5)})); }
  ring.forEach(s => { const n = cnt[s.run] || 0, [x, y] = pos[s.run];
    if (n) svg.appendChild(el('line', {x1: cx, y1: cy, x2: x, y2: y, class: 'spoke' + (s.run === pick ? ' on' : ''), 'stroke-width': 1.5 + Math.sqrt(n) * 1.8, 'data-run': s.run})); });
  ring.forEach(s => { const n = cnt[s.run] || 0, [x, y, a] = pos[s.run], r = 9 + Math.sqrt(n) * 7;
    const g = el('g', {class: 'sn' + (n ? '' : ' zero') + (s.run === pick ? ' on' : ''), tabindex: 0, role: 'button', 'aria-label': `${s.label}，${n} 條關聯`, 'data-run': s.run});
    g.appendChild(el('circle', {cx: x, cy: y, r}));
    const out = Math.cos(a) >= 0 ? 1 : -1, lx = x + out * (r + 8), anchor = Math.abs(Math.cos(a)) < .25 ? 'middle' : (out > 0 ? 'start' : 'end');
    const ly = Math.abs(Math.cos(a)) < .25 ? (Math.sin(a) > 0 ? y + r + 20 : y - r - 28) : y - 2;
    g.appendChild(el('text', {x: Math.abs(Math.cos(a)) < .25 ? x : lx, y: ly, 'text-anchor': anchor, class: 'sl'}, s.label + (EXT.has(s.run) ? '（書外）' : '')));
    g.appendChild(el('text', {x: Math.abs(Math.cos(a)) < .25 ? x : lx, y: ly + 18, 'text-anchor': anchor, class: 'sc'}, n ? `${n} 條` : '沒有關聯'));
    const t = el('title'); t.textContent = s.title; g.appendChild(t);
    g.onclick = () => { pick = s.run; drawRing(); drawPair(); $('#pair').scrollIntoView({behavior: 'smooth', block: 'nearest'}); };
    g.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); g.onclick(); } };
    g.onmouseenter = () => $$('.chord', svg).forEach(c => c.classList.toggle('hl', c.dataset.a === s.run || c.dataset.b === s.run));
    g.onmouseleave = () => $$('.chord', svg).forEach(c => c.classList.remove('hl'));
    svg.appendChild(g); });
  const c = el('g', {class: 'center'}); c.appendChild(el('circle', {cx, cy, r: 44}));
  c.appendChild(el('text', {x: cx, y: cy + 5, 'text-anchor': 'middle'}, S[D.here].label.split(' ')[0])); svg.appendChild(c);
}

// ── 第 2 層：兩場對照 ──
function drawPair() {
  const P = $('#pair'), s = S[pick], L = mine.filter(l => runOf(other(l)) === pick);
  $('#pair-h').innerHTML = `${S[D.here].label.split(' ')[0]} 和 <b>${s.label}${EXT.has(s.run) ? '（書外，已出版）' : ''}</b>（${s.title}）：${L.length ? L.length + ' 條關聯' : '沒有找到真正相關的重點'}`;
  const col = (run, here) => `<div class="col"><h3>${S[run].label}${EXT.has(run) ? '（書外）' : ''}</h3>` + D.cards.filter(c => c.run === run).map(c => {
    const on = L.some(l => l.a === c.id || l.b === c.id);
    return `<a class="node${here ? ' here' : ''}${on ? '' : ' dim'}" data-id="${c.id}" href="${here ? '#' + c.k : IVURL(c.run, c.k)}"><b>${c.k}</b>${c.h}</a>`; }).join('') + '</div>';
  $('.map', P).innerHTML = '<svg aria-hidden="true"></svg>' + col(D.here, true) + col(pick, false);
  const M = $('.map', P), sv = $('svg', M), r = M.getBoundingClientRect();
  L.forEach(l => { const a = $(`.node[data-id="${CSS.escape(self(l))}"]`, M), b = $(`.node[data-id="${CSS.escape(other(l))}"]`, M); if (!a || !b) return;
    const p = a.getBoundingClientRect(), q = b.getBoundingClientRect(), x1 = p.right - r.left, y1 = p.top + p.height / 2 - r.top, x2 = q.left - r.left, y2 = q.top + q.height / 2 - r.top, m = (x1 + x2) / 2;
    sv.appendChild(el('path', {d: `M${x1},${y1} C${m},${y1} ${m},${y2} ${x2},${y2}`, stroke: D.colors[l.t], 'stroke-width': 2.4, fill: 'none'})); });
  $('#pair-list').innerHTML = L.map(l => `<li><span class="rt" style="--c:${D.colors[l.t]}">${l.t}</span><b>${card[self(l)].k}</b> ${card[self(l)].h} ↔ <a href="${IVURL(pick, card[other(l)].k)}"><b>${card[other(l)].k}</b> ${card[other(l)].h}</a><p>${l.why}</p></li>`).join('');
}

// ── 第 3 層：卡片圖譜（力導向；Obsidian local graph 的深度 1／2） ──
const RUNS = D.sessions.map(s => s.run), hue = run => `hsl(${(RUNS.indexOf(run) * 360 / RUNS.length + 15) % 360} 38% 46%)`;
function drawGraph(depth) {
  const box = $('#graph'), svg = $('svg', box), W = box.clientWidth, H = 620;
  svg.setAttribute('width', W); svg.setAttribute('height', H); svg.innerHTML = '';
  let ids = new Set(D.cards.filter(c => c.run === D.here).map(c => c.id));
  for (let d = 0; d < depth; d++) { const nx = new Set(ids); D.links.forEach(l => { if (ids.has(l.a)) nx.add(l.b); if (ids.has(l.b)) nx.add(l.a); }); ids = nx; }
  const runsIn = [...new Set([...ids].map(runOf))];
  const N = [...ids].map((id, i) => { const ri = runsIn.indexOf(runOf(id)), ang = 2 * Math.PI * ri / runsIn.length, rr = runOf(id) === D.here ? 0 : 220;
    return {id, x: W / 2 + rr * Math.cos(ang) + 40 * Math.cos(i * 2.4), y: H / 2 + rr * 0.8 * Math.sin(ang) + 40 * Math.sin(i * 2.4), vx: 0, vy: 0}; });
  const ix = Object.fromEntries(N.map((n, i) => [n.id, i])), E = D.links.filter(l => l.a in ix && l.b in ix);
  for (let it = 0; it < 500; it++) {               // 靜態排好再畫：不做持續晃動的動畫
    const cool = 1 - it / 500, cen = {};
    N.forEach(n => { const r = runOf(n.id); (cen[r] = cen[r] || {x: 0, y: 0, c: 0}); cen[r].x += n.x; cen[r].y += n.y; cen[r].c++; });
    for (let i = 0; i < N.length; i++) for (let j = i + 1; j < N.length; j++) {        // 互斥：避免重疊
      const a = N[i], b = N[j], dx = a.x - b.x, dy = a.y - b.y, d2 = Math.max(dx * dx + dy * dy, 400), f = 1800 / d2;
      a.vx += dx * f / Math.sqrt(d2) * 10; a.vy += dy * f / Math.sqrt(d2) * 10; b.vx -= dx * f / Math.sqrt(d2) * 10; b.vy -= dy * f / Math.sqrt(d2) * 10; }
    E.forEach(l => { const a = N[ix[l.a]], b = N[ix[l.b]], dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1, f = (d - 140) * .03;   // 關聯：彈簧
      a.vx += dx / d * f; a.vy += dy / d * f; b.vx -= dx / d * f; b.vy -= dy / d * f; });
    E.forEach(l => { const a = N[ix[l.a]], b = N[ix[l.b]], vx = b.x - a.x, vy = b.y - a.y, L2 = vx * vx + vy * vy || 1;   // 點避開不相連的線：避免線穿過標籤被誤讀成相連
      N.forEach(n => { if (n === a || n === b) return; const t = Math.max(0, Math.min(1, ((n.x - a.x) * vx + (n.y - a.y) * vy) / L2));
        const px = a.x + t * vx, py = a.y + t * vy, dx = n.x - px, dy = n.y - py, d = Math.hypot(dx, dy) || .1;
        if (d < 34) { const f = (34 - d) * .25; n.vx += dx / d * f; n.vy += dy / d * f; } }); });
    N.forEach(n => { const c = cen[runOf(n.id)];                                     // 同場次向自己的群中心靠
      n.vx += (c.x / c.c - n.x) * .03 + (W / 2 - n.x) * .006; n.vy += (c.y / c.c - n.y) * .03 + (H / 2 - n.y) * .006;
      n.vx = Math.max(-30, Math.min(30, n.vx)); n.vy = Math.max(-30, Math.min(30, n.vy));
      n.x += n.vx * cool; n.y += n.vy * cool; n.vx *= .55; n.vy *= .55;
      n.x = Math.max(80, Math.min(W - 80, n.x)); n.y = Math.max(34, Math.min(H - 24, n.y)); });
  }
  const gE = el('g'), gN = el('g'), gL = el('g', {class: 'labels'}); svg.append(gE, gN, gL);
  E.forEach(l => gE.appendChild(el('line', {x1: N[ix[l.a]].x, y1: N[ix[l.a]].y, x2: N[ix[l.b]].x, y2: N[ix[l.b]].y, stroke: D.colors[l.t], 'stroke-width': 1.8, 'data-a': l.a, 'data-b': l.b})));
  N.forEach(n => { const c = card[n.id], here = c.run === D.here;
    const g = el('g', {class: 'gn' + (here ? ' here' : ''), tabindex: 0, 'data-id': n.id});
    g.appendChild(el('circle', {cx: n.x, cy: n.y, r: here ? 15 : 7, fill: here ? 'var(--accent)' : hue(c.run)}));
    if (here) g.appendChild(el('text', {x: n.x, y: n.y + 5, 'text-anchor': 'middle', class: 'gk'}, c.k));   // 這一場的卡：K 編號寫在圓內，一定看得到
    const t = el('title'); t.textContent = `${S[c.run].label} ${c.k}：${c.h}`; g.appendChild(t);
    const nb = new Set([n.id]); E.forEach(l => { if (l.a === n.id) nb.add(l.b); if (l.b === n.id) nb.add(l.a); });
    g.onmouseenter = g.onfocus = () => { $$('.gn', gN).forEach(x => x.classList.toggle('dim', !nb.has(x.dataset.id))); $$('line', gE).forEach(x => x.style.opacity = x.dataset.a === n.id || x.dataset.b === n.id ? 1 : .08);
      $$('.gl', gL).forEach(x => x.classList.toggle('show', nb.has(x.dataset.id)));
      $('#g-info').innerHTML = `<b>${S[c.run].label}${EXT.has(c.run) ? '（書外）' : ''} ${c.k}</b> ${c.h}`; };
    g.onmouseleave = g.onblur = () => { $$('.gn', gN).forEach(x => x.classList.remove('dim')); $$('line', gE).forEach(x => x.style.opacity = 1); $$('.gl', gL).forEach(x => x.classList.remove('show')); };
    g.onclick = () => location.href = here ? '#' + c.k : IVURL(c.run, c.k);
    gN.appendChild(g); });
  // 標籤擺放：上／下／右／左四個位置，取第一個「不壓到不相連的線、不疊到別的標籤或點、不出畫布」的；
  // 都不行就只在滑過時顯示（避免線穿過標籤被誤讀成相連）。由 k_check iv-graph 幾何閘門驗證。
  const seg = E.map(l => ({a: l.a, b: l.b, x1: N[ix[l.a]].x, y1: N[ix[l.a]].y, x2: N[ix[l.b]].x, y2: N[ix[l.b]].y}));
  const hit = (r, s) => { const inR = (x, y) => x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h;
    if (inR(s.x1, s.y1) || inR(s.x2, s.y2)) return true;
    const X = (ax, ay, bx, by, cx, cy, dx, dy) => { const d = (bx - ax) * (dy - cy) - (by - ay) * (dx - cx); if (!d) return false;
      const u = ((cx - ax) * (dy - cy) - (cy - ay) * (dx - cx)) / d, v = ((cx - ax) * (by - ay) - (cy - ay) * (bx - ax)) / d; return u >= 0 && u <= 1 && v >= 0 && v <= 1; };
    const R = [[r.x, r.y, r.x + r.w, r.y], [r.x + r.w, r.y, r.x + r.w, r.y + r.h], [r.x, r.y + r.h, r.x + r.w, r.y + r.h], [r.x, r.y, r.x, r.y + r.h]];
    return R.some(e => X(s.x1, s.y1, s.x2, s.y2, ...e)); };
  const over = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  const placed = [], dots = N.map(n => { const r = runOf(n.id) === D.here ? 16 : 10; return {id: n.id, x: n.x - r, y: n.y - r, w: 2 * r, h: 2 * r}; });
  const deg = id => E.filter(l => l.a === id || l.b === id).length;
  [...N].sort((p, q) => (runOf(q.id) === D.here) - (runOf(p.id) === D.here) || deg(q.id) - deg(p.id)).forEach(n => {
    const c = card[n.id]; if (c.run === D.here) return;   // 這一場的卡已在圓內標 K 編號
    const txt = `${S[c.run].label.split(' ')[0]} ${c.k}` + (EXT.has(c.run) ? '（書外）' : '');
    const lab = el('text', {class: 'gl' + (c.run === D.here ? ' here' : ''), 'data-id': n.id}, txt); gL.appendChild(lab);
    const bb = lab.getBBox(), w = bb.width + 6, h = bb.height + 2;
    const cand = [];
    for (const k of [1, 1.8]) cand.push([n.x - w / 2, n.y - 13 * k - h], [n.x - w / 2, n.y + 12 * k], [n.x + 12 * k, n.y - h / 2], [n.x - 12 * k - w, n.y - h / 2],
      [n.x + 9 * k, n.y - 9 * k - h], [n.x + 9 * k, n.y + 9 * k], [n.x - 9 * k - w, n.y - 9 * k - h], [n.x - 9 * k - w, n.y + 9 * k]);
    const ok = cand.map(([x, y]) => ({x, y, w, h})).find(r => r.x >= 0 && r.y >= 0 && r.x + r.w <= W && r.y + r.h <= H
      && !seg.some(s => s.a !== n.id && s.b !== n.id && hit(r, s)) && !placed.some(p => over(p, r)) && !dots.some(d => d.id !== n.id && over(d, r)));
    const r = ok || {x: n.x - w / 2, y: n.y - 14 - h, w, h};
    lab.setAttribute('x', r.x + 3); lab.setAttribute('y', r.y + h - 5);
    if (ok) placed.push(r); else lab.classList.add('hide');
  });
  $('#g-count').textContent = `${N.length} 張卡、${E.length} 條關聯、來自 ${new Set(N.map(n => runOf(n.id))).size} 場`;
}

// ── 分頁 ──
let depth = 1;
function view(v) { $$('.vt button').forEach(b => b.setAttribute('aria-pressed', b.dataset.v === v)); $('#v-sessions').hidden = v !== 'sessions'; $('#v-graph').hidden = v !== 'graph';
  if (v === 'graph') drawGraph(depth); else { drawRing(); drawPair(); } }
$$('.vt button').forEach(b => b.onclick = () => view(b.dataset.v));
$$('.dp button').forEach(b => b.onclick = () => { depth = +b.dataset.d; $$('.dp button').forEach(x => x.setAttribute('aria-pressed', x === b)); drawGraph(depth); });
let rz; addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => view($('#v-graph').hidden ? 'sessions' : 'graph'), 150); });
(document.fonts?.ready || Promise.resolve()).then(() => view('sessions'));
})();
