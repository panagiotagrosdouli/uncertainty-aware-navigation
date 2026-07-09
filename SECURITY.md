# Security Policy

## Supported versions

This repository is an academic research prototype. Security updates apply to the default branch unless a release branch is explicitly created.

## Reporting a vulnerability

Please report security concerns privately by opening a GitHub security advisory if available, or by contacting the repository owner through the contact information on the GitHub profile.

Do not publicly disclose vulnerabilities before the maintainer has had a reasonable opportunity to investigate.

## Research-software threat model

The current project does not provide a deployed robot controller, network service, or safety-certified navigation stack. The main risks are:

- unsafe assumptions copied into downstream robot systems;
- malicious or malformed input files;
- dependency vulnerabilities;
- accidental publication of private datasets or logs.

## Safety disclaimer

This repository must not be used as a safety-critical navigation component without independent validation, formal review, and robot-specific testing.
