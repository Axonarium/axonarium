# Succession

This file lists every account the project depends on, who holds it, and how to hand it over. The aim is for the project to survive any one person leaving: every account belongs to the project, and at least two people should hold each one.

## Accounts

| Account | Purpose | Holder | Second holder | Renewal | Notes |
| --- | --- | --- | --- | --- | --- |
| GitHub organization `axonarium` | Repo, issues, CI, secrets | Tyler Banks (@tjbanks) | None yet | n/a | Organization does not yet require 2FA |
| axonarium.com | Domain | Tyler Banks (@tjbanks) | None yet | GoDaddy; registered 2026-10-02, expires 2029-10-02; keep auto-renew on | DNS on Cloudflare |
| axonarium.org | Domain | Tyler Banks (@tjbanks) | None yet | GoDaddy; registered 2026-10-02, expires 2027-10-02; keep auto-renew on | DNS at GoDaddy |
| Cloudflare | DNS for axonarium.com; Email Routing for admin@axonarium.com | Tyler Banks (@tjbanks) | None yet | n/a | |
| admin@axonarium.com | Project email alias used for every account | Tyler Banks (@tjbanks) | None yet | n/a | Forwarded by Cloudflare Email Routing |
| npm organization `axonarium` | The `@axonarium` scope, for the MCP server | Tyler Banks (@tjbanks) | None yet | n/a | |
| PyPI organization `axonarium` | The Python client | Tyler Banks (@tjbanks) | None yet | n/a | The project name `axonarium` is claimed by the first upload, not by the organization |

## Not created yet

An LLM provider (API key with a spending cap) and Zenodo (release DOIs). Add a row for each when it is created, and rows for Vercel (site) and Supabase (database and API), which exist but aren't listed yet: their holders, second holders and renewal terms are the maintainer's to record.

## Handing over an account

1. Add the successor as a second holder.
2. Confirm they can sign in and act.
3. Transfer ownership, or remove the departing holder.
4. Update this file by pull request.

## Credentials

Credentials live in each holder's password manager. They are never committed, or pasted into issues, pull requests or chats.
