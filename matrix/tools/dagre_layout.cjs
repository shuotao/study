// dagre 版面橋接(MIT dagre 0.8.5,裝在 N/vendor/dagre;不執行任何外部 CLI)
// stdin: {"rankdir":"LR|TB","nodes":[{"id","w","h"}],"edges":[{"from","to"}]}
// stdout: {"nodes":{id:{x,y}},"edges":[{"from","to","points":[[x,y]...]}],"w","h"}
const dagre = require(require("path").join(__dirname, "../vendor/dagre/node_modules/dagre"));
let s = ""; process.stdin.on("data", d => s += d).on("end", () => {
  const spec = JSON.parse(s), g = new dagre.graphlib.Graph({ multigraph: true });
  g.setGraph({ rankdir: spec.rankdir || "LR", nodesep: 32, ranksep: 56, marginx: 24, marginy: 24 });
  g.setDefaultEdgeLabel(() => ({}));
  spec.nodes.forEach(n => g.setNode(n.id, { width: n.w, height: n.h }));
  spec.edges.forEach((e, i) => g.setEdge(e.from, e.to, { width: e.lw || 0, height: e.lw ? 20 : 0 }, "e" + i));
  dagre.layout(g);
  const out = { nodes: {}, edges: [], w: g.graph().width, h: g.graph().height };
  g.nodes().forEach(id => { const n = g.node(id); out.nodes[id] = { x: n.x - n.width / 2, y: n.y - n.height / 2 }; });
  spec.edges.forEach((e, i) => { const ed = g.edge(e.from, e.to, "e" + i); out.edges.push({ from: e.from, to: e.to, points: ed.points.map(p => [p.x, p.y]) }); });
  process.stdout.write(JSON.stringify(out));
});
