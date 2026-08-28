import { NextResponse, type NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
  const acceptsHtml = request.headers.get('accept')?.includes('text/html');
  const canRedirectToInstaller = request.method === 'GET' || request.method === 'HEAD';

  if (canRedirectToInstaller && !acceptsHtml) {
    return NextResponse.redirect(new URL('/install.sh', request.url), 307);
  }

  return NextResponse.next();
}

export const config = { matcher: ['/'] };
