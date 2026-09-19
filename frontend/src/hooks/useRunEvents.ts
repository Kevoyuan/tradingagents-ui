import { useEffect, useRef, useState } from 'react';
import { RunEvent } from '../types';

const STORAGE_KEY_EVENTS = (id: string) => `tradingagents_events_${id}`;
const STORAGE_KEY_LAST_SEQ = (id: string) => `tradingagents_last_seq_${id}`;

export interface UseRunEventsResult {
  events: RunEvent[];
  lastSeq: number;
  isConnected: boolean;
  clearEvents: () => void;
}

export function useRunEvents(
  runId: string | null,
  isRunActive: boolean = true
): UseRunEventsResult {
  const [events, setEvents] = useState<RunEvent[]>(() => {
    if (!runId) return [];
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY_EVENTS(runId));
      if (saved) {
        return JSON.parse(saved) as RunEvent[];
      }
    } catch {
      // Ignore sessionStorage parsing errors
    }
    return [];
  });

  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [lastSeq, setLastSeq] = useState<number>(() => {
    if (!runId) return 0;
    try {
      const savedSeq = sessionStorage.getItem(STORAGE_KEY_LAST_SEQ(runId));
      if (savedSeq) {
        return parseInt(savedSeq, 10) || 0;
      }
    } catch {
      // Ignore
    }
    return 0;
  });

  const lastSeqRef = useRef<number>(lastSeq);
  const seenSeqRef = useRef<Set<number>>(new Set());

  // Reset ALL state when the selected run changes. The useState initialisers
  // above only run on mount, so switching from run A to run B used to leave A's
  // events in state and, worse, leave the sequence cursor at A's highest seq.
  // The SSE request for B then went out as ?after=<A's max>, so B's early
  // events were never requested at all and the record showed the previous run's
  // log under the new run's header.
  //
  // Must stay declared before the streaming effect below: both are keyed on
  // runId and run in declaration order, so this reseeds the cursor first.
  useEffect(() => {
    let restored: RunEvent[] = [];
    let restoredSeq = 0;
    if (runId) {
      try {
        const saved = sessionStorage.getItem(STORAGE_KEY_EVENTS(runId));
        if (saved) restored = JSON.parse(saved) as RunEvent[];
      } catch {
        restored = [];
      }
      try {
        const savedSeq = sessionStorage.getItem(STORAGE_KEY_LAST_SEQ(runId));
        if (savedSeq) restoredSeq = parseInt(savedSeq, 10) || 0;
      } catch {
        restoredSeq = 0;
      }
    }
    const maxSeq = restored.reduce((max, e) => Math.max(max, e.seq), 0);
    seenSeqRef.current = new Set(restored.map((e) => e.seq));
    lastSeqRef.current = Math.max(restoredSeq, maxSeq);
    setEvents(restored);
    setLastSeq(lastSeqRef.current);
  }, [runId]);

  const clearEvents = () => {
    if (runId) {
      sessionStorage.removeItem(STORAGE_KEY_EVENTS(runId));
      sessionStorage.removeItem(STORAGE_KEY_LAST_SEQ(runId));
    }
    seenSeqRef.current.clear();
    lastSeqRef.current = 0;
    setEvents([]);
    setLastSeq(0);
  };

  useEffect(() => {
    if (!runId) {
      setIsConnected(false);
      return;
    }

    // Determine seq to request from: strictly after the last sequence seen
    const afterSeq = lastSeqRef.current;
    const url = `/api/runs/${encodeURIComponent(runId)}/events?after=${afterSeq}`;

    const eventSource = new EventSource(url);
    setIsConnected(true);

    // EventSource treats any stream close as a dropped connection and retries
    // on its own. The server closes the stream immediately for a run it does
    // not own - a run left behind by a previous server process - so with no
    // guard the client reconnects once a second forever, which is what showed
    // up as an endless 'events?after=185 200' loop. Count consecutive
    // connections that deliver nothing and give up; any real event resets it.
    let emptyConnections = 0;

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onmessage = (messageEvent) => {
      try {
        emptyConnections = 0;
        const rawEvent: RunEvent = JSON.parse(messageEvent.data);
        if (!rawEvent || typeof rawEvent.seq !== 'number') return;

        // Ensure no duplicates
        if (seenSeqRef.current.has(rawEvent.seq)) {
          return;
        }

        seenSeqRef.current.add(rawEvent.seq);
        const newMaxSeq = Math.max(lastSeqRef.current, rawEvent.seq);
        lastSeqRef.current = newMaxSeq;
        setLastSeq(newMaxSeq);

        setEvents((prev) => {
          // Double check deduplication
          if (prev.some((e) => e.seq === rawEvent.seq)) {
            return prev;
          }
          const updated = [...prev, rawEvent].sort((a, b) => a.seq - b.seq);
          try {
            sessionStorage.setItem(STORAGE_KEY_EVENTS(runId), JSON.stringify(updated));
            sessionStorage.setItem(STORAGE_KEY_LAST_SEQ(runId), String(newMaxSeq));
          } catch {
            // Storage quota or disabled in context
          }
          return updated;
        });

        // If run reaches terminal state, close the stream
        if (rawEvent.kind === 'run_state') {
          const status = rawEvent.payload?.status;
          if (status === 'completed' || status === 'cancelled' || status === 'failed') {
            eventSource.close();
            setIsConnected(false);
          }
        }
      } catch (err) {
        console.error('Error handling SSE event:', err);
      }
    };

    eventSource.onerror = () => {
      emptyConnections += 1;
      if (!isRunActive || emptyConnections >= 3) {
        eventSource.close();
        setIsConnected(false);
      }
    };

    return () => {
      eventSource.close();
      setIsConnected(false);
    };
  }, [runId, isRunActive]);

  return { events, lastSeq, isConnected, clearEvents };
}
