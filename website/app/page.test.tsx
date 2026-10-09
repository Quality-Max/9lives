// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import Home from './page';

afterEach(cleanup);

describe('QualityMax branding', () => {
  it('uses the canonical logo asset and links both wordmarks to QualityMax', () => {
    render(<Home />);

    const brandLinks = screen.getAllByRole('link', { name: 'QualityMax home' });
    const logos = screen.getAllByRole('img', { name: 'QualityMax' });

    expect(brandLinks).toHaveLength(2);
    expect(brandLinks.every((link) => link.getAttribute('href') === 'https://qualitymax.io')).toBe(true);
    expect(logos).toHaveLength(2);
    expect(
      logos.every(
        (logo) => logo.getAttribute('src') === 'https://qualitymax.io/static/img/qualitymax-logo-white.png',
      ),
    ).toBe(true);
  });

  it('links to the AI in QA feature', () => {
    render(<Home />);

    const featureLink = screen.getByRole('link', { name: /as featured in ai in qa — issue #18/i });

    expect(featureLink.getAttribute('href')).toBe('https://aiinqa.com/ai-in-qa-issue-18/');
    expect(featureLink.getAttribute('target')).toBe('_blank');
    expect(featureLink.getAttribute('rel')).toBe('noreferrer');
  });

  it('links to the awesome-python-testing listing', () => {
    render(<Home />);

    const listingLink = screen.getByRole('link', { name: /python package listed on awesome-python-testing/i });

    expect(listingLink.getAttribute('href')).toBe('https://github.com/cleder/awesome-python-testing');
    expect(listingLink.getAttribute('target')).toBe('_blank');
    expect(listingLink.getAttribute('rel')).toBe('noreferrer');
  });
});

describe('Go runner onboarding', () => {
  it('leads with Go installation and execution while retaining an explicit Python path', () => {
    render(<Home />);

    expect(screen.getAllByText('curl -fsSL https://9lives.run/install.sh | sh')).toHaveLength(2);
    expect(screen.getByText('export PATH="$HOME/.local/share/9lives-runner/bin:$PATH"')).toBeTruthy();
    expect(screen.getByText('9l run tests/ --timeout 5m --format json')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Documentation' }).getAttribute('href'))
      .toBe('https://quality-max.github.io/9lives-runner/');
    expect(screen.getByRole('link', { name: /github/i }).getAttribute('href'))
      .toBe('https://github.com/Quality-Max/9lives-runner');
    expect(screen.getByRole('heading', { name: 'Python is in maintenance mode.' })).toBeTruthy();
    expect(screen.getByText('uv tool install 9lives')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Read the migration guide' }).getAttribute('href'))
      .toBe('https://github.com/Quality-Max/9lives/blob/main/docs/MIGRATING_TO_GO.md');
  });
});
