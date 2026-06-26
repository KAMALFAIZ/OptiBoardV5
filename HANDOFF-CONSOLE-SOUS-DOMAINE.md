# Handoff — Adapter OptiBoard à la console KASOFT + routing `{client}.kasoft.ma`

> Coller le bloc ci-dessous comme **premier message** dans une session Claude Code ouverte
> dans `D:\kasoft-platform\OptiBoard`. Mission : finaliser l'intégration à la console unique
> KASOFT et le passage de `?client=xxxx` vers `xxxx.kasoft.ma`.

---

## MISSION

Tu travailles dans le dépôt **OptiBoard** (Python FastAPI + SQL Server, décisionnel/reporting Sage),
l'un des 3 produits du parc KASOFT (avec ERP-Vision et OptiCRM). Objectif global du parc : **une console
unique** (registre clients + signature licences RS256 + monitoring) pilote les 3 produits, avec :
1. **Routing par sous-domaine** `{client}.kasoft.ma` — **supprimer tout `?client=xxxx`**.
2. **Licence unique JWT RS256** signée par la console (clé publique embarquée, fingerprint `08aa9136`).
3. **Endpoint stats** `/api/console/instance-stats` (header `X-Console-Token`) lu par la console.

## ⚠️ TRÈS IMPORTANT — NE RIEN RÉIMPLÉMENTER À L'AVEUGLE

Ce chantier a **déjà été commité** sur `main` (à re-vérifier, ne pas refaire) :
- `ee61893` routing par sous-domaine + suppression du repli `?client=`
- `5a88651` acceptation des licences KASOFT JWT RS256 (additif, repli HMAC conservé)
- `703bcf5` + `f8280e1` endpoint `/api/console/instance-stats` (monitoring console)

**Procède en 3 étapes : (1) AUDIT de l'existant, (2) COMPLÉTER seulement les manques, (3) doc de config.**
Ne réécris pas ce qui marche déjà. Ne casse pas le travail en cours (le dépôt peut avoir des modifs
non commitées — préserve-les).

## CONTRAINTES DE MÉTHODE
- **Aucune action destructive ni commit/push sans me le demander.** Explique avant d'éditer.
- Respecte le `CLAUDE.md` propre à OptiBoard (conventions du projet).
- **Deux arbres backend** : `reporting-commercial/backend/app` = **source canonique** ; `installer/payload/backend` est **synchronisé par le build** (ne pas éditer à la main, il se régénère). Travaille dans la source canonique.
- Local/on-premise (localhost ou IP) doit continuer à marcher (DWH choisi à la connexion / `DWH_CODE`).

---

## ÉTAPE 1 — AUDIT (lis et confirme l'état réel, cite fichier:ligne)

Lis ces fichiers et établis un état précis :
- `reporting-commercial/backend/app/.../tenant_context.py` — fonction d'extraction du DWH depuis le sous-domaine (`_subdomain_dwh_code`), `BASE_DOMAIN` (défaut attendu `kasoft.ma`), sous-domaines réservés (`www, app, api, portal, admin, static, cdn, mail`), ordre de précédence attendu : **header `X-DWH-Code` > sous-domaine > session > env `DWH_CODE`**, et `EXEMPT_PREFIXES` (doit contenir `/api/console`).
- `reporting-commercial/frontend/src/utils/clientCode.js` — `getClientCode()` doit dériver le code **uniquement** du sous-domaine (`_subdomainCode`), `VITE_BASE_DOMAIN` (défaut `kasoft.ma`). + `AuthContext.jsx`, `pages/LoginPage.jsx`.
- `reporting-commercial/backend/app/.../services/license_service.py` — vérif **JWT RS256 console prioritaire** (`_verify_console_jwt`, clé `app/license-public.pem`) puis repli HMAC + serveur externe `kasoft.selfip.net:44100` + grâce 30 j.
- `reporting-commercial/backend/app/routes/console_stats.py` — `GET /api/console/instance-stats`, auth `X-Console-Token`, 404 si `CONSOLE_TOKEN` absent / 401 si erroné / 200 sinon.
- `reporting-commercial/backend/app/config.py` — settings `CONSOLE_TOKEN`, `BASE_DOMAIN`, `STANDALONE_MODE`, `DWH_CODE`, `LICENSE_KEY`.
- `app/license-public.pem` — présence ; le fingerprint doit correspondre à celui d'ERP-Vision/OptiCRM (`08aa9136`).

Puis **grep** sur tout le dépôt (hors `node_modules`, `dist`, `.git`) :
- `?client=`, `args.get("client"`, `query.*client`, `request.query` → il ne doit RESTER aucun routing par query param. Les seuls résidus tolérés sont des **scripts/docs dev** (ex. `FIX_ADMIN_CLIENT.ps1` — déjà nettoyé). Liste précisément tout résidu trouvé (fichier:ligne) et dis s'il est fonctionnel ou cosmétique.
- `optiboard.ma` vs `kasoft.ma` (cohérence domaine).

**Rends un rapport d'audit** : ce qui est déjà conforme vs ce qui manque réellement. NE PASSE À L'ÉTAPE 2 que pour combler les manques constatés.

---

## ÉTAPE 2 — COMPLÉTER UNIQUEMENT LES MANQUES (code)

N'applique que ce qui n'est pas déjà fait, par exemple :
- **Routing** : si un `?client=` fonctionnel subsiste, le retirer (le DWH se résout du sous-domaine `{code}.kasoft.ma` côté back + front). Vérifier que les sous-domaines réservés ne sont pas traités comme des DWH, et que localhost/IP retombe sur `DWH_CODE`/login.
- **Stats console** : confirmer le chemin **exactement** `/api/console/instance-stats` (chemin UNIFIÉ du parc — ne pas le renommer), `X-Console-Token`, et que le router est dans `EXEMPT_PREFIXES`. Payload commun : `{ version, usersActive/Total, companiesActive/Total, license{...}, timestamp }`.
- **Licence** : confirmer que `_verify_console_jwt` (RS256) est prioritaire et que `app/license-public.pem` est bien la clé du parc.
- **Cohérence domaine** : `BASE_DOMAIN`/`VITE_BASE_DOMAIN` par défaut `kasoft.ma` (configurables).

Après toute modif Python : `python -m py_compile` sur les fichiers touchés. Front : `node --check` / build si pertinent.

---

## ÉTAPE 3 — CONFIG DE DÉPLOIEMENT SaaS (documentation, pas du code applicatif)

Documente (dans `.env.production.example` et/ou le `CLAUDE.md`/README OptiBoard) les variables à poser **par instance** pour le mode SaaS unifié :
- `BASE_DOMAIN=kasoft.ma` (back) + `VITE_BASE_DOMAIN=kasoft.ma` (front, au build)
- `CONSOLE_TOKEN=<token unique>` (active `/api/console/instance-stats`, sinon 404)
- `LICENSE_KEY=<JWT RS256 signé par la console>`
- **Ne pas** poser `STANDALONE_MODE` / `DWH_CODE` en SaaS (sinon retombe sur le DWH par défaut)

Rappelle les pré-requis infra (hors dépôt) : **DNS wildcard `*.kasoft.ma`** + **certificat TLS wildcard `*.kasoft.ma`**.

## NE PAS FAIRE sans décision explicite
- **Décommissionner** le serveur de licence externe `kasoft.selfip.net:44100` (c'est le repli HMAC fonctionnel — décision produit, pas un nettoyage).
- Toucher à `installer/payload/**` à la main (régénéré par le build).
- Committer / pousser.

## CRITÈRES D'ACCEPTATION
- `grep -ri "?client="` (hors scripts/docs dev) = **0** route fonctionnelle.
- `{code}.kasoft.ma` → résout le DWH correspondant ; sous-domaines réservés ignorés ; localhost/IP → fallback.
- `GET /api/console/instance-stats` : **404** sans `CONSOLE_TOKEN`, **401** si token erroné, **200** + JSON sinon.
- Licence JWT RS256 du parc acceptée (clé `08aa9136`) ; repli HMAC intact.
- `py_compile` / build OK. Aucun fichier WIP existant écrasé.

Commence par l'ÉTAPE 1 (audit) et présente-moi le rapport avant de modifier quoi que ce soit.
