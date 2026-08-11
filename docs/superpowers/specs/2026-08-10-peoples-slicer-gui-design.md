# People's Slicer Studio — human GUI (v1)

**Date:** 2026-08-10  
**Status:** approved for implementation  
**Form factor:** local web app on `127.0.0.1` only (option A)

## Goal

A fun, premium, mom-simple UI so humans can **slice and send** without an agent,
while agents keep the headless `forge` CLI. One pipeline. MIT. No studio/cloud IP.

## Screens

1. **Drop** — file drop zone + agent cheatsheet  
2. **Prepare** — printer, auto-refit, Slice (real `slice_for`)  
3. **Send** — review findings, bed-clear confirm, Send / dry-run  

## Non-goals (v1)

Full mesh editor, cloud accounts, Telchar/RelayForge branding, secrets in-repo.

## Security

- Bind `127.0.0.1` only  
- Credentials only from env / user-owned `FORGE_CONFIG`  
- Guardian still requires explicit bed confirmation for live send  
