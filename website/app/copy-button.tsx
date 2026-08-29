'use client';

import { useEffect, useRef, useState } from 'react';

export function CopyButton({ value }: { value: string }) {
  const [status, setStatus] = useState<'idle' | 'copied' | 'failed'>('idle');
  const mounted = useRef(true);
  const copying = useRef(false);
  const resetTimer = useRef<number | null>(null);

  useEffect(() => {
    mounted.current = true;

    return () => {
      mounted.current = false;
      if (resetTimer.current !== null) {
        window.clearTimeout(resetTimer.current);
      }
    };
  }, []);

  async function copy() {
    if (copying.current) {
      return;
    }

    copying.current = true;

    if (resetTimer.current !== null) {
      window.clearTimeout(resetTimer.current);
      resetTimer.current = null;
    }

    let nextStatus: 'copied' | 'failed';

    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error('Clipboard API unavailable');
      }

      await navigator.clipboard.writeText(value);
      nextStatus = 'copied';
    } catch {
      nextStatus = 'failed';
    } finally {
      copying.current = false;
    }

    if (!mounted.current) {
      return;
    }

    setStatus(nextStatus);
    resetTimer.current = window.setTimeout(() => {
      if (mounted.current) {
        setStatus('idle');
      }
    }, 1800);
  }

  return (
    <button type="button" onClick={copy} aria-label={`Copy ${value}`}>
      <span aria-live="polite">
        {status === 'copied' ? 'Copied' : status === 'failed' ? 'Copy failed' : 'Copy'}
      </span>
    </button>
  );
}
