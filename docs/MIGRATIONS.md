# Migrations SQL — Guide

Runner versionné : `reporting-commercial/backend/migrate.py`.
Répertoire des migrations : `reporting-commercial/backend/app/sql/migrations/`.

> Les schémas `app/sql/001_central_schema.sql`, `002_client_schema.sql`,
> `003_migration_new_schema.sql` et `pivot_v2_schema.sql` sont l'**initialisation**
> exécutée par le wizard de setup (`setup.py`) — ils sont **hors périmètre** du runner.

## Règle d'or

**Toute évolution de schéma passe par une migration.** Plus de scripts `fix_*.py`
ou de SQL passé à la main : créer un fichier dans `app/sql/migrations/` et
l'appliquer via `migrate.py`. C'est la seule façon de garantir que toutes les
installations (dev, clients) convergent vers le même schéma.

## Créer une migration

1. **Nommage** : `NNN_description.sql` — `NNN` est un numéro séquentiel à 3 chiffres
   (suivant le plus grand existant), `description` en snake_case.
   Exemple : `013_add_budget_axes.sql`. L'ordre d'application est l'ordre
   **lexicographique des noms de fichiers** : ne jamais réutiliser un numéro.
2. **Idempotence recommandée** : protéger les DDL par des gardes
   (`IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='...')`,
   `IF NOT EXISTS (... sys.columns ...)`, `IF OBJECT_ID(...) IS NULL`).
   Indispensable pour les installations existantes baselinées.
3. **Séparateur `GO`** : supporté (seul sur sa ligne, insensible à la casse,
   éventuellement suivi d'un nombre). Obligatoire quand un batch doit être compilé
   séparément (ex. `CREATE PROCEDURE`, `CREATE VIEW` après un autre statement).
   Note : le compteur de répétition (`GO 5`) est traité comme un simple séparateur.
4. **Encodage** : UTF-8 (BOM toléré). Le hash est calculé après normalisation des
   fins de ligne (CRLF → LF), donc Windows/Linux et la config Git `autocrlf`
   n'affectent pas le hash.

### ⚠️ Ne JAMAIS modifier une migration déjà appliquée

Chaque fichier est enregistré dans `APP_Migrations` (base centrale) avec son hash
SHA-256. Si un fichier déjà appliqué est modifié, `migrate.py` s'arrête en erreur :
le schéma réel divergerait silencieusement entre installations. Pour corriger une
migration : **créer une nouvelle migration** (`NNN_fix_....sql`) avec le correctif.

## Exécuter

Depuis `reporting-commercial/backend/` (la connexion centrale est lue dans
`backend/.env` via `app.config`) :

```powershell
# Voir ce qui serait fait, sans rien exécuter (lecture seule)
python migrate.py --dry-run

# Appliquer les migrations pendantes
python migrate.py

# Installation existante où le SQL a déjà été passé à la main :
# enregistrer les migrations comme appliquées SANS les exécuter
python migrate.py --baseline
```

Sortie : une ligne par fichier avec statut `[APPLIED]` / `[SKIP]` / `[BASELINE]` /
`[PENDING]` (dry-run) / `[ERROR]`, puis un résumé. Exit code `0` si OK, `1` si erreur
(utilisable en CI / script d'installation).

La table de tracking `APP_Migrations (name, hash, applied_at)` est créée
automatiquement dans la base centrale au premier lancement (sauf en `--dry-run`,
qui ne modifie rien).

Variable optionnelle : `MIGRATION_QUERY_TIMEOUT` (secondes, défaut `0` = illimité) —
le timeout standard de 60 s est désactivé pendant les migrations car un
`CREATE INDEX` volumineux peut légitimement durer plus longtemps.

## Transactions : limite DDL de SQL Server

Chaque fichier est exécuté dans **une transaction** (autocommit désactivé) :
tous ses batchs `GO` + l'enregistrement dans `APP_Migrations`, puis un seul
`COMMIT`. Si un batch échoue → `ROLLBACK` du fichier entier.

**Limites à connaître :**

- La plupart des DDL SQL Server (CREATE/ALTER TABLE, CREATE INDEX, …) sont
  transactionnels et seront bien annulés par le rollback.
- Certaines instructions **ne peuvent pas s'exécuter dans une transaction
  utilisateur** et feront échouer la migration : `CREATE/ALTER/DROP DATABASE`,
  `BACKUP/RESTORE`, `ALTER FULLTEXT`, certains `ALTER DATABASE SET …`. Les
  exclure des migrations (les opérations base sont gérées par `setup.py`).
- Certaines erreurs graves provoquent un abandon automatique de la transaction
  par SQL Server lui-même ; le rollback du runner est alors sans objet mais
  inoffensif.
- Un fichier **partiellement non-transactionnel** peut donc laisser des effets
  résiduels après un échec. Parade : migrations **courtes, idempotentes**
  (gardes `IF NOT EXISTS`) — relancer `migrate.py` après correction doit
  toujours être sûr.

## Installations existantes (mise en route du runner)

Sur une base où `011_*` / `012_*` ont déjà été exécutées à la main :

```powershell
python migrate.py --dry-run    # vérifier la liste
python migrate.py --baseline   # marquer comme appliquées sans exécuter
python migrate.py              # les futures migrations s'appliqueront normalement
```
