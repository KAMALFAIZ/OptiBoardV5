# Changelog — OptiBoard

Toutes les évolutions notables du projet sont documentées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/) ; versionnement [SemVer](https://semver.org/lang/fr/) (MAJEUR.MINEUR.CORRECTIF).

## [Non publié]

### Ajouté
- Outillage de sauvegarde/restauration des bases SQL Server (`scripts/backup/`) :
  sauvegarde quotidienne planifiée de `OptiBoard_SaaS` + toutes les bases clients,
  vérification `RESTORE VERIFYONLY`, rétention 30 jours, script de restauration avec `MOVE` automatique.
  Livré dans l'installeur (déployé à la racine `C:\OptiBoard\`). Voir `docs/BACKUP_RESTORE.md`.
- `CHANGELOG.md` + script de montée de version `scripts/release/bump_version.ps1`
  (synchronise package.json, run.py, OptiBoard.iss et le changelog).
- Rotation des logs NSSM appliquée aux installations existantes via `FIX_SERVICE.bat`.

### Sécurité
- nginx : en-têtes `Strict-Transport-Security` (HSTS), `Content-Security-Policy`,
  `Permissions-Policy` + rate limiting sur `/api/` et `/api/auth/login` (anti brute-force).

### CI/CD
- `deploy.yml` : les tests backend hermétiques bloquent désormais le déploiement
  production (job `tests` requis avant `deploy`).

## [1.0.0] — 2026-06-06

### Version initiale
- Plateforme BI multi-tenant (FastAPI + React + SQL Server) : dashboards, grilles,
  pivots, tableurs, ventes/stocks/recouvrement/comptabilité/budget, assistant IA
  multi-providers, alertes multi-canaux (email/WhatsApp/Telegram), planification
  de rapports, agent ETL Sage C#, installeur Windows (Inno Setup + NSSM),
  wizard de setup 6 étapes, licence avec mode grâce plafonné.
