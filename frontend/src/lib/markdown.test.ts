import { describe, expect, it } from "vitest";
import { normalizeTitle, renderMarkdown } from "./markdown";

const known = (...titles: string[]) => new Set(titles.map(normalizeTitle));
const render = (src: string, ...titles: string[]) => renderMarkdown(src, known(...titles));

describe("normalizeTitle", () => {
  it("trims and lowercases so links match regardless of case or padding", () => {
    expect(normalizeTitle("  Project Atlas ")).toBe("project atlas");
  });
});

describe("renderMarkdown basics", () => {
  it("renders headings, emphasis, lists and code", () => {
    const html = render("# Title\n\n**bold** and `code`\n\n- one\n- two");
    expect(html).toContain("<h1>Title</h1>");
    expect(html).toContain("<strong>bold</strong>");
    expect(html).toContain("<code>code</code>");
    expect(html.match(/<li>/g)).toHaveLength(2);
  });

  it("supports GitHub-style tables and task lists", () => {
    const html = render("| a | b |\n|---|---|\n| 1 | 2 |\n\n- [x] done");
    expect(html).toContain("<table>");
    expect(html).toContain('type="checkbox"');
  });

  it("turns single newlines into line breaks", () => {
    expect(render("one\ntwo")).toContain("<br>");
  });
});

describe("[[wiki-links]]", () => {
  it("links to an existing title", () => {
    const html = render("see [[Project Atlas]]", "Project Atlas");
    expect(html).toContain('class="wikilink"');
    expect(html).toContain('data-wikilink="Project Atlas"');
    expect(html).not.toContain("wikilink-missing");
  });

  it("marks links to titles that don't exist", () => {
    expect(render("see [[Nowhere]]", "Project Atlas")).toContain("wikilink-missing");
  });

  it("matches titles case-insensitively but keeps the written target", () => {
    const html = render("[[project atlas]]", "Project Atlas");
    expect(html).not.toContain("wikilink-missing");
    expect(html).toContain('data-wikilink="project atlas"');
  });

  it("supports [[Title|label]] aliases", () => {
    const html = render("[[Project Atlas|the atlas plan]]", "Project Atlas");
    expect(html).toContain('data-wikilink="Project Atlas"');
    expect(html).toContain(">the atlas plan</a>");
  });

  it("does not turn links inside code into wiki-links", () => {
    const html = render("`[[Not a link]]` and\n\n```\n[[Nor this]]\n```");
    expect(html).not.toContain("data-wikilink");
  });

  it("finds several links in one paragraph", () => {
    expect(render("[[A]] then [[B]] then [[C]]", "A", "B").match(/data-wikilink/g)).toHaveLength(3);
  });

  it("escapes titles so they cannot break out of the attribute", () => {
    const host = document.createElement("div");
    host.innerHTML = render('[[x" onmouseover="alert(1)]]');
    const link = host.querySelector("a")!;
    expect(link.hasAttribute("onmouseover")).toBe(false);
    expect(link.getAttributeNames().sort()).toEqual(["class", "data-wikilink", "href"]);
    expect(link.dataset.wikilink).toBe('x" onmouseover="alert(1)'); // preserved verbatim as data
  });

  it("ignores empty, blank and malformed links", () => {
    expect(render("[[]] [[ ]] [[   ]] [[unclosed")).not.toContain("data-wikilink");
  });
});

describe("sanitizing hostile Markdown/HTML", () => {
  const attacks: [string, string][] = [
    ["script tags", "<script>window.__x=1</script>hello"],
    ["inline event handlers", '<img src=x onerror="window.__x=2">'],
    ["javascript: links", "[click](javascript:window.__x=3)"],
    ["javascript: links in raw HTML", '<a href="javascript:window.__x=4">x</a>'],
    ["svg onload", '<svg onload="window.__x=5"></svg>'],
    ["iframes", '<iframe src="https://evil.example"></iframe>'],
    ["forms", '<form action="https://evil.example"><input name="p"></form>'],
    ["style tags", "<style>body{display:none}</style>"],
    ["data: html links", "[x](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==)"],
    ["mixed-case handlers", '<div ONCLICK="window.__x=6">x</div>'],
    ["buttons that could pose as UI", "<button>Click to log in</button>"],
    ["fixed-position overlays via style", '<div style="position:fixed;inset:0;background:red">x</div>'],
  ];

  it.each(attacks)("neutralizes %s", (_name, payload) => {
    const html = render(payload);
    expect(html).not.toMatch(/<script/i);
    expect(html).not.toMatch(/\son\w+\s*=/i);
    expect(html).not.toMatch(/href\s*=\s*["']?\s*(javascript|data):/i);
    expect(html).not.toMatch(/<(iframe|form|style|object|embed|button)/i);
    expect(html).not.toMatch(/\sstyle\s*=/i);
  });

  it("drops text and password inputs but keeps task-list checkboxes", () => {
    const html = render('<input type="password" name="p"> <input type="text"> <input>\n\n- [x] done\n- [ ] todo');
    const host = document.createElement("div");
    host.innerHTML = html;
    const inputs = [...host.querySelectorAll("input")];
    expect(inputs).toHaveLength(2);
    expect(inputs.every((i) => i.type === "checkbox")).toBe(true);
  });

  it("keeps ordinary https links and opens them safely", () => {
    const html = render("[docs](https://example.com)");
    expect(html).toContain('href="https://example.com"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
  });

  it("does not execute anything when the output is attached to the DOM", () => {
    const win = window as unknown as { __x?: number };
    win.__x = undefined;
    const host = document.createElement("div");
    host.innerHTML = render('<img src=x onerror="window.__x=1"><svg onload="window.__x=2"></svg>');
    document.body.appendChild(host);
    expect(win.__x).toBeUndefined();
    host.remove();
  });
});
