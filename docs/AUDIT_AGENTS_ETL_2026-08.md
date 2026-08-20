# Audit Agents ETL & DWH clients — 2026-08

Audit approfondi déclenché par le symptôme observé sur l'agent **ALEA FOOD** :
bascule entre `http://127.0.0.1:8084` (connexion refusée), un `404`, puis
`https://optiboard.kasoft.ma` (OK), champs **Agent / Clé vides**.

Ce document trace : (1) la cause racine du symptôme, (2) les faiblesses
d'architecture/sécurité, (3) ce qui a été corrigé dans le code, (4) le
**runbook de déploiement coordonné** pour les parties restantes.

---

## 1. Cause racine du symptôme

| Log observé | Cause |
|---|---|
| `serveur=http://127.0.0.1:8084` | Fichier de config agent généré avec l'URL dérivée du header `Host` de l'admin (sur 127.0.0.1) + build `binpublish_new/appsettings.json` versionné avec cette URL en dur. |
| `connexion refusée (127.0.0.1:8084)` | L'agent chez le client tape sur **sa propre machine**. |
| `Serveur HTTP 404` | Repli sur l'endpoint legacy `/api/admin/etl/agents` car `AgentId`/`ApiKey` vides. |
| Champs Agent/Clé vides | Le fichier d'import ne contenait **jamais** les identifiants → saisie manuelle obligatoire. |

---

## 2. Corrections appliquées dans le code (non déployées)

### Lot A — Correctif du symptôme (sûr, backend + repo)
- `config_multitenant.py` : nouveau réglage **`SERVER_PUBLIC_URL`** (+ persistance `.env`).
- `dwh_admin.py::dwh_admin_agent_config` : garde-fou **409** si l'URL résolue est
  loopback et que `SERVER_PUBLIC_URL` n'est pas défini (refuse de distribuer une
  config non routable au lieu d'échouer silencieusement).
- `SageETLAgent_MultiAgent/.../binpublish_new/` : **désindexé de Git**
  (`git rm --cached`, cohérent avec `.gitignore:46`) ; `appsettings.json` remis en
  template propre (`https://optiboard.kasoft.ma`, champs client vides).

### Lot B — Durcissement sécurité (backend)
- **B1 — Auth agent non contournable** (`etl_agents.py`) : nouveau
  `_enforce_agent_auth()` remplaçant les 7 gardes `if x_api_key and x_dwh_code:`
  (qui laissaient passer tout appel omettant un en-tête). Ajouté aussi sur
  `POST /agents/{id}/sync-result` et `POST /agents/{id}/push-deletions`
  (endpoint **destructif** : DELETE sur le DWH) — DWH cible désormais résolu via
  l'en-tête authentifié, plus via la table centrale divergente.
- **B3 — Clé AES externalisée** (`query_crypto.py`) : `OPTIBOARD_QUERY_AES_KEY`
  avec **repli sur la clé legacy** (comportement inchangé par défaut). La clé du
  fichier d'import (`OPTIBOARD_ETL_AES_KEY`) était déjà externalisée côté backend.

### Lot C — Enrôlement par jeton à usage unique (backend, additif)
- Nouveau module `app/routes/etl_enroll.py` :
  - Table centrale `APP_ETL_Enroll_Tokens` (auto-créée, idempotente).
  - `POST /api/admin/etl/agents/{agent_id}/enroll-token` (**require_admin**) →
    émet un jeton à usage unique lié à `(dwh_code, agent_id)`, TTL 24 h.
  - `POST /api/agents/enroll` (sous le préfixe exempt `/api/agents/`) → échange le
    jeton contre `{agent_id, api_key, dwh_code}`, **régénère** l'ApiKey (exposée une
    seule fois) et consomme le jeton.
- `dwh_admin.py::dwh_admin_agent_config?agent_id=...` embarque le jeton dans le
  fichier de config chiffré → flux mono-fichier, plus aucun copier-coller.
- Enregistré dans `run.py`.

---

## 3. Reste à faire — déploiement coordonné (NON appliqué)

> Ces items exigent un rebuild et/ou une migration sur base de production. Ne pas
> appliquer sans fenêtre de maintenance et sauvegarde préalable.

### 3.1 Rebuild backend (Cython) — OBLIGATOIRE pour activer 2 + 3
Le backend prod tourne en `.pyd`/`.pyc`. Les modifs ci-dessus ne sont actives
qu'après :
```
cd reporting-commercial\backend && build_protected.bat
# puis REBUILD_ALL.bat pour l'installeur, ou déployer dist_client
```
`etl_enroll.py` **n'a pas de modèle Pydantic lourd** mais définit `EnrollRequest`
(BaseModel) → à compiler en `.pyc` (comme `setup.py`), pas en `.pyd`. Vérifier son
classement dans `build_protected.py`.

### 3.2 Agent C# — consommer l'enrôlement + lire les clés AES (rebuild .NET)
Spec des changements (`SageETLAgent_MultiAgent/SageETLAgent/`) :
1. `Services/ApiClient.cs` : ajouter `EnrollAsync(string token)` →
   `POST /api/agents/enroll` `{token}` → stocker `agent_id`/`api_key`.
2. `Forms/MultiAgentForm.cs::ImportAgentConfig` : si le payload contient
   `enroll_token`, appeler `EnrollAsync` et écrire `AgentId`/`ApiKey` dans
   `appsettings.json` automatiquement (remplace la saisie manuelle).
3. `Services/QueryDecryptor.cs` + `MultiAgentForm.cs` (clé d'import) : lire la clé
   AES depuis `appsettings.json`/env avec repli sur la valeur legacy — permet la
   rotation alignée avec `OPTIBOARD_QUERY_AES_KEY` / `OPTIBOARD_ETL_AES_KEY`.
4. Fiabilité : `HttpClient` **singleton** (au lieu de 9 instanciations),
   discrimination 401/404/5xx, brancher `ConnectionManager` (retry/backoff) dans
   `SageEtlWorker` (aujourd'hui le service **s'arrête** si 0 agent au démarrage).

> ⚠️ Rotation des clés AES : ne définir `OPTIBOARD_QUERY_AES_KEY` côté serveur
> **qu'après** avoir déployé un agent qui lit la même clé, sinon les `source_query`
> `$enc1$` deviennent indéchiffrables par les agents legacy.

### 3.3 B2 — Chiffrement des mots de passe au repos (migration live)
`sage_password` (nécessaire à l'agent) et `dwh_password` (l'agent écrit en SQL
direct via `DwhWriter`) transitent et sont stockés **en clair**
(`APP_ETL_Agents`, `APP_ClientDB`, `APP_DWH`). L'agent en a besoin → la solution
n'est pas de les retirer mais :
1. Chiffrer **au repos** (réutiliser `query_crypto` AES-GCM, lecture tolérante au
   plaintext legacy pour migration transparente) dans `credential_resolver.py` +
   chemins INSERT/UPDATE.
2. Déchiffrer côté serveur juste avant l'envoi, sur canal **TLS obligatoire**
   (forcer HTTPS pour `/api/agents/*`).
À faire sur base de prod avec sauvegarde → hors périmètre « code seul ».

### 3.4 Durcissement rôle `/api/admin/etl/*`
`etl_agents.router` est monté **sans garde de rôle** (tout utilisateur authentifié
d'un tenant peut créer un agent / régénérer une clé). Correctif propre = **séparer**
les routes agent (`/api/agents/*`, session-optional) des routes admin
(`/api/admin/etl/*`, `require_admin`) en deux routers. Refactor à planifier.

---

## 4. Ordre de déploiement recommandé
1. Définir `SERVER_PUBLIC_URL=https://optiboard.kasoft.ma` dans le `.env` central.
2. Rebuild backend (3.1) + déployer.
3. Régénérer les fichiers de config agent avec `?agent_id=...` (jeton embarqué).
4. Déployer l'agent C# rebuildé (3.2) chez les clients ; ré-enrôlement auto.
5. Puis, fenêtre planifiée : B2 (3.3) + rotation clés AES + garde rôle (3.4).
