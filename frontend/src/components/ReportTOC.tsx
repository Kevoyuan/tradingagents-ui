import React from 'react';
import { ReportSection } from '../types';

interface ReportTOCProps {
  sections: ReportSection[];
  activeAgentId?: string | null;
  onSelectAgent?: (sectionSlug: string, agentSlug: string) => void;
  onExpandAll?: () => void;
  onCollapseAll?: () => void;
}

export const ReportTOC: React.FC<ReportTOCProps> = ({
  sections,
  activeAgentId,
  onSelectAgent,
  onExpandAll,
  onCollapseAll,
}) => {
  return (
    <nav
      className="sticky top-16 p-5 border-l border-rule bg-page select-none text-ink flex flex-col gap-5 max-h-[calc(100vh-64px)] overflow-y-auto"
      data-testid="report-toc"
      aria-label="Report Table of Contents"
    >
      <div className="flex items-baseline justify-between border-b border-ink pb-2.5">
        <h2 className="text-xs font-bold tracking-[0.15em] uppercase text-ink">
          Outline
        </h2>
        <div className="flex gap-2 text-[11px] font-semibold uppercase tracking-wider text-faint">
          {onExpandAll && (
            <button
              type="button"
              onClick={onExpandAll}
              className="hover:text-ink transition-colors cursor-pointer bg-transparent border-0 p-0"
              data-testid="toc-expand-all"
            >
              Expand
            </button>
          )}
          {onExpandAll && onCollapseAll && <span>·</span>}
          {onCollapseAll && (
            <button
              type="button"
              onClick={onCollapseAll}
              className="hover:text-ink transition-colors cursor-pointer bg-transparent border-0 p-0"
              data-testid="toc-collapse-all"
            >
              Collapse
            </button>
          )}
        </div>
      </div>

      <ul className="space-y-4 list-none p-0 m-0 text-sm">
        {sections.map((sec) => (
          <li key={sec.slug} className="space-y-1.5">
            {/* Level 1: Document Section (H2) */}
            <a
              href={`#section-${sec.slug}`}
              onClick={(e) => {
                e.preventDefault();
                const el = document.getElementById(`section-${sec.slug}`);
                if (el) {
                  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
              }}
              className="block text-xs font-bold tracking-[0.13em] uppercase text-ink hover:text-mut transition-colors no-underline"
              data-testid={`toc-section-${sec.slug}`}
            >
              {sec.title}
            </a>

            {/* Level 2: Agent name under section (H3) */}
            <ul className="pl-3.5 space-y-1 border-l border-rule list-none m-0">
              {sec.blocks.map((blk) => {
                const blockKey = `${sec.slug}-${blk.slug}`;
                const isActive = activeAgentId === blockKey;

                return (
                  <li key={blk.slug}>
                    <a
                      href={`#block-${sec.slug}-${blk.slug}`}
                      onClick={(e) => {
                        e.preventDefault();
                        if (onSelectAgent) {
                          onSelectAgent(sec.slug, blk.slug);
                        }
                        const el = document.getElementById(`block-${sec.slug}-${blk.slug}`);
                        if (el) {
                          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                      }}
                      className={`block text-[13px] py-0.5 leading-snug transition-colors no-underline ${
                        isActive
                          ? 'text-ink font-semibold'
                          : 'text-mut hover:text-ink'
                      }`}
                      data-testid={`toc-agent-${sec.slug}-${blk.slug}`}
                    >
                      {blk.name}
                    </a>
                  </li>
                );
              })}
            </ul>
          </li>
        ))}
      </ul>
    </nav>
  );
};
