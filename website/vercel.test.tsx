// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';

import Home from './app/page';
import vercelConfig from './vercel.json';

afterEach(cleanup);

it('allows the rendered demo through the deployed frame policy without allowing other origins', () => {
  render(<Home />);
  const demo = screen.getByTitle('9lives: repair a broken Playwright locator');
  const demoOrigin = new URL(demo.getAttribute('src')!).origin;
  const policy = vercelConfig.headers
    .find((rule) => rule.source === '/(.*)')!
    .headers.find((header) => header.key === 'Content-Security-Policy')!.value;
  const directives = new Map(policy.split(';').map((directive) => {
    const [name, ...sources] = directive.trim().split(/\s+/);
    return [name, sources];
  }));

  const allowedFrames = directives.get('frame-src')
    ?? directives.get('child-src')
    ?? directives.get('default-src');
  expect(allowedFrames).toEqual([demoOrigin]);
  expect(demoOrigin).toBe('https://app.supademo.com');
  expect(directives.get('default-src')).toEqual(["'self'"]);
  expect(directives.get('frame-ancestors')).toEqual(["'none'"]);
});
