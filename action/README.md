# 🐾 9lives GitHub Action

Self-healing QA on **your** runner, with **your** key — no account, no cloud tether, nothing leaves your CI. The report lands on the PR; healed tests can be committed straight back to the branch.

```yaml
name: 9lives
on: pull_request

permissions:
  contents: write        # only if commit-healed: true
  pull-requests: write   # for the PR comment

jobs:
  qa:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}   # needed for commit-healed
      - uses: quality-max/9lives/action@v1
        with:
          specs: "tests/**/*.spec.ts"
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          commit-healed: "true"
```

## Inputs

| input | default | what it does |
|---|---|---|
| `specs` | *(required)* | Space-separated spec paths or globs |
| `mode` | `heal` | `heal` fixes failing specs; `run` only reports |
| `anthropic-api-key` / `openai-api-key` | — | Your key for Tier 2 healing. Tier 1 (selector drift) heals with no key at all |
| `comment` | `true` | Post/update the 🐾 report comment on the PR |
| `commit-healed` | `false` | Commit healed specs back to the PR branch |

## Outputs

`status` (`passed` / `healed` / `failed`), `healed`, `failed` — use them to gate later steps.

## How this differs from the cloud-tethered alternatives

Execution happens on the runner you already pay GitHub for, healing happens with the key (or agent subscription) you already have, and the tool never sees your code — because there is no "us" to send it to. Compare: KaneAI/TestMu and BrowserStack route your tests through their metered cloud behind an account wall.
