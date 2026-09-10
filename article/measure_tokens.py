"""
Mesure le poids en tokens d'un modèle sémantique dbt.

Ce que l'outil mesure exactement : le nombre de tokens du texte que TU ajoutes
au modèle (descriptions, labels, noms). C'est une mesure exacte de cette part.

Ce qu'il ne mesure pas : le contexte complet reçu par l'agent (prompt système,
mise en forme, éventuelle troncature). Ces éléments ne sont pas exposés.
Formuler les résultats en conséquence : "enrichir cette description ajoute N
tokens au modèle", jamais "cela représente X % du contexte de l'agent".

Usage :
    python3 measure_tokens.py modele.yml
    python3 measure_tokens.py point_zero.yml enrichi.yml --scale 200
"""

import argparse
import sys
from pathlib import Path

import yaml

# --------------------------------------------------------------- tokenizer

def get_counter():
    """Retourne (fonction_de_comptage, nom_de_la_methode)."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return (lambda s: len(enc.encode(s)), "tiktoken/cl100k_base")
    except Exception:
        # Repli si tiktoken est indisponible ou hors ligne.
        # Approximation usuelle sur du texte français : ~3,6 caractères/token.
        return (lambda s: max(1, round(len(s) / 3.6)), "approximation (3,6 car./token)")


count, method = get_counter()


def tokens_of(obj) -> int:
    """Tokens du bloc YAML sérialisé, tel qu'il serait transmis."""
    return count(yaml.dump(obj, allow_unicode=True, sort_keys=False))


def text_tokens(obj) -> int:
    """Tokens des seuls champs rédigés : description, label."""
    total = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("description", "label") and isinstance(v, str):
                total += count(v)
            else:
                total += text_tokens(v)
    elif isinstance(obj, list):
        for item in obj:
            total += text_tokens(item)
    return total


# --------------------------------------------------------------- analyse

def analyse(path: Path) -> dict:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    resultat = {"fichier": path.name, "metriques": {}, "modeles": {}}

    for m in doc.get("metrics", []) or []:
        resultat["metriques"][m["name"]] = {
            "total": tokens_of(m),
            "redige": text_tokens(m),
        }

    for sm in doc.get("semantic_models", []) or []:
        resultat["modeles"][sm["name"]] = {
            "total": tokens_of(sm),
            "redige": text_tokens(sm),
        }

    resultat["total"] = (
        sum(v["total"] for v in resultat["metriques"].values())
        + sum(v["total"] for v in resultat["modeles"].values())
    )
    resultat["redige"] = (
        sum(v["redige"] for v in resultat["metriques"].values())
        + sum(v["redige"] for v in resultat["modeles"].values())
    )
    return resultat


def afficher(r: dict) -> None:
    print(f"\n=== {r['fichier']} ===")
    if r["metriques"]:
        print("\nMétriques           total   dont rédigé")
        for nom, v in r["metriques"].items():
            print(f"  {nom:<18} {v['total']:>5}   {v['redige']:>5}")
    if r["modeles"]:
        print("\nModèles sémantiques total   dont rédigé")
        for nom, v in r["modeles"].items():
            print(f"  {nom:<18} {v['total']:>5}   {v['redige']:>5}")
    print(f"\n  TOTAL              {r['total']:>5}   {r['redige']:>5}")


def comparer(avant: dict, apres: dict, echelle: int | None) -> None:
    print("\n=== Écart ===")
    delta = apres["total"] - avant["total"]
    pct = (delta / avant["total"] * 100) if avant["total"] else 0
    print(f"  Point zéro : {avant['total']} tokens")
    print(f"  Enrichi    : {apres['total']} tokens")
    print(f"  Écart      : {delta:+d} tokens ({pct:+.0f} %)")

    noms = set(avant["metriques"]) | set(apres["metriques"])
    lignes = []
    for n in sorted(noms):
        a = avant["metriques"].get(n, {}).get("total", 0)
        b = apres["metriques"].get(n, {}).get("total", 0)
        if a != b:
            lignes.append((n, a, b, b - a))
    if lignes:
        print("\n  Par métrique :")
        for n, a, b, d in lignes:
            print(f"    {n:<18} {a:>4} -> {b:>4}  ({d:+d})")

    if echelle:
        n_mesure = len(apres["metriques"]) or 1
        par_metrique = delta / n_mesure
        print(f"\n  Extrapolation à {echelle} métriques :")
        print(f"    {par_metrique:+.0f} tokens/métrique -> {par_metrique * echelle:+.0f} tokens")
        print("    (valable uniquement si l'agent reçoit toutes les métriques ;")
        print("     à vérifier au jour 2)")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("fichiers", nargs="+", help="1 fichier = analyse, 2 = comparaison")
    p.add_argument("--scale", type=int, default=None,
                   help="extrapoler l'écart à N métriques")
    args = p.parse_args()

    print(f"Méthode de comptage : {method}")

    resultats = [analyse(Path(f)) for f in args.fichiers[:2]]
    for r in resultats:
        afficher(r)
    if len(resultats) == 2:
        comparer(resultats[0], resultats[1], args.scale)
    return 0


if __name__ == "__main__":
    sys.exit(main())
