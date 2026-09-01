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

    const listingLink = screen.getByRole('link', { name: /listed on awesome-python-testing/i });

    expect(listingLink.getAttribute('href')).toBe('https://github.com/cleder/awesome-python-testing');
    expect(listingLink.getAttribute('target')).toBe('_blank');
    expect(listingLink.getAttribute('rel')).toBe('noreferrer');
  });
});
