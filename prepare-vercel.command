#!/bin/zsh
cd "${0:A:h}"
exec python3 tools/prepare-vercel-handoff.py
