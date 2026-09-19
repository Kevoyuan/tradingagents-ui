import React, { useEffect, useMemo, useState } from 'react';
import { IconRail } from './components/IconRail';
import { Masthead } from './components/Masthead';
import { VerdictBand } from './components/VerdictBand';
import { StageRail } from './components/StageRail';
import { TheRecord } from './components/TheRecord';
import { RightRail } from './components/RightRail';
import { RunLauncherModal } from './components/RunLauncherModal';
import { ReportsIndexScreen } from './components/ReportsIndexScreen';
import { ReportDetailScreen } from './components/ReportDetailScreen';
import { SettingsScreen } from './components/SettingsScreen';
import { useRun } from './hooks/useRun';
import { useRunEvents } from './hooks/useRunEvents';
import { AgentInfo, AgentStatus, StageInfo, TeamName, Verdict } from './types';

// Default initial roster of 12 agents
const INITIAL_ROSTER: { slug: string; name: string; team: TeamName }[] = [
  { slug: 'market', name: 'Market Analyst', team: 'analyst' },
  { slug: 'social', name: 'Social Analyst', team: 'analyst' },
  { slug: 'news', name: 'News Analyst', team: 'analyst' },
  { slug: 'fundamentals', name: 'Fundamentals Analyst', team: 'analyst' },
  { slug: 'bull_researcher', name: 'Bull Researcher', team: 'research' },
  { slug: 'bear_researcher', name: 'Bear Researcher', team: 'research' },
  { slug: 'research_manager', name: 'Research Manager', team: 'research' },
  { slug: 'trader', name: 'Trader', team: 'trading' },
  { slug: 'aggressive_analyst', name: 'Aggressive Analyst', team: 'risk' },
  { slug: 'neutral_analyst', name: 'Neutral Analyst', team: 'risk' },
  { slug: 'conservative_analyst', name: 'Conservative Analyst', team: 'risk' },
  { slug: 'portfolio_manager', name: 'Portfolio Manager', team: 'portfolio' },
];

export const App: React.FC = () => {
  const [currentPath, setCurrentPath] = useState<string>(() => window.location.pathname);

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = (to: string) => {
    window.history.pushState({}, '', to);
    setCurrentPath(to);
  };

  const { runId, header, startRun, cancelRun, applyHeaderUpdate } = useRun();
  const isRunActive = header?.status === 'running' || header?.status === 'pending';
  const { events } = useRunEvents(runId, isRunActive);

  const [isLauncherOpen, setIsLauncherOpen] = useState<boolean>(false);
  const [elapsedSec, setElapsedSec] = useState<number>(0);

  // Dynamic state derived from events
  const [agentsState, setAgentsState] = useState<
    Record<string, { status: AgentStatus; tokens: number; activity?: string; team?: TeamName }>
  >({});
  const [liveVerdict, setLiveVerdict] = useState<Verdict | null>(null);
  const [reportsCount, setReportsCount] = useState<number>(0);
  const [activeAgentSlug, setActiveAgentSlug] = useState<string | null>(null);
  const [tokenHistory, setTokenHistory] = useState<
    { elapsedSec: number; tokensIn: number; tokensOut: number }[]
  >([]);

  // Initialize or reset agent state when runId changes
  useEffect(() => {
    setAgentsState({});
    setLiveVerdict(null);
    setReportsCount(0);
    setActiveAgentSlug(null);
    setTokenHistory([]);
    setElapsedSec(0);
  }, [runId]);

  // Elapsed time counter
  useEffect(() => {
    if (header?.status !== 'running') {
      return;
    }

    const interval = setInterval(() => {
      setElapsedSec((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [header?.status]);

  // Process events to update agent roster, verdict, stats, and stages
  useEffect(() => {
    if (events.length === 0) return;

    let repCount = 0;
    let latestVerdict: Verdict | null = null;
    let currentAgent: string | null = null;
    let currentIn = 0;
    let currentOut = 0;

    const newAgents: Record<
      string,
      { status: AgentStatus; tokens: number; activity?: string; team?: TeamName }
    > = {};

    for (const e of events) {
      if (e.kind === 'agent_status') {
        const slug = e.payload?.agent || e.agent;
        const status = e.payload?.status as AgentStatus;
        const team = (e.team || e.payload?.team) as TeamName | undefined;
        if (slug) {
          newAgents[slug] = {
            ...(newAgents[slug] || { status: 'pending', tokens: 0 }),
            status: status || 'pending',
            team: team || newAgents[slug]?.team,
          };
          if (status === 'running') {
            currentAgent = slug;
          } else if (currentAgent === slug && status === 'done') {
            currentAgent = null;
          }
        }
      } else if (e.kind === 'agent_message') {
        const slug = e.agent;
        const team = e.team as TeamName | undefined;
        const tokensIn = e.payload?.tokens_in || 0;
        const tokensOut = e.payload?.tokens_out || 0;
        currentIn += tokensIn;
        currentOut += tokensOut;

        if (slug) {
          const prev = newAgents[slug] || { status: 'running', tokens: 0 };
          newAgents[slug] = {
            ...prev,
            tokens: prev.tokens + tokensIn + tokensOut,
            team: team || prev.team,
          };
        }
      } else if (e.kind === 'report_section') {
        if (e.payload?.complete) {
          repCount += 1;
        }
      } else if (e.kind === 'verdict') {
        latestVerdict = e.payload as Verdict;
      } else if (e.kind === 'run_state') {
        const stateStatus = e.payload?.status;
        if (stateStatus) {
          applyHeaderUpdate({ status: stateStatus });
        }
      }
    }

    setAgentsState(newAgents);
    setReportsCount(repCount);
    if (latestVerdict) {
      setLiveVerdict(latestVerdict);
    }
    setActiveAgentSlug(currentAgent);

    // Update token history
    if (currentIn > 0 || currentOut > 0) {
      setTokenHistory((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.tokensIn === currentIn && last.tokensOut === currentOut) {
          return prev;
        }
        return [...prev, { elapsedSec, tokensIn: currentIn, tokensOut: currentOut }];
      });
    }
  }, [events, elapsedSec, applyHeaderUpdate]);

  // Aggregate agent info
  const roster: AgentInfo[] = useMemo(() => {
    return INITIAL_ROSTER.map((item) => {
      const state = agentsState[item.slug];
      return {
        slug: item.slug,
        name: item.name,
        team: item.team,
        status: state?.status || 'pending',
        tokens: state?.tokens || 0,
        activity: state?.activity,
      };
    });
  }, [agentsState]);

  // Derive five-stage rail
  const stages: StageInfo[] = useMemo(() => {
    const list: { name: string; team: TeamName }[] = [
      { name: 'Analysts', team: 'analyst' },
      { name: 'Research', team: 'research' },
      { name: 'Trading', team: 'trading' },
      { name: 'Risk', team: 'risk' },
      { name: 'Portfolio', team: 'portfolio' },
    ];

    return list.map((stg) => {
      const teamAgents = roster.filter((a) => a.team === stg.team);
      const completed = teamAgents.filter((a) => a.status === 'done').length;
      const isRunning = teamAgents.some((a) => a.status === 'running');
      const isAllDone =
        teamAgents.length > 0 &&
        (completed === teamAgents.length || (header?.status === 'completed' && completed > 0));

      let status: 'done' | 'now' | 'pending' = 'pending';
      if (isAllDone) {
        status = 'done';
      } else if (isRunning) {
        status = 'now';
      }

      return {
        name: stg.name,
        team: stg.team,
        completed,
        total: teamAgents.length,
        status,
      };
    });
  }, [roster]);

  // Format elapsed time
  const elapsedFormatted = useMemo(() => {
    const mins = Math.floor(elapsedSec / 60);
    const secs = elapsedSec % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }, [elapsedSec]);

  // Active agent display text
  const activeAgentInfo = roster.find((a) => a.slug === activeAgentSlug);
  const activeAgentName = activeAgentInfo ? activeAgentInfo.name : null;

  const currentVerdict = liveVerdict || header?.verdict || null;
  const agentsDone = roster.filter((a) => a.status === 'done').length;

  const reportMatch = currentPath.match(/^\/reports\/([^/]+)\/([^/]+)/);
  const isReportsIndex = currentPath === '/reports' || currentPath === '/reports/';
  const isSettings = currentPath === '/settings' || currentPath.startsWith('/settings');

  // The gear toggles: pressing it while Settings is already open closes it,
  // rather than being a no-op because it navigates to the path you are on.
  const navigateFromRail = (to: string) => {
    if (to === '/settings' && isSettings) {
      navigate('/');
      return;
    }
    navigate(to);
  };

  return (
    <div className="grid grid-cols-[56px_minmax(0,1fr)] min-h-screen bg-page font-grotesk antialiased">
      {/* 56px icon rail */}
      <IconRail currentPath={currentPath} onNavigate={navigateFromRail} />

      {/* Screen container */}
      {reportMatch ? (
        <div className="bg-paper min-h-screen flex flex-col">
          <ReportDetailScreen
            ticker={decodeURIComponent(reportMatch[1])}
            date={decodeURIComponent(reportMatch[2])}
            onNavigate={navigate}
          />
        </div>
      ) : isReportsIndex ? (
        <div className="bg-paper min-h-screen flex flex-col">
          <ReportsIndexScreen onNavigate={navigate} />
        </div>
      ) : (
        <div className="bg-paper min-h-screen flex flex-col">
          {/* Masthead */}
          <Masthead
            header={header}
            elapsedFormatted={elapsedFormatted}
            onStop={cancelRun}
            onNewRun={() => setIsLauncherOpen(true)}
            currentPath={currentPath}
            onNavigate={navigate}
          />

          {/* Persistent verdict band */}
          <VerdictBand
            verdict={currentVerdict}
            runStatus={header?.status}
            activeAgent={activeAgentName}
            activeActivity={activeAgentInfo?.activity || 'analyzing signals'}
            agentsDone={agentsDone}
            totalAgents={roster.length}
            reportsDone={reportsCount}
            totalReports={7}
            elapsedFormatted={elapsedFormatted}
          />

          {/* Five-stage linear rail */}
          <StageRail stages={stages} />

          {/* Main body split */}
          <div className="grid grid-cols-[minmax(0,1fr)_364px] grow">
            {/* Left column: The record */}
            <TheRecord events={events} />

            {/* Right column: Right rail */}
            <RightRail
              agents={roster}
              stats={header?.stats}
              header={header}
              reportsDone={reportsCount}
              totalReports={7}
              elapsedFormatted={elapsedFormatted}
              tokenHistory={tokenHistory}
            />
          </div>

          {/* Launcher modal */}
          <RunLauncherModal
            isOpen={isLauncherOpen}
            onClose={() => setIsLauncherOpen(false)}
            onStart={async (params) => {
              await startRun(params);
            }}
            isLoading={false}
          />
        </div>
      )}

      {/* Settings opens as a modal drawer over whatever is behind it, so a
          running analysis stays mounted and visible through the scrim. */}
      {isSettings && <SettingsScreen onNavigate={navigate} onClose={() => navigate('/')} />}
    </div>
  );
};
