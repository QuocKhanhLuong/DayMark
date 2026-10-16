#!/bin/zsh
cd "${0:A:h}/cloud"
exec node --env-file ../.runtime/cloud.env --import tsx scripts/create-owner.ts
