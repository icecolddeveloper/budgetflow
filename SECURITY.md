# Security Policy

Thank you for helping keep BudgetFlow and its users safe.

## Supported Versions

BudgetFlow is in active development; only the latest commit on `main` is supported. Please test reports against the current `main` before submitting.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security reports.**

Report vulnerabilities privately through one of:

- GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) on this repository, or
- Email the maintainer listed on the GitHub profile of this repo's owner.

Please include:

- A clear description of the issue and its impact
- Steps to reproduce, ideally with a minimal proof of concept
- The affected commit SHA or branch
- Your name or handle for credit (optional)

## What to Expect

- **Acknowledgement:** within 3 business days of your report
- **Initial assessment:** within 7 business days
- **Fix and disclosure:** coordinated with the reporter; timeline depends on severity and complexity

Please give us a reasonable window to remediate before any public disclosure.

## Out of Scope

The following are generally not accepted as vulnerabilities:

- Reports against third-party dependencies without a working PoC against BudgetFlow
- Findings that require a compromised user device, browser, or account
- Missing security headers on local development servers
- Social engineering, physical attacks, or denial-of-service via volumetric traffic
- Issues only reproducible with `DEBUG=True` (a development-only mode)

## Safe Harbor

Good-faith security research conducted in accordance with this policy is welcome. We will not pursue legal action against researchers who:

- Make a good-faith effort to avoid privacy violations, data destruction, and service disruption
- Only interact with accounts they own or have explicit permission to access
- Report findings privately and give us reasonable time to remediate before public disclosure
