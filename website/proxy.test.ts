import { describe, expect, it } from 'vitest';
import { NextRequest } from 'next/server';

import { proxy } from './proxy';

describe('installer content negotiation', () => {
  it('serves the landing page to browsers that accept HTML', () => {
    const response = proxy(
      new NextRequest('https://9lives.run/', {
        headers: { accept: 'text/html,application/xhtml+xml' },
      }),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get('x-middleware-next')).toBe('1');
  });

  it('matches HTML media types case-insensitively', () => {
    const response = proxy(
      new NextRequest('https://9lives.run/', {
        headers: { accept: 'Text/Html; q=0.9' },
      }),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get('x-middleware-next')).toBe('1');
  });

  it('redirects command-line GET requests to the installer', () => {
    const response = proxy(
      new NextRequest('https://9lives.run/', {
        headers: { accept: '*/*' },
      }),
    );

    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('https://9lives.run/install.sh');
  });

  it('redirects HEAD requests to the installer', () => {
    const response = proxy(
      new NextRequest('https://9lives.run/', {
        method: 'HEAD',
        headers: { accept: '*/*' },
      }),
    );

    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('https://9lives.run/install.sh');
  });

  it('does not redirect non-GET methods to the static installer', () => {
    const response = proxy(
      new NextRequest('https://9lives.run/', {
        method: 'POST',
        headers: { accept: 'application/json' },
      }),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get('x-middleware-next')).toBe('1');
  });
});
