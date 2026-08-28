// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CopyButton } from './copy-button';

const installCommand = 'curl -sL 9lives.run | sh';

describe('CopyButton', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('copies the command and resets its success message', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    render(<CopyButton value={installCommand} />);
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => expect(screen.getByText('Copied')).toBeTruthy());
    expect(writeText).toHaveBeenCalledWith(installCommand);

    act(() => vi.advanceTimersByTime(1800));
    expect(screen.getByText('Copy')).toBeTruthy();
  });

  it('shows a recoverable message when clipboard access fails', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockRejectedValue(new Error('denied')) },
    });

    render(<CopyButton value={installCommand} />);
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => expect(screen.getByText('Copy failed')).toBeTruthy());
  });

  it('clears its reset timer when unmounted', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
    const clearTimeoutSpy = vi.spyOn(window, 'clearTimeout');

    const { unmount } = render(<CopyButton value={installCommand} />);
    fireEvent.click(screen.getByRole('button'));
    await waitFor(() => expect(screen.getByText('Copied')).toBeTruthy());
    unmount();

    expect(clearTimeoutSpy).toHaveBeenCalled();
  });
});
