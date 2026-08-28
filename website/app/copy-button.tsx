'use client';

import { useEffect, useRef, useState } from 'react';

export function CopyButton({ value }: { value: string }) {
  const [status, setStatus] = useState<'idle' | 'copied' | 'failed'>('idle');
  const resetTimer = useRef<ReturnType<typeof window.setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (resetTimer.current !== null) {
        window.clearTimeout(resetTimer.current);
      }
    };
  }, []);

  async function copy() {
    if (resetTimer.current !== null) {
      window.clearTimeout(resetTimer.current);
    }

    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error('Clipboard API unavailable');
      }

      await navigator.clipboard.writeText(value);
      setStatus('copied');
    } catch {
      setStatus('failed');
    }

    resetTimer.current = window.setTimeout(() => setStatus('idle'), 1800);
  }

  return (
    <button type="button" onClick={copy} aria-label={`Copy ${value}`}>
      <span aria-live="polite">
        {status === 'copied' ? 'Copied' : status === 'failed' ? 'Copy failed' : 'Copy'}
      </span>
    </button>
  );
}
