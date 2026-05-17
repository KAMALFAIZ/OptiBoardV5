# -*- coding: utf-8 -*-
"""
Remplit les champs doc_description, doc_fields, doc_formula, doc_advantage
pour tous les widgets de tous les dashboards qui n'ont pas encore de documentation.
Ne modifie pas les widgets qui ont deja une doc_description renseignee.
"""
import sys, os, json, warnings, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
from app.database_unified import execute_central

DRY_RUN = '--dry-run' in sys.argv

# ── Defaults par type de widget ──────────────────────────────────────────────
WIDGET_DOC_DEFAULTS = {
    'kpi': {
        'doc_description': "Indicateur clé de performance. Affiche une valeur agrégée unique (total, moyenne, comptage) issue de la source de données.",
        'doc_fields': "Champ valeur (ex: CA HT, Quantité, Nb commandes)",
        'doc_formula': "SUM(valeur) / AVG(valeur) / COUNT(*) selon l'agrégation choisie",
        'doc_advantage': "Vue synthétique immédiate d'un KPI métier, avec icône et couleur d'alerte configurable.",
    },
    'kpi_compare': {
        'doc_description': "KPI avec comparaison N vs N-1. Affiche la valeur courante et l'évolution en % par rapport à la période précédente.",
        'doc_fields': "Champ valeur N (ex: CA HT), Champ valeur N-1 (ex: CA HT N-1)",
        'doc_formula': "Évolution % = (Valeur N − Valeur N-1) / Valeur N-1 × 100",
        'doc_advantage': "Permet de mesurer la progression instantanément avec flèche et couleur (vert/rouge).",
    },
    'gauge': {
        'doc_description': "Jauge circulaire indiquant la progression vers un objectif. Affiche le % atteint entre un minimum et un maximum.",
        'doc_fields': "Champ valeur (valeur actuelle), Objectif (cible max)",
        'doc_formula': "Taux d'atteinte = Valeur / Objectif × 100",
        'doc_advantage': "Visualisation intuitive du degré de réalisation d'un objectif (quota, budget, stock).",
    },
    'progress': {
        'doc_description': "Barre de progression linéaire. Indique la proportion atteinte par rapport à une cible.",
        'doc_fields': "Champ valeur (réalisé), Objectif (cible)",
        'doc_formula': "Progression % = Valeur / Objectif × 100",
        'doc_advantage': "Lecture rapide de l'avancement d'un indicateur en format compact (faible hauteur).",
    },
    'sparkline': {
        'doc_description': "Mini-graphique d'évolution temporelle intégré dans une carte KPI. Idéal pour montrer la tendance sans détail de valeurs.",
        'doc_fields': "Champ période (axe X), Champ valeur (axe Y)",
        'doc_formula': "SUM(valeur) GROUP BY période — courbe ou barres condensées",
        'doc_advantage': "Donne le contexte de tendance en peu d'espace, associé à une valeur KPI principale.",
    },
    'chart_bar': {
        'doc_description': "Graphique en barres verticales. Compare des valeurs entre différentes catégories ou périodes.",
        'doc_fields': "Axe X : champ catégorie (ex: Client, Mois, Famille)\nAxe Y : champ valeur numérique (ex: CA HT)",
        'doc_formula': "SUM(Valeur Y) GROUP BY Catégorie X",
        'doc_advantage': "Comparaison claire entre catégories. Supporte plusieurs séries (multi-barres groupées).",
    },
    'chart_stacked_bar': {
        'doc_description': "Barres empilées ou groupées. Décompose chaque barre en sous-catégories pour visualiser la part de chacune.",
        'doc_fields': "Axe X : catégorie principale\nAxe Y : valeur numérique\nSérie : champ de décomposition (ex: Famille, Commercial)",
        'doc_formula': "SUM(Valeur) GROUP BY Catégorie X, Série — empilement ou regroupement",
        'doc_advantage': "Montre simultanément le total et la composition interne de chaque barre.",
    },
    'chart_line': {
        'doc_description': "Graphique en lignes. Visualise l'évolution d'une ou plusieurs métriques dans le temps.",
        'doc_fields': "Axe X : champ période (ex: Mois, Date)\nAxe Y : champ valeur (ex: CA, Marge)",
        'doc_formula': "SUM(Valeur) GROUP BY Période — une ligne par série",
        'doc_advantage': "Met en évidence les tendances, pics et creux sur une dimension temporelle.",
    },
    'chart_combo': {
        'doc_description': "Graphique combiné barres + ligne(s). Superpose deux métriques de natures différentes sur un même graphique.",
        'doc_fields': "Axe X : période\nAxe Y (barres) : valeur principale (ex: CA HT)\nAxe Y2 (ligne) : valeur secondaire (ex: Marge %)",
        'doc_formula': "Barres : SUM(Y1) GROUP BY X\nLigne : SUM(Y2) ou AVG(Y2) GROUP BY X",
        'doc_advantage': "Corrèle deux indicateurs sur un seul graphique (volume vs ratio, CA vs marge).",
    },
    'chart_pie': {
        'doc_description': "Graphique circulaire (camembert). Représente la répartition en % d'un total entre plusieurs catégories.",
        'doc_fields': "Champ catégorie (ex: Famille article, Région)\nChamp valeur (ex: CA HT)",
        'doc_formula': "Part % = SUM(Valeur catégorie) / SUM(Valeur total) × 100",
        'doc_advantage': "Visualisation immédiate des parts de marché et de la composition d'un total.",
    },
    'chart_area': {
        'doc_description': "Graphique en aire. Visualise le volume cumulé sous une courbe d'évolution temporelle.",
        'doc_fields': "Axe X : période\nAxe Y : valeur numérique",
        'doc_formula': "SUM(Valeur) GROUP BY Période — aire sous la courbe",
        'doc_advantage': "Accentue visuellement l'amplitude des variations et met en valeur la croissance.",
    },
    'chart_funnel': {
        'doc_description': "Entonnoir de conversion. Visualise les étapes successives d'un processus avec le volume à chaque étape.",
        'doc_fields': "Champ étape (ex: Prospect, Devis, Commande, Livré)\nChamp valeur (ex: Nb documents, CA)",
        'doc_formula': "SUM ou COUNT par étape, trié par ordre de conversion décroissant",
        'doc_advantage': "Identifie les points de déperdition dans un cycle de vente ou de production.",
    },
    'chart_treemap': {
        'doc_description': "Arborescence proportionnelle (treemap). Représente les poids relatifs de chaque catégorie par surface.",
        'doc_fields': "Champ catégorie (ex: Famille, Client)\nChamp valeur (ex: CA HT)",
        'doc_formula': "Surface ∝ SUM(Valeur) — plus la valeur est grande, plus le rectangle est grand",
        'doc_advantage': "Permet de voir d'un coup d'œil les catégories dominantes dans un portefeuille.",
    },
    'table': {
        'doc_description': "Tableau de données détaillé. Affiche les lignes brutes ou agrégées de la source de données avec tri et défilement.",
        'doc_fields': "Toutes les colonnes retournées par la requête source",
        'doc_formula': "SELECT colonnes FROM source [WHERE ...] [ORDER BY champ]",
        'doc_advantage': "Permet de consulter le détail ligne par ligne, avec export possible et drill-down.",
    },
    'text': {
        'doc_description': "Zone de texte libre. Sert à afficher des titres de section, commentaires, instructions ou notes.",
        'doc_fields': "Aucun champ de données — contenu statique saisi manuellement",
        'doc_formula': "Texte statique — aucun calcul",
        'doc_advantage': "Structure visuellement le dashboard et guide l'utilisateur dans la lecture.",
    },
    'image': {
        'doc_description': "Affiche une image ou un logo depuis une URL externe ou interne.",
        'doc_fields': "URL de l'image (champ image_url)",
        'doc_formula': "URL statique — aucun calcul",
        'doc_advantage': "Personnalise le dashboard avec la charte graphique de l'entreprise (logo, bannière).",
    },
}


def fill_doc(widget: dict) -> tuple[dict, bool]:
    """Injecte les valeurs par défaut dans le config du widget. Retourne (widget_modifié, changed)."""
    defaults = WIDGET_DOC_DEFAULTS.get(widget.get('type'))
    if not defaults:
        return widget, False

    cfg = widget.get('config') or {}
    # Ne remplace que les champs vides/absents
    changed = False
    for key, val in defaults.items():
        if not cfg.get(key):
            cfg[key] = val
            changed = True

    if changed:
        widget = {**widget, 'config': cfg}
    return widget, changed


def main():
    print(f"{'[DRY-RUN] ' if DRY_RUN else ''}Chargement de tous les dashboards...")
    rows = execute_central("SELECT id, nom, widgets FROM APP_Dashboards WHERE actif = 1 ORDER BY id")
    if not rows:
        print("Aucun dashboard trouvé.")
        return

    total_dashboards = len(rows)
    updated_dashboards = 0
    total_widgets_updated = 0

    for row in rows:
        dash_id = row['id']
        dash_nom = row['nom'] or f'Dashboard #{dash_id}'
        raw = row.get('widgets') or '[]'

        try:
            widgets = json.loads(raw) if isinstance(raw, str) else raw
        except Exception as e:
            print(f"  ⚠ Dashboard {dash_id} '{dash_nom}' — JSON invalide: {e}")
            continue

        if not isinstance(widgets, list):
            continue

        new_widgets = []
        dash_changed = False
        widgets_changed = 0

        for w in widgets:
            new_w, changed = fill_doc(w)
            new_widgets.append(new_w)
            if changed:
                dash_changed = True
                widgets_changed += 1

        if dash_changed:
            updated_dashboards += 1
            total_widgets_updated += widgets_changed
            print(f"  [OK] Dashboard {dash_id} '{dash_nom}' -- {widgets_changed} widget(s) mis a jour")

            if not DRY_RUN:
                new_json = json.dumps(new_widgets, ensure_ascii=False)
                execute_central(
                    "UPDATE APP_Dashboards SET widgets = ?, date_modification = GETDATE() WHERE id = ?",
                    (new_json, dash_id)
                )
        else:
            print(f"  - Dashboard {dash_id} '{dash_nom}' -- deja documente, ignore")

    print(f"\n{'[DRY-RUN] ' if DRY_RUN else ''}Terminé.")
    print(f"  Dashboards traités  : {total_dashboards}")
    print(f"  Dashboards modifiés : {updated_dashboards}")
    print(f"  Widgets mis à jour  : {total_widgets_updated}")


if __name__ == '__main__':
    main()
