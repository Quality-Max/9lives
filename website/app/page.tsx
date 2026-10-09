import Image from 'next/image';
import { CopyButton } from './copy-button';

const installCommand = 'curl -fsSL https://9lives.run/install.sh | sh';
const pathCommand = 'export PATH="$HOME/.local/share/9lives-runner/bin:$PATH"';
const runCommand = '9l run tests/ --timeout 5m --format json';
const pythonCommand = 'uv tool install 9lives';
const runnerSite = 'https://quality-max.github.io/9lives-runner/';
const migrationGuide = 'https://github.com/Quality-Max/9lives/blob/main/docs/MIGRATING_TO_GO.md';

const healingSteps = [
  {
    number: '01',
    title: 'Plan your tests',
    copy: 'Inspect discovered specs before execution. Keep your existing Playwright configuration and assertions.',
  },
  {
    number: '02',
    title: 'Run with bounds',
    copy: 'Go owns concurrency, deadlines, cancellation, and a terminal outcome for every required test.',
  },
  {
    number: '03',
    title: 'Inspect the evidence',
    copy: 'Validated receipts distinguish completed tests from missing evidence, skips, and interrupted runs.',
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
          <a href={runnerSite}>Documentation</a>
          <a href="#ecosystem">Ecosystem</a>
          <a className="nav-github" href="https://github.com/Quality-Max/9lives-runner">
            GitHub <span aria-hidden="true">↗</span>
          </a>
        </nav>
      </header>

      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-glow" aria-hidden="true" />
        <p className="product-mark"><span aria-hidden="true">🐾</span> 9LIVES</p>
        <p className="eyebrow"><span /> Go runner · Playwright · Local execution <span /></p>
        <h1 id="hero-title">Your tests have<br /><em>nine lives.</em></h1>
        <p className="hero-copy">
          Ordinary Playwright tests. Bounded AI help. Evidence for every attempt.
          Run locally with the Go runner, keep your assertions, and inspect the result.
        </p>

        <div className="command-stack" aria-label="Quick start commands">
          <div className="command-card primary-command">
            <span className="command-label">Install the Go runner</span>
            <code>{installCommand}</code>
            <CopyButton value={installCommand} />
          </div>
          <div className="command-card">
            <span className="command-label">Add the Go binary to PATH</span>
            <code>{pathCommand}</code>
            <CopyButton value={pathCommand} />
          </div>
          <div className="command-card">
            <span className="command-label">Run your existing Playwright suite</span>
            <code>{runCommand}</code>
            <CopyButton value={runCommand} />
          </div>
        </div>

        <p className="trust-line">Apache-2.0 <span>•</span> No QualityMax account <span>•</span> macOS & Linux <span>•</span> amd64 & arm64</p>
        <p className="hero-note">
          The installer downloads a checksum-verified binary; Go and Python are not required.
          Your project needs its own Playwright dependencies and browsers.{' '}
          <a href={runnerSite}>Explore the runner</a> ·{' '}
          <a href="https://github.com/Quality-Max/9lives-runner/releases">Download a release</a> ·{' '}
          <a href={migrationGuide}>Migrate from Python</a>
        </p>
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
            Python package listed on <strong>awesome-python-testing</strong> <span aria-hidden="true">↗</span>
          </a>
        </div>
      </section>

      <section className="section" id="how-it-works" aria-labelledby="how-heading">
        <div className="section-heading">
          <p>THE EXECUTION LOOP</p>
          <h2 id="how-heading">Keep your assertions. Get the evidence.</h2>
          <span>Go runs your existing tests. Add SDK steps and bounded goals when you need them; explicit assertions remain the test oracle.</span>
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
            <strong>A pass has a precise meaning.</strong>
            <p>A passing receipt means assertions passed and execution evidence was validated. It does not prove full requirement coverage. Native selector healing is experimental and preserves assertions.</p>
          </div>
        </div>
      </section>

      <section className="framework-strip" aria-label="Supported test frameworks">
        <span>GO RUNNER</span><i>+</i><span>PLAYWRIGHT</span><i>+</i><span>OPTIONAL SDK</span>
      </section>

      <section className="section" id="python" aria-labelledby="python-heading">
        <div className="section-heading">
          <p>EXISTING PYTHON WORKFLOWS</p>
          <h2 id="python-heading">Python is in maintenance mode.</h2>
          <span>Use Go for new Playwright projects. Python continues to receive security, correctness, and compatibility fixes; no removal date has been set.</span>
        </div>
        <p className="compatibility-copy">
          Keep Python for MCP, watch and history reports, Cypress/Selenium, standalone-spec
          scaffolding, and existing Action or pre-commit integrations. Go&apos;s <code>9l heal</code>{' '}
          still delegates to Python; <code>heal-native</code> is an experimental, narrower alternative.
        </p>
        <div className="inline-command">
          <code>{pythonCommand}</code>
          <CopyButton value={pythonCommand} />
        </div>
        <p className="compatibility-copy">
          Select Python explicitly with <code>9lives</code> or <code>python -m ninelives.cli</code>.
          Both distributions provide <code>9l</code>, so check <code>9l --version</code> before migrating scripts.{' '}
          <a href={migrationGuide}>Read the migration guide</a> ·{' '}
          <a href="https://github.com/Quality-Max/9lives">Python source and compatibility docs</a>
        </p>
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
        <a href={runnerSite}>See the Go runner in action <span aria-hidden="true">↗</span></a>
      </section>

      <footer>
        <a className="qualitymax-brand" href="https://qualitymax.io" aria-label="QualityMax home">
          <Image src="https://qualitymax.io/static/img/qualitymax-logo-white.png" alt="QualityMax" width={200} height={30} unoptimized />
        </a>
        <p>Local Playwright execution with attributable evidence.</p>
        <span>© 2026 QualityMax</span>
      </footer>
    </main>
  );
}
