import Image from 'next/image';
import { CopyButton } from './copy-button';

const installCommand = 'curl -fsSL https://9lives.run/install.sh | sh';
const pathCommand = 'export PATH="$HOME/.local/share/9lives-runner/bin:$PATH"';
const runCommand = '9l run tests/ --timeout 5m --format json';
const scanCommand = '9l scan https://your-app.dev --format markdown';
const mcpCommand = 'claude mcp add 9lives -- 9l mcp';
const pythonCommand = 'uv tool install 9lives';
const runnerSite = 'https://quality-max.github.io/9lives-runner/';
const migrationGuide = 'https://github.com/Quality-Max/9lives/blob/main/docs/MIGRATING_TO_GO.md';
const interactiveDemo = 'https://app.supademo.com/demo/cmv43czgb0031wi0jzgno1y8r?utm_source=link';

const memes = [
  {
    file: 'button-rename-launch',
    title: 'One button. A whole afternoon.',
    alt: 'One button rename. The black Qmax kitten slumps over a failing laptop labeled My afternoon, then sits calmly beside a passing laptop labeled After the re-run. Repair the locator. Keep the assertion.',
    copy: 'A locator repair still has to pass the original assertions.',
  },
  {
    file: 'harry-potter-launch',
    title: 'Less panic. More proof.',
    alt: 'Magical-school cat parody: You\'re a tester, Harry. The black Qmax kitten in wizard glasses faces a failing laptop, then a passing one. Locatorus Brokenus becomes Rerunus Verifiedus. Even magic needs a re-run.',
    copy: 'Even a little UI magic deserves a real test result.',
  },
  {
    file: 'lotr-launch',
    title: 'A tiny change. An epic detour.',
    alt: 'Epic fantasy cat parody: One does not simply rename a button. The black Qmax kitten wears a grey wizard cloak beside a failing laptop, then reviews a passing result. Repair. Re-run. Review.',
    copy: 'The journey ends with evidence, not a hopeful green badge.',
  },
  {
    file: 'batman-catwoman-launch',
    title: 'Your tests deserve nine lives.',
    alt: 'Original feline superhero parody: The button moved. A black kitten in a bat-eared cape sees FAIL; the Qmax kitten in a violet mask sees PASS. Another long night. Nine lives. Keep the assertion. Verify the fix.',
    copy: 'Keep the assertion. Make the fix earn its green.',
  },
];

const pageChecks = [
  ['console', 'JavaScript errors, warnings, and failed requests'],
  ['links', 'Broken and redirecting links'],
  ['accessibility', 'Missing alt text, unlabelled controls, heading structure'],
  ['performance', 'Core Web Vitals: LCP, CLS, TTFB, FCP'],
  ['seo', 'Title and meta description'],
  ['security_headers', 'CSP, HSTS, X-Content-Type-Options, Referrer-Policy'],
  ['cookies', 'Cookie flags, third-party cookies, trackers before consent'],
  ['mixed_content', 'HTTP resources and form actions on HTTPS pages'],
  ['weight', 'Transfer size, requests, render-blocking and oversized assets'],
];

const verificationSteps = [
  {
    number: '01',
    title: 'scan_url — find what broke',
    copy: 'Nine checks from one Chromium page load, with graded findings, reproduction steps, and suggested fixes.',
  },
  {
    number: '02',
    title: 'inspect_page — see what a test can use',
    copy: 'Page structure, accessible names, and ranked Playwright locators with a stability verdict for each control.',
  },
  {
    number: '03',
    title: 'generate_playwright_repro — keep the failure',
    copy: 'A deterministic, reviewable spec for a finding, written inside the project. Nothing runs until you choose.',
  },
  {
    number: '04',
    title: 'run_test or confirm_finding — prove it',
    copy: 'Execute the repro with validated receipts, or check that it fails before the fix and passes after it.',
  },
];

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
          <a href="#page-checks">Page checks</a>
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
            <span className="command-label">Install on macOS or Linux</span>
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
          <div className="command-card">
            <span className="command-label">Check the page you changed</span>
            <code>{scanCommand}</code>
            <CopyButton value={scanCommand} />
          </div>
        </div>

        <p className="trust-line">Apache-2.0 <span>•</span> No QualityMax account <span>•</span> Linux · macOS · Windows <span>•</span> x64 & ARM64</p>
        <p className="hero-note">One local Playwright workflow across your team’s machines. The Go runner v0.4.0 has native binaries for all three platforms.</p>
        <p className="hero-note">Built by QualityMax without any external funding. Our ambition: become a leading name in modern test automation, with practical AI and proof you can inspect.</p>
        <p className="hero-note">
          The macOS/Linux shell installer downloads a checksum-verified binary; Go and Python are not required.
          Windows users: follow the <a href="https://github.com/Quality-Max/9lives-runner/blob/main/docs/install.md#windows">ZIP install guide</a>.
          Windows provider CLI shell integrations remain unqualified.
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

      <section className="section feature-tour" id="features" aria-labelledby="feature-tour-heading">
        <div className="section-heading">
          <p>THE 9LIVES FEATURE LOOP</p>
          <h2 id="feature-tour-heading">Create. Assess. Run. Heal. Challenge.</h2>
          <span>Explore the 9lives workflow in an interactive demo, then try the runner on your own Playwright tests. Native healing is experimental; a demo is not a comparative benchmark.</span>
        </div>
        <div className="interactive-demo">
          <iframe
            src="https://app.supademo.com/embed/cmv43czgb0031wi0jzgno1y8r?embed_v=2&utm_source=embed"
            loading="lazy"
            title="9lives: repair a broken Playwright locator"
            allow="clipboard-write"
            allowFullScreen
          />
        </div>
        <p className="hero-note"><a href={interactiveDemo} target="_blank" rel="noreferrer">Open the demo in a new tab ↗</a></p>
        <div className="feature-grid">
          <article key="Agent-assisted test generation"><h3>Agent-assisted test generation</h3><p>Your coding agent drafts Playwright specs from reviewed requirements. Capture creation provenance before assessing and executing them.</p></article>
          <article key="Test assessment"><h3>Test assessment</h3><p>9l assess flags fixed waits, skips, missing or unawaited assertions, and requirement-mapping gaps. Static findings are advisory.</p></article>
          <article key="Local execution"><h3>Local execution</h3><p>Plan and run your existing Playwright suite with bounded concurrency, deadlines, cancellation, and attributable terminal receipts.</p></article>
          <article key="Locator healing"><h3>Locator healing</h3><p>Experimental native healing preserves assertions and verifies supported locator-only candidates in isolation before review and acceptance.</p></article>
          <article key="Fault testing & confirmation"><h3>Fault testing &amp; confirmation</h3><p>Experimental prove injects fetch/XHR faults; confirm compares a reproduction on unfixed and fixed Git revisions. Inspect what each result establishes.</p></article>
          <article key="Page checks"><h3>Page checks</h3><p>9l scan reports console, link, accessibility, vitals, SEO, header, cookie, mixed-content, and weight findings from one page load; 9l inspect ranks locators. Observations, not test results.</p></article>
          <article key="Agent tools & SDK"><h3>Agent tools &amp; SDK</h3><p>Native MCP exposes run, heal, assess, confirm, page scan, page inspection, and repro tools. The optional SDK adds named steps and bounded goals; goal completion remains unverified.</p></article>
        </div>
        <p className="hero-note"><a href="https://github.com/Quality-Max/9lives-runner/blob/main/docs/README.md">Read all features and limits →</a></p>
      </section>

      <section className="section" id="page-checks" aria-labelledby="page-checks-heading">
        <div className="section-heading">
          <p>THE VERIFICATION LOOP</p>
          <h2 id="page-checks-heading">From “looks done” to evidence it works.</h2>
          <span>Give your coding agent independent evidence from the page before it declares a web change done. Local, no account, and the same checks from the CLI or MCP.</span>
        </div>
        <div className="step-grid">
          {verificationSteps.map((step) => (
            <article className="step-card" key={step.number}>
              <span className="step-number">{step.number}</span>
              <h3>{step.title}</h3>
              <p>{step.copy}</p>
            </article>
          ))}
        </div>
        <div className="feature-grid">
          {pageChecks.map(([name, copy]) => (
            <article key={name}><h3><code>{name}</code></h3><p>{copy}</p></article>
          ))}
        </div>
        <div className="inline-command">
          <code>{mcpCommand}</code>
          <CopyButton value={mcpCommand} />
        </div>
        <p className="compatibility-copy">
          <code>--baseline</code> with <code>--fail-on-new</code> gates a pipeline on new findings only.
          Pages behind a login use a Playwright storage-state file with explicit consent; loopback targets
          need <code>--allow-private-network</code>. One cold page load is not field data, and INP is not measured.
          These checks were previously the separate qmax-mcp npm server.{' '}
          <a href="https://github.com/Quality-Max/9lives-runner#check-the-page-you-changed">Read the page-check guide</a>
        </p>
      </section>

      <section className="section meme-section" id="memes" aria-labelledby="meme-heading">
        <div className="section-heading">
          <p>SMALL UI CHANGE. BIG TEST DRAMA.</p>
          <h2 id="meme-heading">Nine lives. Same test drama.</h2>
          <span>The launch kitten has been through it too. Open a meme and send it to the teammate who knows the feeling.</span>
        </div>
        <div className="meme-grid">
          {memes.map((meme) => (
            <figure className="meme-card" key={meme.file}>
              <a href={`/memes/${meme.file}.webp`} aria-label={`Open meme: ${meme.title}`}>
                <Image src={`/memes/${meme.file}.webp`} alt={meme.alt} width={1024} height={1024} unoptimized />
              </a>
              <figcaption><strong>{meme.title}</strong><p>{meme.copy}</p></figcaption>
            </figure>
          ))}
        </div>
        <p className="meme-note">Illustrated developer jokes. Native healing is experimental; these images are not benchmarks. <a href="https://qualitymax.io/blog/9lives-playwright-field-report">Read the field report →</a></p>
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
          Keep Python for its existing MCP contracts, watch and history reports, Cypress/Selenium,
          standalone-spec scaffolding, and existing Action or pre-commit integrations.
          Go v0.4 has native <code>9l heal</code>, <code>9l mcp</code>, <code>9l scan</code>, and <code>9l inspect</code>;
          native healing is experimental. The website shell installer installs Go v0.4.0.
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

      <footer id="legal">
        <a className="qualitymax-brand" href="https://qualitymax.io" aria-label="QualityMax home">
          <Image src="https://qualitymax.io/static/img/qualitymax-logo-white.png" alt="QualityMax" width={200} height={30} unoptimized />
        </a>
        <p>Local Playwright execution with attributable evidence.</p>
        <span>© 2026 QualityMax</span>
        <nav className="legal-links" aria-label="Legal information">
          <a href="https://qualitymax.io/legal">Imprint / Impressum</a>
          <a href="https://qualitymax.io/privacy">Privacy / Datenschutz</a>
          <a href="https://qualitymax.io/terms">Terms / Nutzungsbedingungen</a>
        </nav>
        <div className="service-legal">
          <p>For QualityMax service contracts:</p>
          <nav className="legal-links" aria-label="QualityMax contract information">
            <a href="https://qualitymax.io/legal/widerruf">Withdrawal / Widerruf</a>
            <a href="https://qualitymax.io/cancel-contract">Cancel contract / Vertrag kündigen</a>
          </nav>
        </div>
        <p className="legal-note">Legal information is maintained on qualitymax.io.</p>
      </footer>
    </main>
  );
}
