# Audit approfondi OptiBoard — Architecture · Synchronisation · SaaS · On-Premise
_Date : 2026-06-10 — périmètre : backend FastAPI, frontend React, agent ETL C#, installeur, déploiement cloud, licensing._

> **Statut (2026-06-11)** : le **lot sécurité non-cassant** des failles 🔴 1-6 ci-dessous a été **implémenté et vérifié** (hachage bcrypt rétro-compatible, gardes `require_admin`/`require_superadmin`, machine_id + plafond de grace + retrait du bypass DEBUG, secrets retirés des fichiers livrés). Reste en attente de décision : la **signature asymétrique de licence** (cassante, rollout coordonné), la **rotation des secrets exposés** (action ops), et le **balayage des ~50 scripts de dev**. Rebuild Cython requis avant de générer un nouvel installeur.

## Verdict global

OptiBoard est un produit **fonctionnellement riche et architecturalement cohérent** (multi-tenant propre, pooling de connexions, ETL incrémental performant, CI/CD cloud). Mais il porte une **dette de sécurité critique sur 3 points vérifiés** qui doivent être traités avant toute montée en charge commerciale, et une **dette de maintenabilité** (fichiers monolithiques, duplication, ~40 scripts fix/diag non versionnés) qui ralentit déjà le développement.

| Axe | Note | Synthèse |
|---|---|---|
| Architecture backend | 6.5/10 | Solide multi-tenant, mais authz incomplète + monolithes routes |
| Synchronisation / ETL | 6.5/10 | ETL perfomant, mais pas d'idempotence ni de versioning catalog |
| SaaS (cloud) | 6/10 | CI/CD ok, mais `latest` partout, pas de tests, secrets manuels |
| On-Premise | 5/10 | Packaging propre, mais licensing contournable + pas d'auto-update |
| Frontend | 6/10 | Bon code splitting, mais fichiers 1900+ lignes, tests < 5% |

---

## 🔴 Failles critiques VÉRIFIÉES dans le code (à corriger en priorité)

Ces points ont été confirmés par lecture directe du source, pas seulement déduits.

### 1. Licence contournable — grace mode reconduit à l'infini
`app/services/license_service.py:386-401` : quand le serveur de licence est injoignable et que le cache local a expiré, le code **reconduit automatiquement** la grace de 7 jours et ré-écrit le cache. Conséquence : débrancher le réseau = licence valide indéfiniment.

### 2. Secret de signature HMAC en clair dans un fichier versionné
`.env.production.example:35` contient la vraie valeur :
`LICENSE_SIGNING_SECRET=F36XJAyo4dHrXMtcDH_...` (présent aussi dans `.env.example` et `FIX_LICENSE.bat`). Quiconque a le repo peut **forger des licences premium valides**.

### 3. `machine_id` non vérifié en mode hors-ligne
`license_service.py:344-360` : en validation offline, la signature HMAC est vérifiée mais le `mid` du payload n'est **jamais comparé** au `get_machine_id()` réel. Une même licence fonctionne sur N machines.

### 4. Mots de passe en SHA256 nu (sans sel, sans itération)
`app/routes/auth_multitenant.py:120-121` : `hashlib.sha256(password.encode()).hexdigest()`. Vulnérable aux rainbow tables et au brute-force GPU. Comparaison via `==` (timing attack théorique). À migrer vers bcrypt/argon2.

### 5. Routes `/api/dwh-admin/*` sans contrôle de rôle
`app/routes/dwh_admin.py:41` (`APIRouter(prefix="/api")` sans `dependencies=`) et `dwh_admin_create:1664` n'a aucune vérification admin. Le middleware ne fait que valider la session, pas le rôle. **Tout utilisateur authentifié** peut créer/modifier un DWH et y injecter des credentials Sage.

### 6. SQL en f-string sur des identifiants (injection résiduelle)
`app/routes/demo_portal.py:70` (`CREATE DATABASE [{DEMO_DB_NAME}]`), `datasource_templates.py:1340` (`SELECT DISTINCT {column}`), `parameter_resolver.py:200-226` (`inject_params` fait du `str.replace` au lieu de paramètres liés). Risque limité aujourd'hui (valeurs internes) mais fragile.

---

## Axe 1 — Architecture

### État
- Backend : **63 600 lignes Python**, **73 routeurs**. Multi-tenant via ContextVars async-safe (`database_unified.py`), pooling sémaphore (20 conn.), routage central/`OptiBoard_<CODE>`/`DWH_<CODE>` via `APP_ClientDB`. Tunnels SSH supportés.
- Tests présents mais partiels (`tests/test_auth_security.py`, `test_multitenant.py`) — routes admin non couvertes.

### Faiblesses
- **Monolithes** : `etl_agents.py` 6 487 lignes, `pivot_v2.py` 3 119, `dwh_admin.py` 2 469, `setup.py` 1 956. Top 5 = 17 600 lignes.
- **Duplication** : pattern `cursor.execute → zip(columns,row)` recopié 50+ fois au lieu d'un `execute_dwh()` partagé.
- **Logique métier dans les routes** plutôt que dans `services/` → faible réutilisation, tests difficiles.
- **Isolation tenant non re-validée par route** : le header `X-DWH-Code` est accepté par le middleware ; aucune route ne vérifie que `user_id ∈ dwh_code`. Risque d'accès croisé si un token de session est rejoué avec un autre `X-DWH-Code`.
- **Cache** : clés MD5, **pas de namespacing par tenant** (`cache.py:23-26`) → risque de collision/fuite inter-tenant.

### Améliorations proposées
1. **Garde d'autorisation centralisé** : `dependencies=[Depends(require_admin)]` sur les routeurs `dwh_admin`, `admin_*`, `master_publish`, `sql_jobs`. Ajouter la vérif `user ∈ dwh_code` dans le middleware tenant.
2. **Couche d'accès données unique** : factoriser `execute_dwh/execute_central/execute_client` + un mapper ligne→dict, supprimer la duplication.
3. **Découper les monolithes** : extraire `etl_agents.py` en sous-modules (registration, heartbeat, tables, proposals), idem `pivot_v2`.
4. **Cache par tenant** : préfixer les clés `cache:{dwh_code}:{sha256(query)}` et invalider après chaque ETL.
5. **SAST en CI** : Bandit + Semgrep pour bloquer les f-strings SQL et secrets en dur.

---

## Axe 2 — Synchronisation / ETL

### Flux
```
Sage → Agent C# (SageETLAgent) → POST /ingest → DWH client     (données)
Central OptiBoard_SaaS → /api/master/* → update_manager → client (catalogue)
```
Agent C# : config JSON chiffrée AES-256-GCM, heartbeat 30 s, extraction persistante Sage (retry 3×), `fast_executemany` (batch 5000), staging + MERGE incrémental, watermarks.

### Points forts
- ETL incrémental avec watermark (reprise au dernier point), bulk insert performant, retry transient côté agent, logs structurés, chiffrement des requêtes source.

### Faiblesses
- **Pas d'idempotence agent→backend** : pas de `X-Request-Id`/clé d'idempotence ; un batch rejoué peut dupliquer ou échouer en PK violation (`etl_multitenant.py:349-357`, `data_ingestion.py`).
- **Catalogue sans versioning** : `master_export.py` n'expose ni version ni checksum (sauf etl-tables) ; `update_manager` compare par `code` seulement → conflits master/local non détectés. `is_customized=1` est binaire (tout-ou-rien) : un dashboard personnalisé ne reçoit jamais les correctifs.
- **Publication sans transaction globale ni verrou** : `master_publish.py:360-390` boucle INSERT sans `BEGIN TRAN` global ni lock distribué ; un `/publish-all` interrompu laisse un état partiel.
- **Credentials en clair dans des scripts** : `REPUBLISH_ETL_RADICAL.py` et `GENERATE_AGENT_CONFIG.py` embarquent `sa/SQL@2019` et la clé AES `kasoft_optiboard_etl_key_2026!!!`.
- **Polling 30 s** : latence jusqu'à 60 s pour propager un ordre ; coûteux à l'échelle (1000 agents = 2000 req/min).
- **Pas de file de reprise** côté backend : un sync échoué est loggé mais pas rejoué.

### Améliorations proposées
1. **Idempotence** : clé `X-Request-Id` par batch + table `ETL_IngestLog(request_id UNIQUE)` ; MERGE avec checksum de ligne (`WHEN MATCHED AND hash<>? THEN UPDATE`).
2. **Versioning catalogue** : ajouter `version` + `content_hash` sur chaque entité master ; `update_manager` compare les hash et marque les conflits (`needs_review`) au lieu de skip silencieux.
3. **Merge à 3 voies pour `is_customized`** : distinguer « champ personnalisé » de « entité gelée » pour propager les correctifs sans écraser le custom.
4. **Transaction + verrou** sur `/publish-all` (lock applicatif en table ou advisory lock SQL).
5. **Secrets hors code** : déplacer toutes les chaînes de connexion et la clé AES vers `.env`/coffre ; rotation de la clé agent.
6. **Push plutôt que poll** : à terme, un canal SignalR/WebSocket (l'agent est déjà .NET) ou réduire le heartbeat avec backoff ; au minimum un endpoint « ordres en attente » consommé immédiatement.

---

## Axe 3 — SaaS (cloud)

### État
GitHub Actions → build images Docker → GHCR → SSH deploy → docker-compose + Nginx + Watchtower. Healthchecks présents, reverse proxy TLS.

### Faiblesses
- **Tag `latest` partout** (`docker-compose.prod.yml:11,43`) → rollback impossible sans retrouver le SHA.
- **Watchtower auto-update toutes les 5 min sans garde** → un build cassé part en prod sans validation ni rollback.
- **Aucun test en CI** : la suite `tests/` existe mais n'est jamais lancée ; pas de lint, pas de scan de dépendances (Dependabot/Snyk).
- **Migrations DB non versionnées** : `sql/001..010_*.sql` sans table `_migrations`, exécution ad-hoc, ordre non garanti. Symptôme : ~40 scripts `check_*/fix_*/diag_*.py` non versionnés à la racine backend (dont `check_encours` en 4 versions).
- **Secrets manuels** : `.env` posé à la main sur le serveur, aucune rotation, pas de coffre.
- **Renouvellement TLS manuel** (certbot) sans alerte d'expiration.

### Améliorations proposées
1. **Images taggées par version sémantique + SHA** ; déploiement explicite, Watchtower en notification-only (pas auto-apply en prod).
2. **CI = tests + lint + SAST + scan deps** bloquants avant build ; coverage minimal sur auth/multitenant/licence.
3. **Migrations versionnées** : adopter un outil (Alembic-like ou scripts numérotés + table `_migrations(name, hash, applied_at)`), interdire l'exécution hors-ordre. Reclasser les `fix_*/diag_*` en migrations ou les supprimer.
4. **Gestion de secrets** : Docker secrets / SOPS / coffre ; retirer les vraies valeurs des `.env.*.example`.
5. **TLS automatisé** (certbot renew + hook reload Nginx) + alerte d'expiration.

---

## Axe 4 — On-Premise

### État
Pipeline 7 étapes : Python 3.11 embedded + deps → patch `python311._pth` → copie `dist_client/` (Cython) + `dist/` (Vite) → Inno Setup → service NSSM. Protection Cython des `services/routes/middleware`.

### Faiblesses
- **Licensing contournable** (cf. failles 1-3 ci-dessus) : grace infinie, secret partagé en clair, machine_id ignoré offline, et `DEBUG=True` désactive tout (`license.py:60-78`).
- **Pas d'auto-update binaire** : `update_manager.py` ne met à jour que le **catalogue**, pas le code. Les clients restent sur d'anciennes versions non patchées (failles non corrigées chez eux).
- **Téléchargements installeur sans vérification d'intégrité** : `build_installer.bat:77-78` télécharge Python/NSSM sans checksum SHA256 (risque MITM).
- **Installeur non signé** (`OptiBoard.iss`) : pas de signature Authenticode → SmartScreen + risque de substitution.
- **Protection Cython incomplète** : `schemas.py` (tout le modèle de données) reste en `.py` clair ; échec de compilation = fallback silencieux en `.py` (`build_protected.py:372-382`).
- **Service NSSM sans isolation** : tourne sous le compte d'installation (souvent SYSTEM), pas de DACL restrictive sur `C:\OptiBoard\`.

### Améliorations proposées
1. **Durcir la licence** : (a) plafonner la grace cumulée (ex. 14 j max absolus, puis blocage doux), (b) **vérifier `machine_id`** dans le chemin offline, (c) **secret par client** signé par une clé serveur que le client n'a pas — passer à une signature asymétrique (le client n'a que la **clé publique**, impossible de forger), (d) neutraliser le bypass `DEBUG` en build release.
2. **Auto-update binaire** : endpoint `/api/updates/binary/check` (version + hash + URL signée) ; updater qui télécharge, vérifie la signature, et relance le service.
3. **Intégrité installeur** : vérifier SHA256 des ZIP téléchargés ; **signer l'exe** (Authenticode).
4. **Signature asymétrique des licences** (Ed25519/RSA) : élimine le partage de secret — la faille #2 disparaît structurellement.
5. **Étendre la protection Cython** aux schémas (séparer les modèles Pydantic non compilables des structures compilables) et **échouer le build** si un module censé être protégé reste en `.py`.

---

## Frontend (transverse)

66 700 lignes, 64 pages, 76 composants, **tests < 5 %**. Bon code splitting (`React.lazy` sur 41 routes), 8 contextes. Mais : fichiers monolithiques (`GridViewDisplay.jsx` 1 969, `DashboardBuilder.jsx` 1 901), constantes `APP_*` dupliquées entre les 4 builders, token en `localStorage` (exposition XSS), `dangerouslySetInnerHTML` dans `MobileChatPage.jsx:86`, pas d'i18n (français en dur), plotly.js (~2,8 Mo) sous-utilisé.

Améliorations : extraire les constantes et un `WidgetConfigPanel` partagé ; tests sur `AuthContext`/intercepteurs/`ProtectedRoute` ; sanitizer le markdown (DOMPurify) ; auditer le bundle (vite-plugin-visualizer) et retirer plotly si recharts suffit.

---

## Feuille de route priorisée

### P0 — Sécurité (1-2 semaines, bloquant commercial)
1. Passer à une **signature de licence asymétrique** + vérifier `machine_id` + plafonner la grace + retirer le bypass `DEBUG`. Rotation immédiate du secret exposé et purge des `.env.*.example`/`FIX_LICENSE.bat`.
2. **Garde `require_admin`** sur tous les routeurs d'administration + vérif `user ∈ dwh_code`.
3. **Migrer le hachage** vers bcrypt/argon2 (avec migration progressive des hash existants) + `hmac.compare_digest`.
4. Sortir tous les **secrets du code** (scripts ETL, clé AES) vers `.env`/coffre.

### P1 — Robustesse sync & déploiement (3-4 semaines)
5. **Idempotence ETL** (X-Request-Id + checksum) et **versioning du catalogue** (hash + détection de conflit).
6. **CI** : exécuter tests + lint + SAST + scan deps ; images taggées par version ; Watchtower en notify-only.
7. **Migrations DB versionnées** + table `_migrations` ; reclasser/supprimer les ~40 scripts fix/diag.

### P2 — Maintenabilité & on-prem (1-2 mois)
8. **Auto-update binaire on-premise** + installeur signé + checksums.
9. Découper les **monolithes** backend (etl_agents, pivot_v2) et frontend (builders, GridViewDisplay) ; couche data unique.
10. Cache par tenant ; i18n ; sanitization XSS ; audit bundle frontend.
