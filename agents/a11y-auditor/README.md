# Accessibility Auditor

Audits HTML, JSX, TSX, and Vue source before deployment. It checks semantic source patterns, explains real user impact, maps findings to WCAG 2.1, and offers exact fixes. Use it with axe-core or Lighthouse: those inspect the live rendered DOM and runtime/CSS behavior; this catches source issues earlier.

```bash
pip install -r requirements.txt
python agent.py --project . --rules-only
python agent.py --file components/LoginForm.jsx --output a11y-report.html
python agent.py --project . --ci-mode
```

A form with `<input placeholder="Email">` and no label is reported as CRITICAL because the placeholder disappears and assistive technology receives no programmatic name. A filename alt such as `alt="image1.png"` is reported separately from a compliant descriptive alt.

WCAG A is the baseline, AA adds the level most organizations target, and AAA is the strictest level that is not practical for every kind of content. The `--wcag-level` option records the intended target; source checks remain conservative. Accessibility laws and lawsuits, including ADA-related claims, make accessibility a real compliance concern, but the goal is usable products for disabled people rather than fear-driven compliance.
