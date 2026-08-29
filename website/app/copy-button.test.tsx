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
    const writeText = vi.fn().mockRejectedValue(new Error('denied'));
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    render(<CopyButton value={installCommand} />);
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => expect(screen.getByText('Copy failed')).toBeTruthy());

    await act(async () => fireEvent.click(screen.getByRole('button')));
    expect(writeText).toHaveBeenCalledTimes(2);
  });

  it('handles browsers without the Clipboard API', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: undefined,
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

  it('replaces the pending reset timer on a subsequent copy', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
    const clearTimeoutSpy = vi.spyOn(window, 'clearTimeout');
    const setTimeoutSpy = vi.spyOn(window, 'setTimeout');

    render(<CopyButton value={installCommand} />);
    fireEvent.click(screen.getByRole('button'));
    await waitFor(() => expect(screen.getByText('Copied')).toBeTruthy());

    clearTimeoutSpy.mockClear();
    setTimeoutSpy.mockClear();
    await act(async () => fireEvent.click(screen.getByRole('button')));

    expect(clearTimeoutSpy).toHaveBeenCalledTimes(1);
    expect(setTimeoutSpy).toHaveBeenCalledWith(expect.any(Function), 1800);
    expect(screen.getByText('Copied')).toBeTruthy();
  });

  it('ignores concurrent copy attempts until the active write finishes', async () => {
    let finishCopy: (() => void) | undefined;
    const pendingCopy = new Promise<void>((resolve) => {
      finishCopy = resolve;
    });
    const writeText = vi
      .fn()
      .mockReturnValueOnce(pendingCopy)
      .mockResolvedValueOnce(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    render(<CopyButton value={installCommand} />);
    fireEvent.click(screen.getByRole('button'));
    fireEvent.click(screen.getByRole('button'));

    expect(writeText).toHaveBeenCalledTimes(1);

    await act(async () => finishCopy?.());
    expect(screen.getByText('Copied')).toBeTruthy();

    await act(async () => fireEvent.click(screen.getByRole('button')));
    expect(writeText).toHaveBeenCalledTimes(2);
  });

  it('does not update state or create a timer when copying finishes after unmount', async () => {
    let finishCopy: (() => void) | undefined;
    const pendingCopy = new Promise<void>((resolve) => {
      finishCopy = resolve;
    });
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockReturnValue(pendingCopy) },
    });
    const setTimeoutSpy = vi.spyOn(window, 'setTimeout');

    const { unmount } = render(<CopyButton value={installCommand} />);
    fireEvent.click(screen.getByRole('button'));
    unmount();
    await act(async () => finishCopy?.());

    expect(setTimeoutSpy).not.toHaveBeenCalledWith(expect.any(Function), 1800);
  });
});
