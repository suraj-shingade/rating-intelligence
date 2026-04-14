/* ============================================================
   Lightweight markdown renderer -- supports paragraphs,
   headers, bold, italic, bullet/numbered lists, and code.
   No external library dependency.
   ============================================================ */

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function inlineMarkdown(text: string): string {
  let result = escapeHtml(text);
  // Bold
  result = result.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  result = result.replace(/__(.+?)__/g, '<strong>$1</strong>');
  // Italic
  result = result.replace(/\*(.+?)\*/g, '<em>$1</em>');
  result = result.replace(/_(.+?)_/g, '<em>$1</em>');
  // Inline code
  result = result.replace(/`(.+?)`/g, '<code>$1</code>');
  return result;
}

function parseMarkdown(md: string): string {
  const lines = md.split('\n');
  const htmlParts: string[] = [];
  let inList = false;
  let listType: 'ul' | 'ol' | null = null;

  const closeList = () => {
    if (inList && listType) {
      htmlParts.push(`</${listType}>`);
      inList = false;
      listType = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed === '') {
      closeList();
      continue;
    }

    // Headers
    const headerMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (headerMatch) {
      closeList();
      const level = headerMatch[1].length;
      htmlParts.push(
        `<h${level}>${inlineMarkdown(headerMatch[2])}</h${level}>`
      );
      continue;
    }

    // Unordered list
    const ulMatch = trimmed.match(/^[-*+]\s+(.+)$/);
    if (ulMatch) {
      if (!inList || listType !== 'ul') {
        closeList();
        htmlParts.push('<ul>');
        inList = true;
        listType = 'ul';
      }
      htmlParts.push(`<li>${inlineMarkdown(ulMatch[1])}</li>`);
      continue;
    }

    // Ordered list
    const olMatch = trimmed.match(/^\d+[.)]\s+(.+)$/);
    if (olMatch) {
      if (!inList || listType !== 'ol') {
        closeList();
        htmlParts.push('<ol>');
        inList = true;
        listType = 'ol';
      }
      htmlParts.push(`<li>${inlineMarkdown(olMatch[1])}</li>`);
      continue;
    }

    // Horizontal rule
    if (/^[-*_]{3,}$/.test(trimmed)) {
      closeList();
      htmlParts.push('<hr/>');
      continue;
    }

    // Regular paragraph
    closeList();
    htmlParts.push(`<p>${inlineMarkdown(trimmed)}</p>`);
  }

  closeList();
  return htmlParts.join('');
}

export default function MarkdownRenderer({
  content,
  className = '',
}: MarkdownRendererProps) {
  const html = parseMarkdown(content);
  return (
    <div
      className={`markdown-content ${className}`}
      dangerouslySetInnerHTML={{ __html: html }}
      style={{
        lineHeight: 1.7,
        fontSize: 'var(--font-size-base)',
        color: 'var(--color-gray-700)',
      }}
    />
  );
}
