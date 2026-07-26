# -*- coding: utf-8 -*-
"""
Verifie l'implementation des INFORMATIONS LIBRES pour une base cliente donnee.
Controle 4 couches : config ETL, materialisation, datasources, exploitation.

Usage : python scripts/verify_info_libres.py <OptiBoard_CODE>
        python scripts/verify_info_libres.py OptiBoard_ALEAFOOD
"""
import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from app.database_unified import execute_central

DB = sys.argv[1] if len(sys.argv) > 1 else "OptiBoard_ALEAFOOD"
def ok(b): return "[OK]" if b else "[KO]"
def one(q, p=None):
    try: return execute_central(q, p, use_cache=False)[0]["n"]
    except Exception: return 0

print("=" * 68)
print(f"  VERIFICATION INFOS LIBRES — {DB}")
print("=" * 68)
all_ok = True

print("\n1) CONFIG ETL (master + published)")
for t in ["Info_Libres", "Info_Libres_Valeurs", "Info_Libres_Cle_Tiers"]:
    m = one("SELECT COUNT(*) n FROM OptiBoard_SaaS.dbo.APP_ETL_Tables_Config WHERE target_table=?", (t,))
    p = one(f"SELECT COUNT(*) n FROM [{DB}].dbo.APP_ETL_Tables_Published WHERE target_table=? AND is_enabled=1", (t,))
    all_ok &= bool(m and p); print(f"   {ok(m and p)} {t:<24} master={m} published={p}")

print("\n2) TABLES MATERIALISEES")
for t in ["Info_Libres", "Info_Libres_Valeurs", "Info_Libres_Cle_Tiers"]:
    ex = one(f"SELECT COUNT(*) n FROM [{DB}].sys.tables WHERE name='{t}'")
    c = one(f"SELECT COUNT(*) n FROM [{DB}].dbo.[{t}]") if ex else 0
    all_ok &= bool(c); print(f"   {ok(ex and c>0)} {t:<24} {c if ex else 'ABSENTE'} lignes")

print("\n3) DATASOURCES (central)")
ds = execute_central("SELECT code FROM APP_DataSources_Templates WHERE code LIKE 'DS_INFO_LIBRES%' AND actif=1 ORDER BY code", use_cache=False)
all_ok &= len(ds) == 6; print(f"   {ok(len(ds)==6)} {len(ds)}/6 : " + ", ".join(d["code"].replace("DS_INFO_LIBRES_", "") for d in ds))

print("\n4) EXPLOITATION (jointures reelles)")
qA = f"SELECT COUNT(*) n FROM [{DB}].dbo.Articles a JOIN [{DB}].dbo.Info_Libres_Valeurs v ON v.CB_File='F_ARTICLE' AND v.societe=a.societe AND v.entity_key=CAST(a.[Code interne] AS NVARCHAR(50))"
qC = f"SELECT COUNT(*) n FROM [{DB}].dbo.Clients cl JOIN [{DB}].dbo.Info_Libres_Cle_Tiers k ON k.societe=cl.societe AND k.[Code tiers]=cl.[Code client] JOIN [{DB}].dbo.Info_Libres_Valeurs v ON v.CB_File='F_COMPTET' AND v.societe=cl.societe AND v.entity_key=k.[Clé Sage]"
a = one(qA); c = one(qC)
print(f"   {ok(a>0)} Articles x infos libres : {a} lignes")
print(f"   {ok(c>0)} Clients  x infos libres (cle tiers) : {c} lignes")

print("\n" + "=" * 68)
print("  RESULTAT : " + ("TOUT OK — infos libres operationnelles" if all_ok else "INCOMPLET — voir les [KO] ci-dessus"))
print("=" * 68)
sys.exit(0 if all_ok else 1)
