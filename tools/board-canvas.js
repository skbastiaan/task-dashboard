/* Canvas interaction is presentation-only; it never writes task status. */
function createBoardCanvas({root, board, shownStatus, tagChip, selectTask, save, saved}) {
  const originals = new Map(board.tasks.map(task => [task.id, task]));
  const query = selector => root.querySelector(selector);
  const panel = query('[data-worktree]'), viewport = query('[data-map-viewport]');
  const world = query('[data-map-world]'), edges = query('[data-map-edges]');
  const mini = query('[data-minimap]'), miniView = query('[data-mini-view]');
  const tooltip = query('[data-map-tooltip]'), help = query('[data-map-help]');
  // Measure wrapped labels before routing links so all tags stay inside their cards.
  const measure = document.createElement('span');
  measure.className = 'task-tags map-tag-measure';
  root.append(measure);
  let tagHeight = 0;
  for (const task of board.tasks) {
    measure.replaceChildren(...(task.tags || []).map(tagChip));
    tagHeight = Math.max(tagHeight, measure.getBoundingClientRect().height);
  }
  measure.remove();
  let scope = null, graph, minZoom;
  const buttons = new Map(), paths = [];
  const svg = name => document.createElementNS('http://www.w3.org/2000/svg', name);
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  let camera = null, selected = null, expanded = false, suppressClick = false;
  const valid = value => value && [value.x, value.y, value.zoom].every(Number.isFinite);
  const restore = value => {
    const target = value?.scope;
    const [stage, category] = boardScopeParts(target);
    const known = typeof target === 'string'
      && (stage === 'all' || board.phases.some(phase => stage === `phase:${phase.id}`))
      && (category === 'all' || board.tasks.some(task => (task.tags || []).some(tag => category === `tag:${tag.toLowerCase()}`)));
    if (known && target !== scope) rebuild(target);
    camera = valid(value) && value.layout === graph.layout
      ? {x: value.x, y: value.y, zoom: clamp(value.zoom, minZoom, 2.5)} : null;
  };
  const hideTooltip = () => { tooltip.hidden = true; };
  const showTooltip = button => {
    tooltip.textContent = button.getAttribute('aria-label');
    tooltip.hidden = false;
  };
  const rebuild = next => {
    scope = next;
    graph = buildBoardGraph(projectBoardScope(board, scope), Math.ceil(108 + tagHeight));
    graph.layout += `:${scope}`;
    minZoom = Math.min(.08, 160 / Math.max(graph.width, graph.height));
    buttons.forEach(button => button.remove()); buttons.clear(); paths.length = 0;
    edges.replaceChildren(); mini.replaceChildren(miniView); hideTooltip();
    world.style.width = `${graph.width}px`;
    world.style.height = `${graph.height}px`;
    query('[data-map-count]').textContent = `${graph.nodes.size} tasks · ${graph.edges.length} links`;
    if (graph.divider !== null) {
      const line = svg('line');
      line.setAttribute('x1', 0); line.setAttribute('x2', graph.width);
      line.setAttribute('y1', graph.divider); line.setAttribute('y2', graph.divider);
      line.setAttribute('class', 'map-divider');
      edges.append(line);
      mini.insertBefore(line.cloneNode(), miniView);
      for (const [text, y] of [['Selected tasks', 24], ['External dependencies', graph.divider + 24]]) {
        const label = svg('text');
        label.textContent = text;
        label.setAttribute('x', 48); label.setAttribute('y', y);
        label.setAttribute('class', 'map-lane-label');
        edges.append(label);
      }
    }
    for (const edge of graph.edges) {
      const route = svg('g'), clearance = svg('path'), path = svg('path');
      clearance.setAttribute('d', edge.path);
      clearance.setAttribute('class', 'map-edge-clearance');
      path.setAttribute('d', edge.path);
      path.setAttribute('class', 'map-edge');
      path.setAttribute('marker-end', 'url(#board-map-arrow)');
      path.dataset.from = edge.from;
      path.dataset.to = edge.to;
      route.append(clearance, path);
      edges.append(route);
      paths.push({edge, path, route});
    }
    for (const node of graph.nodes.values()) {
      const {task} = node, status = shownStatus(originals.get(task.id));
      const button = document.createElement('button'), head = document.createElement('span');
      const id = document.createElement('strong'), state = document.createElement('span');
      const title = document.createElement('span');
      button.type = 'button';
      button.className = 'map-node cursor-interaction';
      button.dataset.taskId = task.id;
      button.dataset.level = node.level;
      button.dataset.status = status;
      button.setAttribute('aria-label', `${task.id}: ${task.title}; ${task.phase}; ${status}; ${(task.tags || []).join(', ')}`);
      button.setAttribute('aria-describedby', 'board-map-tooltip');
      Object.assign(button.style, {left: `${node.x}px`, top: `${node.y}px`,
        width: `${node.width}px`, height: `${node.height}px`});
      head.className = 'map-node-head';
      id.textContent = task.id;
      state.textContent = status;
      head.append(id, state);
      title.className = 'map-node-title';
      title.textContent = task.title;
      if (!task.external) button.append(head);
      button.append(title);
      button.classList.toggle('is-external', !!task.external);
      const tags = document.createElement('span');
      tags.className = 'task-tags';
      if (task.external) tags.textContent = (task.tags || [task.phase]).join(' · ');
      else tags.append(...(task.tags || []).map(tagChip));
      button.append(tags);
      button.addEventListener('click', () => selectTask(task.id));
      button.addEventListener('pointerenter', () => showTooltip(button));
      button.addEventListener('pointerleave', hideTooltip);
      button.addEventListener('focus', () => {
        showTooltip(button);
        if (!camera) return;
        const rect = button.getBoundingClientRect(), bounds = viewport.getBoundingClientRect();
        if (rect.left < bounds.left || rect.right > bounds.right || rect.top < bounds.top || rect.bottom > bounds.bottom) {
          focusTask(task.id);
        }
      });
      button.addEventListener('blur', hideTooltip);
      world.append(button);
      buttons.set(task.id, button);
      const mark = svg('rect');
      for (const key of ['x', 'y', 'width', 'height']) mark.setAttribute(key, node[key]);
      mini.insertBefore(mark, miniView);
    }
    mini.setAttribute('viewBox', `0 0 ${graph.width} ${graph.height}`);
    camera = null;
  };
  rebuild(saved?.scope || 'all');
  restore(saved);
  const paint = () => {
    if (!camera || panel.hidden) return;
    camera.x = clamp(camera.x, 0, graph.width);
    camera.y = clamp(camera.y, 0, graph.height);
    const width = viewport.clientWidth, height = viewport.clientHeight;
    const left = width / 2 - camera.x * camera.zoom, top = height / 2 - camera.y * camera.zoom;
    world.style.transform = `translate(${left}px, ${top}px) scale(${camera.zoom})`;
    query('[data-map-zoom]').textContent = `${Math.round(camera.zoom * 100)}%`;
    query('[data-map-action="in"]').disabled = camera.zoom >= 2.5;
    query('[data-map-action="out"]').disabled = camera.zoom <= minZoom;
    miniView.setAttribute('x', camera.x - width / camera.zoom / 2);
    miniView.setAttribute('y', camera.y - height / camera.zoom / 2);
    miniView.setAttribute('width', width / camera.zoom);
    miniView.setAttribute('height', height / camera.zoom);
  };
  function fit() {
    camera = {x: graph.width / 2, y: graph.height / 2,
      zoom: clamp(Math.min((viewport.clientWidth - 32) / graph.width,
        (viewport.clientHeight - 32) / graph.height), minZoom, 1)};
    paint();
  }
  function focusTask(id = selected) {
    const node = graph.nodes.get(id);
    if (!node) return;
    camera = {x: node.x + node.width / 2, y: node.y + node.height / 2,
      zoom: Math.min(1, (viewport.clientWidth - 32) / node.width)};
    paint();
  }
  const zoom = (factor, point = {x: viewport.clientWidth / 2, y: viewport.clientHeight / 2}) => {
    if (!camera) fit();
    const next = clamp(camera.zoom * factor, minZoom, 2.5);
    camera.x += (point.x - viewport.clientWidth / 2) * (1 / camera.zoom - 1 / next);
    camera.y += (point.y - viewport.clientHeight / 2) * (1 / camera.zoom - 1 / next);
    camera.zoom = next;
    paint();
  };
  const expand = () => {
    expanded = !expanded;
    panel.classList.toggle('is-expanded', expanded);
    query('[data-map-action="expand"]').setAttribute('aria-pressed', String(expanded));
    query('[data-map-action="expand"]').textContent = expanded ? 'Restore' : 'Expand';
    if (expanded) viewport.focus({preventScroll: true});
    paint();
  };
  const actions = {
    in: () => zoom(1.25), out: () => zoom(.8), fit,
    reset: () => { camera.zoom = 1; paint(); }, selected: () => focusTask(), expand,
    help: () => {
      help.hidden = !help.hidden;
      query('[data-map-action="help"]').setAttribute('aria-expanded', String(!help.hidden));
    }
  };
  panel.querySelectorAll('[data-map-action]').forEach(button => {
    button.addEventListener('click', () => { actions[button.dataset.mapAction](); save(); });
  });
  const pointers = new Map();
  let gesture = null;
  const point = event => {
    const rect = viewport.getBoundingClientRect();
    return {x: event.clientX - rect.left, y: event.clientY - rect.top};
  };
  const baseline = () => {
    const values = [...pointers.values()];
    if (!values.length) { gesture = null; return; }
    const a = values[0], b = values[1] || a;
    gesture = {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2,
      distance: Math.hypot(a.x - b.x, a.y - b.y), camera: {...camera}, moved: false};
  };
  viewport.addEventListener('pointerdown', event => {
    if (event.button !== 0 && event.button !== 1) return;
    if (event.target.closest('[data-minimap]')) return;
    if (pointers.size === 0) suppressClick = false;
    pointers.set(event.pointerId, point(event));
    viewport.setPointerCapture(event.pointerId);
    // Capture on the originating node preserves normal node click targeting.
    event.target.closest('.map-node')?.setPointerCapture(event.pointerId);
    baseline();
  });
  viewport.addEventListener('pointermove', event => {
    if (!pointers.has(event.pointerId) || !gesture) return;
    pointers.set(event.pointerId, point(event));
    const values = [...pointers.values()], a = values[0], b = values[1] || a;
    const x = (a.x + b.x) / 2, y = (a.y + b.y) / 2;
    const dx = x - gesture.x, dy = y - gesture.y;
    if (Math.hypot(dx, dy) < 4 && values.length === 1 && !gesture.moved) return;
    gesture.moved = true;
    suppressClick = true;
    hideTooltip();
    viewport.classList.add('is-panning');
    camera = {...gesture.camera};
    if (values.length > 1 && gesture.distance > 0) {
      zoom(Math.hypot(a.x - b.x, a.y - b.y) / gesture.distance, {x: gesture.x, y: gesture.y});
    }
    camera.x -= dx / camera.zoom;
    camera.y -= dy / camera.zoom;
    paint();
  });
  const release = event => {
    if (!pointers.delete(event.pointerId)) return;
    baseline();
    if (!pointers.size) { viewport.classList.remove('is-panning'); save(); }
  };
  viewport.addEventListener('pointerup', release);
  viewport.addEventListener('pointercancel', release);
  viewport.addEventListener('lostpointercapture', release);
  viewport.addEventListener('click', event => {
    if (!suppressClick || event.detail === 0) return;
    event.preventDefault();
    event.stopPropagation();
    suppressClick = false;
  }, true);
  let wheelTimer;
  viewport.addEventListener('wheel', event => {
    event.preventDefault();
    hideTooltip();
    const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? viewport.clientHeight : 1);
    zoom(Math.exp(-clamp(delta, -200, 200) * .003), point(event));
    clearTimeout(wheelTimer);
    wheelTimer = setTimeout(save, 180);
  }, {passive: false});
  mini.addEventListener('pointerdown', event => {
    event.preventDefault();
    event.stopPropagation();
    const transform = mini.getScreenCTM();
    if (!transform) return;
    const cursor = new DOMPoint(event.clientX, event.clientY).matrixTransform(transform.inverse());
    camera.x = cursor.x;
    camera.y = cursor.y;
    paint();
    save();
  });
  panel.addEventListener('keydown', event => {
    if (expanded && event.key === 'Tab') {
      const stops = [...panel.querySelectorAll('button:not(:disabled), select:not(:disabled), [tabindex="0"]')]
        .filter(element => element.getClientRects().length);
      const next = event.shiftKey ? stops.at(-1) : stops[0];
      const boundary = event.shiftKey ? stops[0] : stops.at(-1);
      if (document.activeElement === boundary) { event.preventDefault(); next?.focus(); }
      return;
    }
    if (event.key === 'Escape') {
      hideTooltip(); help.hidden = true;
      query('[data-map-action="help"]').setAttribute('aria-expanded', 'false');
      if (expanded) { expand(); query('[data-map-action="expand"]').focus(); }
      return;
    }
    if (event.ctrlKey || event.metaKey || event.altKey || event.target.closest('[data-category-tabs], select')) return;
    const moves = {ArrowLeft: [-80, 0], ArrowRight: [80, 0], ArrowUp: [0, -80], ArrowDown: [0, 80]};
    if (moves[event.key]) {
      const [x, y] = moves[event.key];
      camera.x += x / camera.zoom; camera.y += y / camera.zoom; paint();
    } else if (['+', '='].includes(event.key)) zoom(1.25);
    else if (event.key === '-') zoom(.8);
    else if (event.key === '0') fit();
    else if (event.key === '1') actions.reset();
    else if (event.key.toLowerCase() === 'f') focusTask();
    else return;
    event.preventDefault();
    save();
  });
  root.addEventListener('pointerdown', event => {
    if (help.hidden || help.contains(event.target) || event.target.closest('[data-map-action="help"]')) return;
    help.hidden = true;
    query('[data-map-action="help"]').setAttribute('aria-expanded', 'false');
  });
  new ResizeObserver(() => { if (!panel.hidden) camera ? paint() : fit(); }).observe(viewport);
  return {
    state: () => camera ? {...camera, layout: graph.layout, scope} : null,
    restore,
    show(id, next = scope) {
      if (next !== scope) rebuild(next);
      selected = id;
      query('[data-map-action="selected"]').disabled = !graph.nodes.has(id);
      const related = new Set();
      for (const {edge, path, route} of paths) {
        const match = edge.from === id || edge.to === id;
        path.classList.toggle('is-related', match);
        path.setAttribute('marker-end', `url(#board-map-${match ? 'selected-' : ''}arrow)`);
        if (match) { related.add(edge.from); related.add(edge.to); edges.append(route); }
      }
      for (const [taskId, button] of buttons) {
        button.setAttribute('aria-pressed', String(taskId === id));
        button.classList.toggle('is-related', taskId !== id && related.has(taskId));
      }
      if (!panel.hidden) camera ? paint() : fit();
    }
  };
}
