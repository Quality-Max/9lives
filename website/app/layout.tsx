import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] });
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] });

export const metadata: Metadata = {
  metadataBase: new URL('https://9lives.run'),
  title: '9Lives — Your tests have nine lives',
  description: 'Local-first self-healing QA for Playwright, Cypress, and Selenium. Heal selector drift without hiding real bugs.',
  alternates: { canonical: '/' },
  openGraph: {
    title: '9Lives — Your tests have nine lives',
    description: 'Run the failing spec, heal selector drift, verify it green, and review the diff.',
    url: 'https://9lives.run',
    siteName: '9Lives',
    type: 'website',
    images: [{ url: '/og.png', width: 1200, height: 630, alt: '9Lives — Your tests have nine lives' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: '9Lives — Your tests have nine lives',
    description: 'Local-first self-healing QA that refuses to hide real bugs.',
    images: ['/og.png'],
  },
  icons: { icon: 'https://qualitymax.io/favicon.ico' },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>{children}</body>
    </html>
  );
}
