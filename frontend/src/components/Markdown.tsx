import { useMemo } from "react";
import { renderMarkdown } from "../lib/markdown";

interface MarkdownProps {
  source: string;
  knownTitles: ReadonlySet<string>;
  onWikiLink: (title: string) => void;
  className?: string;
}

export function Markdown({ source, knownTitles, onWikiLink, className = "" }: MarkdownProps) {
  const html = useMemo(() => renderMarkdown(source, knownTitles), [source, knownTitles]);

  return (
    <div
      className={`markdown ${className}`}
      // Sanitized by DOMPurify in renderMarkdown.
      dangerouslySetInnerHTML={{ __html: html }}
      onClick={(e) => {
        const link = (e.target as HTMLElement).closest<HTMLAnchorElement>("a[data-wikilink]");
        if (link) {
          e.preventDefault();
          onWikiLink(link.dataset.wikilink ?? "");
        }
      }}
    />
  );
}
