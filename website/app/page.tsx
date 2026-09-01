import Image from 'next/image';
import { CopyButton } from './copy-button';

const installCommand = 'curl -sL 9lives.run | sh';
const healCommand = '9l heal login.spec.ts';

const healingSteps = [
  {
    number: '01',
    title: 'Run & classify',
    copy: '9Lives runs the failing spec and separates selector drift from real behavior changes.',
  },
  {
    number: '02',
    title: 'Heal the drift',
    copy: 'Stable page evidence finds the element again. Structural changes can use your existing coding-agent CLI.',
  },
  {
    number: '03',
    title: 'Verify & review',
    copy: 'The spec runs again, then you get a unified diff before anything is applied.',
  },
];

const ecosystem = [
  {
    eyebrow: 'Find defects',
    title: 'qmax-mcp',
    copy: 'Scan a live page, inspect stable locators, and generate a Playwright reproduction.',
    href: 'https://qmax.run',
  },
  {
    eyebrow: 'Ship in the cloud',
    title: 'QualityMax Cloud',
    copy: 'Hosted test management, execution, and quality intelligence for growing teams.',
    href: 'https://qualitymax.io',
  },
  {
    eyebrow: 'Code with evidence',
    title: 'qmax-code',
    copy: 'Agentic delivery loops that keep implementation, QA, and release evidence together.',
    href: 'https://github.com/Quality-Max/qmax-code',
  },
  {
    eyebrow: 'Grade your specs',
    title: 'QualityMax Grader',
    copy: 'An offline A–F quality grade for Playwright specs before they reach the repository.',
    href: 'https://github.com/Quality-Max/qualitymax-grader',
  },
  {
    eyebrow: 'Equip your agent',
    title: 'Free QA Skills',
    copy: 'Open QA skills for test quality, selectors, dependencies, accessibility, security, and more.',
    href: 'https://github.com/Quality-Max/free-qa-skills',
  },
];

export default function Home() {
  return (
    <main>
      <header className="site-header">
        <a className="qualitymax-brand" href="https://qualitymax.io" aria-label="QualityMax home">
          <Image src="https://qualitymax.io/static/img/qualitymax-logo-white.png" alt="QualityMax" width={200} height={30} unoptimized />
        </a>
        <nav aria-label="Primary navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#ecosystem">Ecosystem</a>
          <a className="nav-github" href="https://github.com/Quality-Max/9lives">
            GitHub <span aria-hidden="true">↗</span>
          </a>
        </nav>
      </header>

      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-glow" aria-hidden="true" />
        <p className="product-mark"><span aria-hidden="true">🐾</span> 9LIVES</p>
        <p className="eyebrow"><span /> Local-first self-healing QA <span /></p>
        <h1 id="hero-title">Your tests have<br /><em>nine lives.</em></h1>
        <p className="hero-copy">
          A Playwright selector drifted after your coding agent shipped a change? Run the spec,
          heal the locator, verify it green, and review the diff—without hiding a real bug.
        </p>

        <div className="command-stack" aria-label="Quick start commands">
          <div className="command-card primary-command">
            <span className="command-label">Install free</span>
            <code>{installCommand}</code>
            <CopyButton value={installCommand} />
          </div>
          <div className="command-card">
            <span className="command-label">Resurrect a spec</span>
            <code>{healCommand}</code>
            <CopyButton value={healCommand} />
          </div>
        </div>

        <p className="trust-line">MIT licensed <span>•</span> No account <span>•</span> No telemetry <span>•</span> Tier 1 works offline</p>
        <div className="featured-links">
          <a
            className="featured-link"
            href="https://aiinqa.com/ai-in-qa-issue-18/"
            target="_blank"
            rel="noreferrer"
          >
            As featured in <strong>AI in QA</strong> — Issue #18 <span aria-hidden="true">↗</span>
          </a>
          <a
            className="featured-link"
            href="https://github.com/cleder/awesome-python-testing"
            target="_blank"
            rel="noreferrer"
          >
            Listed on <strong>awesome-python-testing</strong> <span aria-hidden="true">↗</span>
          </a>
        </div>
      </section>

      <section className="section" id="how-it-works" aria-labelledby="how-heading">
        <div className="section-heading">
          <p>THE HEAL LOOP</p>
          <h2 id="how-heading">Fix drift. Keep the signal.</h2>
          <span>9Lives changes locators when the page moved. It refuses to rewrite assertions just to force green.</span>
        </div>
        <div className="step-grid">
          {healingSteps.map((step) => (
            <article className="step-card" key={step.number}>
              <span className="step-number">{step.number}</span>
              <h3>{step.title}</h3>
              <p>{step.copy}</p>
            </article>
          ))}
        </div>

        <div className="safety-banner">
          <span className="safety-icon" aria-hidden="true">!</span>
          <div>
            <strong>Assertions stay honest.</strong>
            <p>A failing assertion may be a real regression. 9Lives marks it <code>needs-human</code> instead of masking it.</p>
          </div>
        </div>
      </section>

      <section className="framework-strip" aria-label="Supported test frameworks">
        <span>PLAYWRIGHT</span><i>+</i><span>CYPRESS</span><i>+</i><span>SELENIUM</span>
      </section>

      <section className="section ecosystem-section" id="ecosystem" aria-labelledby="ecosystem-heading">
        <div className="section-heading">
          <p>THE QUALITYMAX ECOSYSTEM</p>
          <h2 id="ecosystem-heading">From first defect to lasting test.</h2>
          <span>Open local tools when you want them. Hosted QualityMax when your team needs scale.</span>
        </div>
        <div className="ecosystem-grid">
          {ecosystem.map((item) => (
            <a className="ecosystem-card" href={item.href} key={item.title}>
              <span>{item.eyebrow}</span>
              <h3>{item.title}</h3>
              <p>{item.copy}</p>
              <b aria-hidden="true">↗</b>
            </a>
          ))}
        </div>
      </section>

      <section className="final-cta">
        <p aria-hidden="true">🐾</p>
        <h2>Give your tests another life.</h2>
        <div className="inline-command">
          <code>{installCommand}</code>
          <CopyButton value={installCommand} />
        </div>
        <a href="https://github.com/Quality-Max/9lives">Read the source on GitHub <span aria-hidden="true">↗</span></a>
      </section>

      <footer>
        <a className="qualitymax-brand" href="https://qualitymax.io" aria-label="QualityMax home">
          <Image src="https://qualitymax.io/static/img/qualitymax-logo-white.png" alt="QualityMax" width={200} height={30} unoptimized />
        </a>
        <p>Open self-healing QA for the coding-agent era.</p>
        <span>© 2026 QualityMax</span>
      </footer>
    </main>
  );
}
