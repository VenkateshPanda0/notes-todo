import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent, WheelEvent as ReactWheelEvent } from "react";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
} from "d3-force";
import type { Simulation, SimulationLinkDatum, SimulationNodeDatum } from "d3-force";
import { graphApi, itemsApi } from "../api/client";
import { TaskModal } from "../components/TaskModal";
import { normalizeTitle } from "../lib/markdown";
import type { GraphData, GraphNodeData, Item, ItemType, Priority } from "../types/item";

const WIDTH = 960;
const HEIGHT = 600;
const DRAG_THRESHOLD = 4;

type SimNode = GraphNodeData & SimulationNodeDatum;
type SimLink = SimulationLinkDatum<SimNode>;

interface View {
  x: number;
  y: number;
  k: number;
}

const radius = (n: GraphNodeData) => 5 + Math.sqrt(n.degree) * 3;

function nodeFill(n: GraphNodeData): string {
  if (n.missing) return "transparent";
  if (n.type === "TODO") return n.completed ? "var(--text-secondary)" : "var(--color-success)";
  return "var(--color-primary)";
}

export function GraphView() {
  const [data, setData] = useState<GraphData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showUnlinked, setShowUnlinked] = useState(true);
  const [search, setSearch] = useState("");
  const [hovered, setHovered] = useState<string | null>(null);
  const [view, setView] = useState<View>({ x: 0, y: 0, k: 1 });
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});

  const [modalOpen, setModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<Item | null>(null);

  const svgRef = useRef<SVGSVGElement>(null);
  const simRef = useRef<Simulation<SimNode, SimLink> | null>(null);
  const nodesRef = useRef<SimNode[]>([]);
  const dragRef = useRef<{ key: string | null; startX: number; startY: number; moved: boolean } | null>(
    null,
  );
  const panRef = useRef<{ x: number; y: number; view: View } | null>(null);
  // While true, the view is fitted to the graph as the layout settles. Any manual zoom/pan/drag
  // turns it off so the app never fights the user.
  const fitPendingRef = useRef(true);

  const load = useCallback(
    () =>
      graphApi
        .get()
        .then((graph) => {
          setData(graph);
          setError(null);
        })
        .catch((err) => setError(err instanceof Error ? err.message : "Failed to load the graph.")),
    [],
  );

  useEffect(() => {
    load();
  }, [load]);

  // Nodes actually shown (optionally hiding items with no links).
  const visible = useMemo(() => {
    if (!data) return { nodes: [] as GraphNodeData[], edges: [] as GraphData["edges"] };
    const nodes = showUnlinked ? data.nodes : data.nodes.filter((n) => n.degree > 0);
    return { nodes, edges: data.edges };
  }, [data, showUnlinked]);

  // Zoom/pan so every node is visible with some padding.
  const fitToNodes = useCallback((nodes: SimNode[]) => {
    if (nodes.length === 0) return;
    const pad = 60;
    const xs = nodes.map((n) => n.x ?? WIDTH / 2);
    const ys = nodes.map((n) => n.y ?? HEIGHT / 2);
    const minX = Math.min(...xs) - pad;
    const maxX = Math.max(...xs) + pad;
    const minY = Math.min(...ys) - pad;
    const maxY = Math.max(...ys) + pad;
    const k = Math.min(1.6, Math.max(0.3, Math.min(WIDTH / (maxX - minX), HEIGHT / (maxY - minY))));
    setView({
      k,
      x: WIDTH / 2 - ((minX + maxX) / 2) * k,
      y: HEIGHT / 2 - ((minY + maxY) / 2) * k,
    });
  }, []);

  // (Re)build the force simulation whenever the visible graph changes.
  useEffect(() => {
    simRef.current?.stop();
    const previous = new Map(nodesRef.current.map((n) => [n.key, n]));
    const nodes: SimNode[] = visible.nodes.map((n) => {
      const old = previous.get(n.key);
      return { ...n, x: old?.x, y: old?.y };
    });
    const links: SimLink[] = visible.edges.map((e) => ({ source: e.source, target: e.target }));
    nodesRef.current = nodes;

    const sim = forceSimulation<SimNode>(nodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(links)
          .id((n) => n.key)
          .distance(110)
          .strength(0.5),
      )
      .force("charge", forceManyBody<SimNode>().strength(-420))
      .force("center", forceCenter(WIDTH / 2, HEIGHT / 2))
      // Gentle gravity so unlinked nodes stay on screen instead of being repelled away.
      .force("x", forceX<SimNode>(WIDTH / 2).strength(0.07))
      .force("y", forceY<SimNode>(HEIGHT / 2).strength(0.12))
      .force("collide", forceCollide<SimNode>().radius((n) => radius(n) + 6))
      .on("tick", () => {
        // Snapshot positions into state so rendering never reads the mutable simulation objects.
        setPositions(
          Object.fromEntries(nodes.map((n) => [n.key, { x: n.x ?? WIDTH / 2, y: n.y ?? HEIGHT / 2 }])),
        );
        if (fitPendingRef.current && sim.alpha() < 0.35) fitToNodes(nodes);
      })
      .on("end", () => {
        if (fitPendingRef.current) {
          fitToNodes(nodes);
          fitPendingRef.current = false;
        }
      });
    fitPendingRef.current = true;
    simRef.current = sim;
    return () => {
      sim.stop();
    };
  }, [visible, fitToNodes]);

  const neighbors = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const e of visible.edges) {
      if (!map.has(e.source)) map.set(e.source, new Set());
      if (!map.has(e.target)) map.set(e.target, new Set());
      map.get(e.source)!.add(e.target);
      map.get(e.target)!.add(e.source);
    }
    return map;
  }, [visible]);

  const query = normalizeTitle(search);
  const matches = useMemo(
    () =>
      query
        ? new Set(
            visible.nodes
              .filter((n) => n.title.toLowerCase().includes(query) || n.tags.some((t) => t.includes(query.replace(/^#/, ""))))
              .map((n) => n.key),
          )
        : null,
    [visible, query],
  );

  // A hovered node can disappear (e.g. a missing note gets created), and pointerleave never fires
  // for removed elements, so ignore hover keys that no longer exist.
  const activeHover = hovered && visible.nodes.some((n) => n.key === hovered) ? hovered : null;

  const isDimmed = (key: string): boolean => {
    if (activeHover) return key !== activeHover && !neighbors.get(activeHover)?.has(key);
    if (matches) return !matches.has(key);
    return false;
  };

  // --- pointer helpers: client pixels -> SVG user units -> graph coordinates -------------------
  const toLocal = (clientX: number, clientY: number) => {
    const rect = svgRef.current!.getBoundingClientRect();
    const scale = rect.width / WIDTH;
    return { x: (clientX - rect.left) / scale, y: (clientY - rect.top) / scale };
  };

  const onWheel = (e: ReactWheelEvent<SVGSVGElement>) => {
    fitPendingRef.current = false;
    const p = toLocal(e.clientX, e.clientY);
    const factor = Math.exp(-e.deltaY * 0.0015);
    setView((v) => {
      const k = Math.min(4, Math.max(0.25, v.k * factor));
      const ratio = k / v.k;
      return { k, x: p.x - (p.x - v.x) * ratio, y: p.y - (p.y - v.y) * ratio };
    });
  };

  const onBackgroundPointerDown = (e: ReactPointerEvent<SVGSVGElement>) => {
    if (e.target !== e.currentTarget && (e.target as Element).tagName !== "rect") return;
    e.currentTarget.setPointerCapture(e.pointerId);
    fitPendingRef.current = false;
    panRef.current = { x: e.clientX, y: e.clientY, view };
  };

  const onNodePointerDown = (e: ReactPointerEvent<SVGGElement>, key: string) => {
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    fitPendingRef.current = false;
    dragRef.current = { key, startX: e.clientX, startY: e.clientY, moved: false };
  };

  const onPointerMove = (e: ReactPointerEvent<SVGSVGElement>) => {
    const drag = dragRef.current;
    if (drag?.key) {
      if (Math.hypot(e.clientX - drag.startX, e.clientY - drag.startY) > DRAG_THRESHOLD) {
        drag.moved = true;
      }
      if (drag.moved) {
        const node = nodesRef.current.find((n) => n.key === drag.key);
        if (node) {
          const p = toLocal(e.clientX, e.clientY);
          node.fx = (p.x - view.x) / view.k;
          node.fy = (p.y - view.y) / view.k;
          simRef.current?.alphaTarget(0.3).restart();
        }
      }
      return;
    }
    const pan = panRef.current;
    if (pan) {
      const rect = svgRef.current!.getBoundingClientRect();
      const scale = rect.width / WIDTH;
      setView({
        ...pan.view,
        x: pan.view.x + (e.clientX - pan.x) / scale,
        y: pan.view.y + (e.clientY - pan.y) / scale,
      });
    }
  };

  const openNode = async (node: GraphNodeData) => {
    try {
      let item: Item;
      if (node.id === null) {
        // A link to a note that doesn't exist yet: create it.
        item = await itemsApi.create({ title: node.title, type: "NOTE" });
        await load();
      } else {
        item = await itemsApi.get(node.id);
      }
      setEditingItem(item);
      setModalOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open item.");
    }
  };

  const resetLayout = () => {
    fitPendingRef.current = true;
    const sim = simRef.current;
    if (!sim) return;
    sim.nodes().forEach((node) => {
      node.fx = null;
      node.fy = null;
    });
    sim.alpha(0.8).restart();
  };

  const onPointerUp = () => {
    const drag = dragRef.current;
    if (drag?.key) {
      const node = nodesRef.current.find((n) => n.key === drag.key);
      if (node) {
        // A dragged node stays pinned where it was dropped; "Reset layout" releases every pin.
        simRef.current?.alphaTarget(0);
        if (!drag.moved) openNode(node);
      }
    }
    dragRef.current = null;
    panRef.current = null;
  };

  // --- modal handlers ---------------------------------------------------------------------------
  const knownTitles = useMemo(
    () => new Set((data?.nodes ?? []).filter((n) => !n.missing).map((n) => normalizeTitle(n.title))),
    [data],
  );

  const handleSave = async (payload: {
    title: string;
    content: string;
    type: ItemType;
    priority: Priority;
    due_date: string | null;
    tags: string[];
  }) => {
    if (!editingItem) return;
    await itemsApi.update(editingItem.id, payload);
    if (editingItem.type !== payload.type) await itemsApi.convert(editingItem.id);
    await load();
  };

  const handleDelete = async () => {
    if (!editingItem) return;
    await itemsApi.remove(editingItem.id);
    setModalOpen(false);
    await load();
  };

  const handleOpenLink = async (title: string) => {
    const node = data?.nodes.find((n) => normalizeTitle(n.title) === normalizeTitle(title));
    await openNode(node ?? { key: "", id: null, title: title.trim(), type: "NOTE", completed: false, tags: [], missing: true, degree: 0 });
  };

  const at = (key: string) => positions[key] ?? { x: WIDTH / 2, y: HEIGHT / 2 };
  const showAllLabels = visible.nodes.length <= 40;
  const linkedCount = data?.nodes.filter((n) => n.degree > 0).length ?? 0;

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text)]">Graph</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            How your notes and todos link together with <code>[[Title]]</code>. Click a node to open
            it; drag to move and pin; scroll to zoom.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Highlight…"
            aria-label="Highlight nodes"
            className="w-40 rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-1.5 text-sm text-[var(--text)] placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
            <input
              type="checkbox"
              checked={showUnlinked}
              onChange={(e) => setShowUnlinked(e.target.checked)}
            />
            Unlinked items
          </label>
          <button
            onClick={resetLayout}
            className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--text)] hover:border-primary/50"
          >
            Reset layout
          </button>
        </div>
      </div>

      {error && <p className="mb-3 text-sm text-danger-ink">{error}</p>}

      {data && data.nodes.length === 0 && (
        <p className="py-16 text-center text-sm text-[var(--text-secondary)]">
          Nothing to show yet. Add some notes and connect them with <code>[[Title]]</code>.
        </p>
      )}

      {data && data.nodes.length > 0 && linkedCount === 0 && (
        <p className="mb-3 rounded-lg bg-primary/10 px-3 py-2 text-sm text-primary-ink">
          No links yet. Write <code>[[Another note]]</code> inside a note to connect them.
        </p>
      )}

      {data && data.nodes.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)]">
          <svg
            ref={svgRef}
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            className="block h-auto w-full touch-none select-none"
            role="img"
            aria-label="Graph of linked notes and todos"
            onWheel={onWheel}
            onPointerDown={onBackgroundPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
          >
            <rect width={WIDTH} height={HEIGHT} fill="transparent" />
            <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
              {visible.edges.map((l, i) => {
                const s = at(l.source);
                const t = at(l.target);
                const dim = activeHover
                  ? !(l.source === activeHover || l.target === activeHover)
                  : matches
                    ? !(matches.has(l.source) && matches.has(l.target))
                    : false;
                return (
                  <line
                    key={i}
                    x1={s.x}
                    y1={s.y}
                    x2={t.x}
                    y2={t.y}
                    stroke="var(--text-secondary)"
                    strokeWidth={1.2 / view.k}
                    opacity={dim ? 0.08 : 0.45}
                  />
                );
              })}

              {visible.nodes.map((n) => {
                const r = radius(n);
                const pos = at(n.key);
                const dim = isDimmed(n.key);
                const showLabel =
                  showAllLabels || n.degree >= 2 || activeHover === n.key || (matches?.has(n.key) ?? false);
                return (
                  <g
                    key={n.key}
                    data-node={n.key}
                    transform={`translate(${pos.x} ${pos.y})`}
                    opacity={dim ? 0.15 : 1}
                    className="cursor-pointer"
                    onPointerDown={(e) => onNodePointerDown(e, n.key)}
                    onPointerEnter={() => setHovered(n.key)}
                    onPointerLeave={() => setHovered((h) => (h === n.key ? null : h))}
                  >
                    <circle
                      r={r}
                      fill={nodeFill(n)}
                      stroke={n.missing ? "var(--text-secondary)" : "var(--bg-elevated)"}
                      strokeWidth={n.missing ? 1.5 : 2}
                      strokeDasharray={n.missing ? "3 2" : undefined}
                    />
                    {showLabel && (
                      <text
                        y={r + 12}
                        textAnchor="middle"
                        fontSize={11 / Math.max(view.k, 0.75)}
                        fill="var(--text)"
                        paintOrder="stroke"
                        stroke="var(--bg-elevated)"
                        strokeWidth={3}
                        pointerEvents="none"
                      >
                        {n.title.length > 28 ? `${n.title.slice(0, 27)}…` : n.title}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          </svg>
        </div>
      )}

      {data && data.nodes.length > 0 && (
        // The picture is mouse-oriented, so offer the same items as a keyboard- and screen-reader-friendly
        // list. It is visually hidden until a keyboard user tabs into it.
        <nav aria-label="Graph items" className="sr-only focus-within:not-sr-only focus-within:mt-3">
          <p className="mb-1 text-xs text-[var(--text-secondary)]">
            Items in the graph, with how many links each has:
          </p>
          <ul className="flex flex-wrap gap-2">
            {data.nodes.map((n) => (
              <li key={n.key}>
                <button
                  type="button"
                  onClick={() => openNode(n)}
                  className="rounded-full border border-[var(--border)] px-2.5 py-0.5 text-xs text-[var(--text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
                >
                  {n.title}
                  {n.missing ? " (not written yet, creates it)" : ""} · {n.degree} link
                  {n.degree === 1 ? "" : "s"}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      )}

      {data && data.nodes.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-4 text-xs text-[var(--text-secondary)]">
          <Legend color="var(--color-primary)" label="Note" />
          <Legend color="var(--color-success)" label="Todo" />
          <Legend color="var(--text-secondary)" label="Completed todo" />
          <Legend dashed label="Link to a note that doesn't exist yet (click to create)" />
          <span className="ml-auto">
            {data.nodes.length} items · {data.edges.length} links
          </span>
        </div>
      )}

      <TaskModal
        open={modalOpen}
        initial={editingItem}
        knownTitles={knownTitles}
        onOpenLink={handleOpenLink}
        onOpenItem={(item) => setEditingItem(item)}
        onClose={() => setModalOpen(false)}
        onSave={handleSave}
        onDelete={editingItem ? handleDelete : undefined}
      />
    </div>
  );
}

function Legend({ color, label, dashed }: { color?: string; label: string; dashed?: boolean }) {
  return (
    <span className="flex items-center gap-1.5">
      <span
        className="inline-block h-3 w-3 rounded-full"
        style={{
          background: dashed ? "transparent" : color,
          border: dashed ? "1.5px dashed var(--text-secondary)" : undefined,
        }}
      />
      {label}
    </span>
  );
}
