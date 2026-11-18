import Markdown from "react-markdown";

/** Claude's prose as markdown. react-markdown drops raw HTML and unsafe URLs by default: keep it that way (no rehype-raw). */
export function Narration({ text }: { text: string }) {
  return (
    <div
      className="space-y-3 [&_h1]:text-xl [&_h1]:font-semibold [&_h2]:text-lg [&_h2]:font-semibold [&_h3]:font-semibold
        [&_ol]:list-decimal [&_ol]:pl-6 [&_ul]:list-disc [&_ul]:pl-6 [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:pl-3 [&_blockquote]:italic"
    >
      <Markdown>{text}</Markdown>
    </div>
  );
}
