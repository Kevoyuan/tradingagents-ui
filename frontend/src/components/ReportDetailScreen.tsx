import React, { useEffect, useState } from 'react';
import { ReportDetail } from '../types';
import { ReportVerdictCard } from './ReportVerdictCard';
import { ReportTOC } from './ReportTOC';
import { AgentCollapsibleBlock } from './AgentCollapsibleBlock';
import { ReportExportWidget } from './ReportExportWidget';

interface ReportDetailScreenProps {
  ticker: string;
  date: string;
  onNavigate: (path: string) => void;
}

export const ReportDetailScreen: React.FC<ReportDetailScreenProps> = ({
  ticker,
  date,
  onNavigate,
}) => {
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Track collapsed/open state per agent block
  // Key: `${sectionSlug}-${agentSlug}`
  const [openBlocks, setOpenBlocks] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`/api/reports/${encodeURIComponent(ticker)}/${encodeURIComponent(date)}`)
      .then(async (res) => {
        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          throw new Error(errData?.detail || `HTTP ${res.status}: Failed to load report`);
        }
        return res.json();
      })
      .then((data: ReportDetail) => {
        if (cancelled) return;
        setReport(data);

        // Initially open all blocks so user can read smoothly, but user can collapse any
        const initialOpen: Record<string, boolean> = {};
        for (const sec of data.sections || []) {
          for (const blk of sec.blocks || []) {
            initialOpen[`${sec.slug}-${blk.slug}`] = true;
          }
        }
        setOpenBlocks(initialOpen);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || String(err));
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [ticker, date]);

  const toggleBlock = (sectionSlug: string, agentSlug: string) => {
    const key = `${sectionSlug}-${agentSlug}`;
    setOpenBlocks((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleExpandAll = () => {
    if (!report?.sections) return;
    const next: Record<string, boolean> = {};
    for (const sec of report.sections) {
      for (const blk of sec.blocks) {
        next[`${sec.slug}-${blk.slug}`] = true;
      }
    }
    setOpenBlocks(next);
  };

  const handleCollapseAll = () => {
    if (!report?.sections) return;
    const next: Record<string, boolean> = {};
    for (const sec of report.sections) {
      for (const blk of sec.blocks) {
        next[`${sec.slug}-${blk.slug}`] = false;
      }
    }
    setOpenBlocks(next);
  };

  const handleSelectAgentFromTOC = (sectionSlug: string, agentSlug: string) => {
    const key = `${sectionSlug}-${agentSlug}`;
    if (!openBlocks[key]) {
      setOpenBlocks((prev) => ({ ...prev, [key]: true }));
    }
  };

  if (loading) {
    return (
      <div className="p-12 flex flex-col items-center justify-center min-h-[400px] text-mut" data-testid="report-loading">
        <span className="inline-block w-5 h-5 border-2 border-mut border-t-transparent rounded-full animate-spin mb-3"></span>
        <div className="text-xs font-semibold tracking-[0.13em] uppercase">
          Loading report for {ticker} ({date})...
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-10" data-testid="report-error">
        <div className="mb-4">
          <button
            type="button"
            onClick={() => onNavigate('/reports')}
            className="text-xs font-semibold tracking-[0.13em] uppercase text-mut hover:text-ink transition-colors bg-transparent border-0 cursor-pointer p-0"
          >
            ← Back to Reports Index
          </button>
        </div>
        <div className="p-6 border border-sell/40 bg-sell/5 text-sell max-w-2xl">
          <h3 className="text-sm font-bold uppercase tracking-wider mb-2">Report Not Found</h3>
          <p className="text-sm m-0">{error || 'Unable to display report'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper flex flex-col font-grotesk" data-testid="report-screen">
      {/* Top Header / Breadcrumb Bar */}
      <header className="h-[62px] flex items-center justify-between px-10 border-b border-ink bg-paper sticky top-0 z-30 select-none">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => onNavigate('/reports')}
            className="text-xs font-semibold tracking-[0.13em] uppercase text-faint hover:text-ink transition-colors bg-transparent border-0 cursor-pointer p-0"
            data-testid="back-to-reports"
          >
            ← Reports
          </button>
          <span className="text-faint">/</span>
          <h1 className="text-sm font-bold tracking-[0.15em] uppercase text-ink m-0">
            {ticker} · {date}
          </h1>
        </div>

        {/* Export Widget */}
        <ReportExportWidget ticker={ticker} date={date} />
      </header>

      {/* Verdict Band (driven by extract_verdict) */}
      <ReportVerdictCard
        verdict={report.verdict || null}
        ticker={ticker}
        tradeDate={date}
      />

      {/* Main Content Layout: Left Sections & Blocks, Right 2-level TOC */}
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_300px] grow">
        {/* Left Column: Five document sections */}
        <main className="p-8 md:p-10 border-r border-rule space-y-12">
          {report.sections.map((section) => (
            <section
              key={section.slug}
              id={`section-${section.slug}`}
              className="scroll-mt-20"
              data-testid={`report-section-${section.slug}`}
            >
              {/* Document Section Heading (H2 in document hierarchy) */}
              <div className="flex items-baseline justify-between border-b border-ink pb-3 mb-6">
                <h2 className="text-sm font-bold tracking-[0.15em] uppercase text-ink m-0">
                  {section.title}
                </h2>
                <span className="text-xs text-mut tracking-wider">
                  {section.blocks.length} {section.blocks.length === 1 ? 'AGENT' : 'AGENTS'}
                </span>
              </div>

              {/* Collapsible Agent Blocks */}
              <div className="space-y-4">
                {section.blocks.map((block) => {
                  const key = `${section.slug}-${block.slug}`;
                  const isOpen = !!openBlocks[key];

                  return (
                    <AgentCollapsibleBlock
                      key={block.slug}
                      sectionSlug={section.slug}
                      block={block}
                      isOpen={isOpen}
                      onToggle={() => toggleBlock(section.slug, block.slug)}
                    />
                  );
                })}
              </div>
            </section>
          ))}
        </main>

        {/* Right Column: Two-level TOC */}
        <aside className="hidden lg:block">
          <ReportTOC
            sections={report.sections}
            onSelectAgent={handleSelectAgentFromTOC}
            onExpandAll={handleExpandAll}
            onCollapseAll={handleCollapseAll}
          />
        </aside>
      </div>
    </div>
  );
};
