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
});
