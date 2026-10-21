/* Read-only layout: dependency depth runs left to right, independent of phase. */
function buildBoardGraph(board, minimumHeight = 108) {
  const width = 248, inset = 48, portStep = 14, trackStep = 14;
  const stagger = [0, 49, 98, 49], staggerHeight = Math.max(...stagger);
  const byId = new Map(board.tasks.map(task => [task.id, task]));
  const ranks = new Map();
  const rank = id => {
    if (!ranks.has(id)) {
      ranks.set(id, 0);
      ranks.set(id, Math.max(0, ...byId.get(id).depends_on.map(dep => rank(dep) + 1)));
    }
    return ranks.get(id);
  };
  board.tasks.forEach(task => rank(task.id));
  const levels = Array.from({length: Math.max(-1, ...ranks.values()) + 1}, () => []);
  board.tasks.forEach(task => levels[ranks.get(task.id)].push(task));
  levels.forEach(tasks => tasks.sort((a, b) => a.id.localeCompare(b.id)));
  const rows = Math.max(1, ...levels.map(tasks => tasks.length));
  const slots = new Map(), dependents = new Map(board.tasks.map(task => [task.id, []]));
  board.tasks.forEach(task => task.depends_on.forEach(id => dependents.get(id).push(task.id)));
  const assignSlots = tasks => tasks.forEach((task, index) =>
    slots.set(task.id, Math.floor((rows - tasks.length) / 2) + index));
  levels.forEach(assignSlots);
  // Stable neighbour ordering keeps parallel branches near their connections.
  for (let pass = 0; pass < 4; pass++) {
    const forward = pass % 2 === 0;
    for (const tasks of forward ? levels : [...levels].reverse()) {
      const score = task => {
        const neighbours = forward ? task.depends_on : dependents.get(task.id);
        return neighbours.length ? neighbours.reduce((sum, id) => sum + slots.get(id), 0)
          / neighbours.length : slots.get(task.id);
      };
      tasks.sort((a, b) => score(a) - score(b) || a.id.localeCompare(b.id));
      assignSlots(tasks);
    }
  }
  const tasks = [...board.tasks].sort((a, b) => a.id.localeCompare(b.id));
  const edges = tasks.flatMap(task => [...task.depends_on].sort().map(from => ({from, to: task.id})));
  const incoming = new Map(tasks.map(task => [task.id, []]));
  const outgoing = new Map(tasks.map(task => [task.id, []]));
  const gutters = levels.map(() => ({departures: [], adjacent: [], arrivals: []}));
  const bands = Array.from({length: rows}, () => []);
  const key = edge => JSON.stringify([edge.from, edge.to]);
  for (const edge of edges) {
    incoming.get(edge.to).push(edge);
    outgoing.get(edge.from).push(edge);
    const start = ranks.get(edge.from), end = ranks.get(edge.to);
    if (end === start + 1) gutters[start].adjacent.push(edge);
    else {
      gutters[start].departures.push(edge);
      gutters[end - 1].arrivals.push(edge);
      edge.band = Math.min(slots.get(edge.from), slots.get(edge.to));
      bands[edge.band].push(edge);
    }
  }
  const degree = Math.max(1, ...tasks.map(task => Math.max(
    incoming.get(task.id).length, outgoing.get(task.id).length)));
  const height = Math.max(minimumHeight, (degree - 1) * portStep + 28);
  const nodeHeight = task => task.external
    ? Math.max(76, (Math.max(incoming.get(task.id).length, outgoing.get(task.id).length) - 1) * portStep + 28)
    : height;
  const columnX = [inset], rail = new Map();
  for (let level = 0; level < levels.length; level++) {
    const gutter = gutters[level];
    // Each vertical segment owns a rail, including short adjacent links.
    const routes = [...gutter.departures, ...gutter.adjacent, ...gutter.arrivals];
    routes.forEach((edge, index) => rail.set(`${level}:${key(edge)}`,
      columnX[level] + width + 32 + index * trackStep));
    columnX.push(columnX[level] + width + Math.max(144, 64 + routes.length * trackStep));
  }
  const port = (links, endpoint) => {
    for (const [id, list] of links) {
      const portSlots = Math.floor((nodeHeight(byId.get(id)) - 28) / portStep) + 1;
      const other = endpoint === 'from' ? 'to' : 'from';
      list.sort((a, b) => slots.get(a[other]) - slots.get(b[other])
        || ranks.get(a[other]) - ranks.get(b[other]) || key(a).localeCompare(key(b)));
      list.forEach((edge, index) => {
        edge[`${endpoint}Offset`] = 14 + (Math.round((portSlots - list.length) / 2) + index) * portStep;
      });
    }
  };
  port(outgoing, 'from');
  port(incoming, 'to');
  const bandHeights = bands.map(links => {
    const ends = [];
    links.sort((a, b) => ranks.get(a.from) - ranks.get(b.from)
      || ranks.get(a.to) - ranks.get(b.to) || key(a).localeCompare(key(b)));
    for (const edge of links) {
      const start = ranks.get(edge.from), end = ranks.get(edge.to);
      const left = rail.get(`${start}:${key(edge)}`), right = rail.get(`${end - 1}:${key(edge)}`);
      let track = ends.findIndex(value => value + trackStep < left);
      if (track < 0) track = ends.length;
      ends[track] = right;
      edge.track = track;
    }
    return Math.max(96, 64 + ends.length * trackStep);
  });
  const rowY = [inset];
  bandHeights.forEach(gap => rowY.push(rowY.at(-1) + height + staggerHeight + gap));
  const nodes = new Map();
  levels.forEach((items, level) => items.forEach(task => nodes.set(task.id, {
    task, x: columnX[level], y: rowY[slots.get(task.id)] + stagger[level % stagger.length],
    width: task.external ? 180 : width, height: nodeHeight(task), level, slot: slots.get(task.id)
  })));
  for (const edge of edges) {
    const from = nodes.get(edge.from), to = nodes.get(edge.to);
    const x1 = from.x + from.width, y1 = from.y + edge.fromOffset;
    const x2 = to.x, y2 = to.y + edge.toOffset;
    const exit = rail.get(`${from.level}:${key(edge)}`);
    const entry = rail.get(`${to.level - 1}:${key(edge)}`);
    // Ports share a 14px grid; adjacent columns offset it by half a step.
    // This keeps parallel stubs at least 7px apart, beyond the crossing clearance.
    // Long links use interval-packed tracks below every card in their row.
    if (to.level === from.level + 1) {
      edge.points = [[x1, y1], [exit, y1], [exit, y2], [x2, y2]];
    } else {
      const corridor = rowY[edge.band] + height + staggerHeight + 32 + edge.track * trackStep;
      edge.points = [[x1, y1], [exit, y1], [exit, corridor], [entry, corridor], [entry, y2], [x2, y2]];
    }
    edge.path = edge.points.map(([x, y], index) => `${index ? 'L' : 'M'} ${x} ${y}`).join(' ');
  }
  return {nodes, edges, layout: `dependency-tags-v3-${height}`,
    width: Math.max(392, columnX.at(-1)), height: Math.max(300, rowY.at(-1))};
}

/* Scope projections retain only direct links touching a member of the selection. */
function projectBoardScope(board, scope) {
  const members = new Set(board.tasks.filter(task => scope === 'all'
    || scope === `phase:${task.phase}`
    || (task.tags || []).some(tag => scope === `tag:${tag.toLowerCase()}`)).map(task => task.id));
  const included = new Set(members);
  for (const task of board.tasks) for (const dep of task.depends_on) {
    if (members.has(task.id) || members.has(dep)) { included.add(task.id); included.add(dep); }
  }
  return {...board, tasks: board.tasks.filter(task => included.has(task.id)).map(task => ({
    ...task, external: !members.has(task.id),
    depends_on: task.depends_on.filter(dep => included.has(dep) && (members.has(task.id) || members.has(dep)))
  }))};
}

function createBoardScopes({root, board, saved, change}) {
  const select = root.querySelector('[data-flow-scope]');
  const tabs = root.querySelector('[data-category-tabs]');
  const options = new Map([['all', 'All tasks']]);
  const tags = new Map();
  board.tasks.forEach(task => (task.tags || []).forEach(tag => tags.set(tag.toLowerCase(), tag)));
  [...tags].sort((a, b) => a[0].localeCompare(b[0])).forEach(([id, tag]) => options.set(`tag:${id}`, tag));
  board.phases.forEach(phase => options.set(`phase:${phase.id}`, `${phase.id} · ${phase.title}`));
  let flowScope = options.has(saved.flowScope) ? saved.flowScope : 'task';
  let worktreeScope = options.has(saved.worktreeScope) ? saved.worktreeScope : 'all';
  select.append(new Option('Selected task', 'task'));
  for (const [value, label] of options) {
    select.append(new Option(label, value));
    const button = document.createElement('button');
    button.type = 'button'; button.textContent = label;
    button.dataset.scope = value;
    button.addEventListener('click', () => { worktreeScope = value; change(); });
    tabs.append(button);
  }
  select.addEventListener('change', () => { flowScope = select.value; change(); });
  return {
    state: () => ({flowScope, worktreeScope}),
    restore(state) {
      if (state.flowScope === 'task' || options.has(state.flowScope)) flowScope = state.flowScope;
      if (options.has(state.worktreeScope)) worktreeScope = state.worktreeScope;
    },
    sync(view) {
      select.value = flowScope;
      select.parentElement.hidden = view !== 'flow';
      tabs.hidden = view !== 'worktree';
      for (const button of tabs.children) button.setAttribute('aria-pressed', String(button.dataset.scope === worktreeScope));
      return view === 'worktree' ? worktreeScope : flowScope;
    }
  };
}
