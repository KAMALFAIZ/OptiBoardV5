# OptiBoard — Sauvegarde & Restauration des bases SQL Server

## Vue d'ensemble

| Script | Rôle |
|---|---|
| `scripts/backup/backup_dbs.ps1` | Sauvegarde la base centrale (`OptiBoard_SaaS`) + toutes les bases clients (`OptiBoard_<CODE>`) avec vérification (`RESTORE VERIFYONLY`) et rétention glissante (30 jours par défaut). |
| `scripts/backup/restore_db.ps1` | Restaure une base depuis un `.bak` (même nom ou nouveau nom). |
| `scripts/backup/INSTALL_BACKUP_TASK.bat` | Crée la tâche planifiée Windows `OptiBoard-Backup` (quotidienne, 02:00, compte SYSTEM). |

Sur une installation client, ces trois fichiers sont déployés à la racine `C:\OptiBoard\`.

## Mise en place (une fois par installation)

```bat
REM Sur le serveur OptiBoard (en admin) :
C:\OptiBoard\INSTALL_BACKUP_TASK.bat
```

La tâche lit la connexion SQL dans `C:\OptiBoard\backend\.env` (`DB_SERVER`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`) et écrit les `.bak` dans `C:\OptiBoard\backups\`.

**Test immédiat** :
```powershell
schtasks /Run /TN "OptiBoard-Backup"
# puis vérifier :
Get-Content C:\OptiBoard\backups\backup_log.txt -Tail 20
```

## Points d'attention

- **SQL Server distant** : `BACKUP DATABASE` écrit sur le disque **du serveur SQL**, pas de la machine qui lance le script. Si SQL Server n'est pas local et que `-BackupDir` n'est pas fourni, le script découvre automatiquement le dossier de backup par défaut du serveur (`SERVERPROPERTY('InstanceDefaultBackupPath')`, repli registre) et y crée un sous-dossier `OptiBoard\` via `xp_create_subdir`. Pour un autre emplacement, passer `-BackupDir` avec un chemin valide **côté serveur** (ou un partage UNC accessible au compte de service SQL Server).
- **Rétention sur serveur distant** : si le dossier n'est pas accessible depuis la machine qui lance le script, la purge des vieux `.bak` est faite côté serveur via `xp_delete_file` (procédure des plans de maintenance).
- **Espace disque serveur** : surveiller l'espace libre du volume de backup — un disque plein fait échouer les sauvegardes **et** menace SQL Server lui-même (erreur constatée : `Operating system error 112`).
- **SQL Express** : la compression de backup n'est pas supportée — le script bascule automatiquement en backup non compressé.
- **Hors site** : le dossier `C:\OptiBoard\backups` doit lui-même être copié hors de la machine (NAS, cloud, disque externe). Un backup sur le même disque que la base ne protège pas d'une panne disque.
- **Code retour** : `backup_dbs.ps1` retourne `1` si au moins une base a échoué — exploitable pour un monitoring externe.

## Restauration

```powershell
# Restaurer en écrasant la base existante (confirmation demandée) :
.\restore_db.ps1 -BakFile "C:\OptiBoard\backups\OptiBoard_SG_20260611_020000.bak" -Database OptiBoard_SG

# Restaurer vers une base de test (sans toucher la production) :
.\restore_db.ps1 -BakFile "C:\OptiBoard\backups\OptiBoard_SG_20260611_020000.bak" -Database OptiBoard_SG_TEST

# Sans confirmation (scripts/urgence) :
.\restore_db.ps1 -BakFile "...bak" -Database OptiBoard_SG -Force
```

Le script :
1. Lit la liste des fichiers logiques du `.bak` (`RESTORE FILELISTONLY`) et construit les clauses `MOVE` vers les chemins par défaut de l'instance — la restauration sous un autre nom fonctionne donc sans préparation.
2. Passe la base cible en `SINGLE_USER WITH ROLLBACK IMMEDIATE` (déconnecte les utilisateurs).
3. Restaure avec `WITH REPLACE`.
4. Repasse la base en `MULTI_USER` (y compris en cas d'échec).

**Après restauration d'une base client**, vérifier que le routage est intact :
```sql
SELECT * FROM OptiBoard_SaaS.dbo.APP_ClientDB WHERE db_name = 'OptiBoard_<CODE>';
```

## Objectifs de service recommandés

| Paramètre | Valeur par défaut | Ajustable via |
|---|---|---|
| Fréquence | Quotidienne 02:00 | `INSTALL_BACKUP_TASK.bat` (schtasks) |
| Rétention | 30 jours | `backup_dbs.ps1 -RetentionDays N` |
| RPO (perte max) | 24 h | augmenter la fréquence de la tâche |
| RPO renforcé | — | passer les bases en mode FULL + backups de journaux (non couvert par ces scripts) |

## Vérification mensuelle conseillée

Une sauvegarde n'est fiable que si on l'a restaurée au moins une fois :

```powershell
.\restore_db.ps1 -BakFile "<dernier .bak>" -Database OptiBoard_VERIF -Force
# contrôler quelques tables, puis :
# DROP DATABASE OptiBoard_VERIF;
```
