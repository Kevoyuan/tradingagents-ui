import React from 'react';
import { StageInfo } from '../types';

interface StageRailProps {
  stages: StageInfo[];
}

export const StageRail: React.FC<StageRailProps> = ({ stages }) => {
  return (
    <div
      className="grid grid-cols-5 border-b border-rule px-10 bg-paper select-none"
      data-testid="stage-rail"
    >
      {stages.map((stage, idx) => {
        const isFirst = idx === 0;
        const isLast = idx === stages.length - 1;

        let statusClass = '';
        let sqClass = 'bg-transparent border border-faint';
        let nmClass = 'text-xs font-semibold tracking-[0.13em] uppercase text-faint';
        let ctClass = 'text-[13px] text-faint ml-auto pr-4 num';

        if (stage.status === 'done') {
          statusClass = 'stage-done';
          sqClass = 'bg-mut border-mut';
          nmClass = 'text-xs font-semibold tracking-[0.13em] uppercase text-mut';
          ctClass = 'text-[13px] text-mut ml-auto pr-4 num';
        } else if (stage.status === 'now') {
          statusClass = 'stage-now';
          sqClass = 'bg-ink border-ink';
          nmClass = 'text-xs font-bold tracking-[0.13em] uppercase text-ink';
          ctClass = 'text-[13px] text-ink font-semibold ml-auto pr-4 num';
        }

        return (
          <span
            key={stage.name}
            className={`flex items-baseline gap-2.5 py-3.5 ${
              isFirst ? 'pl-0' : 'pl-4.5'
            } ${!isLast ? 'border-r border-rule-2' : ''} ${statusClass}`}
            data-testid={`stage-${stage.team}`}
          >
            <span
              className={`w-[9px] h-[9px] shrink-0 self-center ${sqClass}`}
              aria-hidden="true"
            />
            <span className={nmClass}>{stage.name}</span>
            <span className={ctClass}>
              {stage.completed}/{stage.total}
            </span>
          </span>
        );
      })}
    </div>
  );
};
