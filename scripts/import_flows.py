#!/usr/bin/env python3
"""Importe des flows YAML dans une instance Kestra via l'API REST."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

from kestra_api import KestraClient, load_flow_identity


DEFAULT_FLOW_ROOT = Path("kestra/flows")


def discover_yaml(paths: Iterable[str], include_all: bool = False) -> List[Path]:
    if include_all:
        roots = [DEFAULT_FLOW_ROOT]
    else:
        roots = [Path(p) for p in paths]

    discovered: List[Path] = []
    for root in roots:
        if root.is_file() and root.suffix in {".yml", ".yaml"}:
            discovered.append(root)
        elif root.is_dir():
            discovered.extend(sorted(root.rglob("*.yml")))
            discovered.extend(sorted(root.rglob("*.yaml")))
        else:
            raise FileNotFoundError(f"Chemin introuvable ou non YAML: {root}")

    return sorted(set(discovered))


def main() -> int:
    parser = argparse.ArgumentParser(description="Importe des flows YAML dans Kestra.")
    parser.add_argument("paths", nargs="*", help="Fichiers ou dossiers de flows à importer.")
    parser.add_argument("--all", action="store_true", help="Importer tous les flows sous kestra/flows.")
    args = parser.parse_args()

    if not args.all and not args.paths:
        parser.error("Fournir au moins un fichier/dossier ou utiliser --all.")

    paths = discover_yaml(args.paths, include_all=args.all)

    client = KestraClient()
    if not client.health():
        raise SystemExit("Kestra ne répond pas. Vérifier KESTRA_URL et que l'instance est démarrée.")

    for path in paths:
        namespace, flow_id = load_flow_identity(path)
        client.import_flow_file(path)
        print(f"OK import {namespace}/{flow_id} depuis {path}")

    print(f"{len(paths)} flow(s) importé(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
