// First non-empty line of a note, with the most common Markdown markers removed.
export function snippet(content: string): string {
  const line = content.split("\n").find((l) => l.trim()) ?? "";
  return line.replace(/^[#>*\-\s]+/, "").replace(/[*_`]/g, "").trim();
}
