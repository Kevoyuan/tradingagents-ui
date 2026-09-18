import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { AgentBlock } from '../types';

interface AgentCollapsibleBlockProps {
  sectionSlug: string;
  block: AgentBlock;
  isOpen: boolean;
  onToggle: () => void;
}

export const AgentCollapsibleBlock: React.FC<AgentCollapsibleBlockProps> = ({
  sectionSlug,
  block,
  isOpen,
  onToggle,
}) => {
  const blockId = `block-${sectionSlug}-${block.slug}`;

  return (
    <article
      id={blockId}
      className="border border-rule bg-paper mb-4 overflow-hidden"
      data-testid={`agent-block-${sectionSlug}-${block.slug}`}
    >
      {/* Agent Block Header */}
      <div
        className="flex items-center justify-between px-5 py-3.5 bg-paper hover:bg-page/50 transition-colors cursor-pointer select-none border-b border-rule-2"
        onClick={onToggle}
      >
        <div className="flex items-baseline gap-3">
          {/* H3 Agent Name per Section 4 */}
          <h3 className="text-[15px] font-semibold tracking-[-0.015em] text-ink m-0">
            {block.name}
          </h3>
          <span className="text-[11px] font-semibold tracking-[0.13em] uppercase text-faint">
            {block.slug}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggle();
            }}
            className="text-xs font-semibold tracking-[0.1em] uppercase text-mut hover:text-ink transition-colors bg-transparent border-0 cursor-pointer p-0"
            data-testid={`agent-block-toggle-${sectionSlug}-${block.slug}`}
            aria-expanded={isOpen}
          >
            {isOpen ? 'Collapse −' : 'Expand +'}
          </button>
        </div>
      </div>

      {/* Collapsed content NOT mounted in DOM per requirement */}
      {isOpen && (
        <div
          className="px-6 py-5 prose-swiss text-ink-2 text-sm leading-relaxed"
          data-testid={`agent-block-content-${sectionSlug}-${block.slug}`}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeSanitize]}
            components={{
              h1: ({ ...props }) => (
                <h4 className="text-base font-bold text-ink mt-5 mb-2.5 first:mt-0 tracking-tight" {...props} />
              ),
              h2: ({ ...props }) => (
                <h5 className="text-sm font-semibold text-ink mt-4 mb-2 tracking-tight" {...props} />
              ),
              h3: ({ ...props }) => (
                <h6 className="text-xs font-semibold text-mut uppercase tracking-wider mt-3 mb-1" {...props} />
              ),
              h4: ({ ...props }) => (
                <h6 className="text-xs font-semibold text-mut uppercase tracking-wider mt-3 mb-1" {...props} />
              ),
              h5: ({ ...props }) => (
                <h6 className="text-xs font-medium text-mut uppercase tracking-wider mt-2 mb-1" {...props} />
              ),
              h6: ({ ...props }) => (
                <h6 className="text-xs font-medium text-faint uppercase tracking-wider mt-2 mb-1" {...props} />
              ),
              p: ({ ...props }) => <p className="mb-3 leading-relaxed text-ink-2" {...props} />,
              strong: ({ ...props }) => <strong className="font-semibold text-ink" {...props} />,
              table: ({ ...props }) => (
                <div className="my-4 overflow-x-auto">
                  <table className="w-full border-collapse border border-rule text-xs font-grotesk" {...props} />
                </div>
              ),
              th: ({ ...props }) => (
                <th className="border border-rule bg-page px-3 py-2 text-left font-semibold text-ink uppercase tracking-wider text-[11px]" {...props} />
              ),
              td: ({ ...props }) => (
                <td className="border border-rule px-3 py-2 text-ink-2 num" {...props} />
              ),
              ul: ({ ...props }) => <ul className="list-disc pl-5 mb-3 space-y-1" {...props} />,
              ol: ({ ...props }) => <ol className="list-decimal pl-5 mb-3 space-y-1" {...props} />,
              li: ({ ...props }) => <li className="leading-relaxed" {...props} />,
              blockquote: ({ ...props }) => (
                <blockquote className="border-l-2 border-rule pl-4 my-3 text-mut italic" {...props} />
              ),
              code: ({ className, children, ...props }) => {
                const isInline = !className && typeof children === 'string' && !children.includes('\n');
                if (isInline) {
                  return (
                    <code className="font-mono text-xs bg-page px-1.5 py-0.5 border border-rule-2 text-ink" {...props}>
                      {children}
                    </code>
                  );
                }
                return (
                  <pre className="font-mono text-xs bg-page p-3 border border-rule overflow-x-auto my-3 text-ink-2">
                    <code {...props}>{children}</code>
                  </pre>
                );
              },
            }}
          >
            {block.markdown}
          </ReactMarkdown>
        </div>
      )}
    </article>
  );
};
