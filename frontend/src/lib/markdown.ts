import DOMPurify from "dompurify";
import { Marked } from "marked";
import type { TokenizerAndRendererExtension } from "marked";

// [[Title]] or [[Title|label]] — links between notes and todos.
const WIKI_LINK = /^\[\[([^\[\]|\n]+?)(?:\|([^\[\]\n]+?))?\]\]/;

export function normalizeTitle(title: string): string {
  return title.trim().toLowerCase();
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function wikiLinkExtension(knownTitles: ReadonlySet<string>): TokenizerAndRendererExtension {
  return {
    name: "wikilink",
    level: "inline",
    start: (src) => src.indexOf("[["),
    tokenizer(src) {
      const match = WIKI_LINK.exec(src);
      if (!match) return undefined;
      const target = match[1].trim();
      if (!target) return undefined; // "[[ ]]" is not a link
      return {
        type: "wikilink",
        raw: match[0],
        target,
        label: (match[2] ?? match[1]).trim(),
      };
    },
    renderer(token) {
      const target = String(token.target);
      const label = String(token.label);
      const missing = knownTitles.has(normalizeTitle(target)) ? "" : " wikilink-missing";
      return `<a href="#" class="wikilink${missing}" data-wikilink="${escapeHtml(target)}">${escapeHtml(label)}</a>`;
    },
  };
}

// Task-list checkboxes are the only <input> a note needs; drop every other kind (text boxes,
// password fields...) so a note can't present a fake form.
DOMPurify.addHook("afterSanitizeAttributes", (node) => {
  if (node.tagName === "INPUT" && node.getAttribute("type") !== "checkbox") node.remove();
});

// Open ordinary links in a new window and never leak the opener.
DOMPurify.addHook("afterSanitizeAttributes", (node) => {
  if (node.tagName === "A" && node.getAttribute("href")?.match(/^https?:/i)) {
    node.setAttribute("target", "_blank");
    node.setAttribute("rel", "noopener noreferrer");
  }
});

/**
 * Render Markdown (with [[wiki-links]]) to sanitized HTML.
 * `knownTitles` holds normalized titles of existing items so unresolved links can be styled.
 */
export function renderMarkdown(source: string, knownTitles: ReadonlySet<string>): string {
  const marked = new Marked({ gfm: true, breaks: true });
  marked.use({ extensions: [wikiLinkExtension(knownTitles)] });
  const html = marked.parse(source, { async: false });
  return DOMPurify.sanitize(html, {
    ADD_ATTR: ["data-wikilink"],
    // DOMPurify allows these by default, but in a note they could only be used to imitate a login
    // form or overlay the interface. Checkboxes (task lists) are kept; see the hook below.
    FORBID_TAGS: ["form", "style", "button", "textarea", "select", "option", "fieldset", "label"],
    FORBID_ATTR: ["style", "formaction", "action"],
  });
}
