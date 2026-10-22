// III 追查與檢核：反白 → 註記／問 Claude／Google；註記存在瀏覽器（localStorage），不改原文。
// CTX 由 render_ii_iii.py 注入：{key, title, speaker, run}
(() => {
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const para = id => document.getElementById(id);
const ptext = id => (para(id)?.textContent || '').replace(/^p\d{4}/, '').trim();
let A = []; try { A = JSON.parse(localStorage.getItem(CTX.key) || '[]'); } catch (e) { A = []; }
const save = () => { localStorage.setItem(CTX.key, JSON.stringify(A)); $('#ann-n').textContent = A.length; $('#ann-empty').hidden = A.length > 0; };

// ── 分頁 ──
const tabs = $$('.tabs button');
function tab(name) { tabs.forEach(b => b.setAttribute('aria-selected', b.dataset.p === name)); $$('.pane').forEach(p => p.hidden = p.id !== 'pane-' + name); }
tabs.forEach(b => b.onclick = () => tab(b.dataset.p));

// ── 研究簡報（帶出去的文字） ──
function brief(quote, pid, extra) {
  const ctx = ptext(pid).slice(0, 320);
  return `我正在學習〈${CTX.title}〉（${CTX.speaker}）。\n講者原話（段落 ${pid}）：「${quote}」\n上下文：「${ctx}」\n` +
    (extra ? `我想深入的點：${extra}\n` : '') +
    `\n請幫我往外查這一點：\n1. 這句話牽涉的概念或技術是什麼，用一兩句說明。\n2. 可查證的外部資料：每一點附網址與發布日期，優先官方文件與原始來源。\n3. 外部資料和講者說法是一致、補充，還是矛盾？\n查不到就直接說查不到，不要推測。`;
}
const claude = q => window.open('https://claude.ai/new?q=' + encodeURIComponent(q), '_blank', 'noopener');
const google = q => window.open('https://www.google.com/search?q=' + encodeURIComponent(q.slice(0, 80)), '_blank', 'noopener');

// ── 在原文標出註記 ──
function markOne(a) {
  const p = para(a.pid); if (!p || $(`mark[data-id="${a.id}"]`)) return;
  const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT); let n;
  while ((n = w.nextNode())) {
    if (n.parentElement.closest('.pid,.aud-tag')) continue;
    const i = n.data.indexOf(a.quote); if (i < 0) continue;
    const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + a.quote.length);
    const m = document.createElement('mark'); m.className = 'ann-m'; m.dataset.id = a.id; m.title = '我的註記';
    r.surroundContents(m); m.onclick = () => openAnn(a.id); return;
  }
  p.classList.add('has-ann');   // 跨粗體等標籤時：整段標示
}
function unmark(id) { const m = $(`mark[data-id="${id}"]`); if (m) m.replaceWith(...m.childNodes); }

// ── 註記卡 ──
const REL = ['未定', '一致', '補充', '矛盾'];
function card(a) {
  const d = new Date(a.t);
  return `<div class="ann" id="ann-${a.id}"><blockquote data-pid="${a.pid}">「${esc(a.quote)}」</blockquote>
<div class="src">原文 ${a.pid}，${d.getMonth() + 1}/${d.getDate()} 記</div>
<label>我的筆記</label><textarea data-f="note" placeholder="為什麼在意這句？想查什麼？">${esc(a.note || '')}</textarea>
<label>查回來的重點（貼上）</label><textarea data-f="found" placeholder="從 Claude 或搜尋結果貼回來的重點">${esc(a.found || '')}</textarea>
<label>來源網址</label><input data-f="url" type="url" value="${esc(a.url || '')}" placeholder="https://">
<label>和講者說法的關係</label><select data-f="rel">${REL.map(r => `<option${(a.rel || '未定') === r ? ' selected' : ''}>${r}</option>`).join('')}</select>
<div class="row"><button type="button" data-do="claude">問 Claude</button><button type="button" data-do="google">Google</button><button type="button" data-do="del">刪除</button></div></div>`;
}
function render() {
  $('#anns').innerHTML = A.slice().reverse().map(card).join('');
  $$('#anns .ann').forEach(el => {
    const a = A.find(x => 'ann-' + x.id === el.id);
    $$('[data-f]', el).forEach(f => f.oninput = f.onchange = () => { a[f.dataset.f] = f.value; save(); });
    $('blockquote', el).onclick = () => go(a.pid, a.id);
    $$('[data-do]', el).forEach(b => b.onclick = () => {
      if (b.dataset.do === 'claude') claude(brief(a.quote, a.pid, a.note));
      if (b.dataset.do === 'google') google(a.quote);
      if (b.dataset.do === 'del') { A = A.filter(x => x.id !== a.id); unmark(a.id); save(); render(); }
    });
  });
  save();
}
function openAnn(id) { tab('notes'); const el = document.getElementById('ann-' + id); if (!el) return; el.scrollIntoView({block: 'nearest'}); el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 1200); }
function go(pid, id) { const p = para(pid); if (!p) return; p.scrollIntoView({behavior: 'smooth', block: 'center'}); p.classList.add('hit'); setTimeout(() => p.classList.remove('hit'), 1600); }
function add(quote, pid) { const a = {id: Date.now().toString(36), pid, quote, t: Date.now()}; A.push(a); markOne(a); render(); openAnn(a.id); return a; }

// ── 反白工具列 ──
const bar = $('#selbar'); let cur = null;
function sel() {
  const s = getSelection(); if (!s.rangeCount || s.isCollapsed) return null;
  const r = s.getRangeAt(0), q = s.toString().replace(/\s+/g, ' ').trim();
  const p1 = r.startContainer.parentElement?.closest('.text p[id]'), p2 = r.endContainer.parentElement?.closest('.text p[id]');
  if (!q || q.length < 2 || !p1 || p1 !== p2) return null;    // 一次只取同一段內的文字
  return {q, pid: p1.id, rect: r.getBoundingClientRect()};
}
function showBar() {
  cur = sel(); if (!cur) { bar.style.display = 'none'; return; }
  bar.style.display = 'flex';
  const top = cur.rect.top - bar.offsetHeight - 8;
  bar.style.top = (top < 60 ? cur.rect.bottom + 8 : top) + 'px';
  bar.style.left = Math.max(8, Math.min(innerWidth - bar.offsetWidth - 8, cur.rect.left + cur.rect.width / 2 - bar.offsetWidth / 2)) + 'px';
}
document.addEventListener('mouseup', e => { if (!bar.contains(e.target)) setTimeout(showBar, 0); });
document.addEventListener('keyup', e => { if (e.shiftKey || e.key === 'Escape') setTimeout(e.key === 'Escape' ? () => bar.style.display = 'none' : showBar, 0); });
addEventListener('scroll', () => { bar.style.display = 'none'; }, {passive: true});
$$('button', bar).forEach(b => b.onmousedown = e => e.preventDefault());
$$('button', bar).forEach(b => b.onclick = () => {
  if (!cur) return; const {q, pid} = cur;
  if (b.dataset.a === 'note') add(q, pid);
  if (b.dataset.a === 'claude') { add(q, pid); claude(brief(q, pid)); }
  if (b.dataset.a === 'google') google(q);
  if (b.dataset.a === 'copy') navigator.clipboard?.writeText(`「${q}」——${CTX.speaker}，〈${CTX.title}〉，原文 ${pid}`);
  bar.style.display = 'none'; getSelection().removeAllRanges();
});

// ── 匯出（一次性的學習筆記；原文以 II 為準） ──
$('#ann-export').onclick = () => {
  const md = `# 註記：${CTX.title}\n\n> 一次性的學習筆記，原文以 ii.html 為準；外部資料只代表查到的來源，不是講者說的。\n\n` +
    A.map(a => `## 「${a.quote}」\n\n- 原文：${a.pid}（${location.href.replace(/iii\.html.*/, 'ii.html')}#${a.pid}）\n- 我的筆記：${a.note || ''}\n- 查回來的重點：${(a.found || '').replace(/\n/g, ' ')}\n- 來源：${a.url || ''}\n- 和講者說法：${a.rel || '未定'}\n`).join('\n');
  const u = URL.createObjectURL(new Blob([md], {type: 'text/markdown'}));
  const l = Object.assign(document.createElement('a'), {href: u, download: `${CTX.run}-註記.md`}); l.click(); URL.revokeObjectURL(u);
};
$('#ann-clear').onclick = () => { if (!A.length) return; A.forEach(a => unmark(a.id)); $$('.has-ann').forEach(p => p.classList.remove('has-ann')); A = []; render(); };

// ── 深挖題目 ──
$$('.topics li').forEach(li => {
  const refs = li.dataset.refs.split(' ').filter(Boolean);
  $('.t-show', li).onclick = () => { $$('.text p.hit').forEach(p => p.classList.remove('hit')); refs.forEach(r => para(r)?.classList.add('hit')); para(refs[0])?.scrollIntoView({behavior: 'smooth', block: 'center'}); };
  $('.t-ask', li).onclick = () => claude(brief(($('q', li)?.textContent || ptext(refs[0]).slice(0, 60)), refs[0] || '', $('.tt', li).textContent));
});

// ── 主張：搜尋＋篩選 ──
const L = $$('#claims li'), P = $$('.text p[id]'); let f = '';
function apply() {
  if (!$('#q') || !L.length) return;
  const q = $('#q').value.trim(); let n = 0;
  L.forEach(li => { const ok = (!f || li.dataset.type === f) && (!q || li.textContent.includes(q)); li.hidden = !ok; n += ok; });
  P.forEach(p => p.classList.toggle('hit', !!q && p.textContent.includes(q)));
  const m = q ? P.filter(p => p.textContent.includes(q)).length : 0;
  $('#count').textContent = `顯示 ${n} 條` + (q ? `；原文有 ${m} 段含「${q}」（已標亮）` : '');
}
$$('.chips button').forEach(b => b.onclick = () => { f = b.dataset.f; $$('.chips button').forEach(x => x.classList.toggle('on', x === b)); apply(); });
if ($('#q')) $('#q').oninput = apply;
L.forEach(li => li.onclick = ev => { if (ev.target.closest('a')) return; L.forEach(x => x.classList.toggle('on', x === li)); P.forEach(p => p.classList.remove('hit'));
  const ids = li.dataset.anchors.split(' '); ids.forEach(i => para(i)?.classList.add('hit')); para(ids[0])?.scrollIntoView({behavior: 'smooth', block: 'center'}); });

A.forEach(markOne); render(); apply(); tab(A.length ? 'notes' : 'topics');
})();
