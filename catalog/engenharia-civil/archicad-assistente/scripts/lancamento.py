#!/usr/bin/env python3
"""Modelo estrutural v1 -> plano de chamadas Archicad MCP 0.7.1/Tapir.

Não executa comandos no Archicad. O plano começa com dry-run, e a execução
exige confirmação e conferência no projeto aberto.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def _modelo():
    path = Path(__file__).resolve().parents[2] / "modelo-estrutural/scripts/modelo.py"
    spec = importlib.util.spec_from_file_location("skillverse_modelo_archicad", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gerar(d: dict, config: dict) -> dict:
    m = _modelo()
    m.validar(d)
    mat_cfg = config.get("materiais") or {}
    cotas = {n["id"]: n["cota_m"] for n in d["niveis"]}
    stories = config.get("pavimentos") or {}
    for n in d["niveis"]:
        item = stories.get(n["id"])
        if not isinstance(item, dict) or not isinstance(item.get("floorIndex"), int) or abs(item.get("cota_m", 1e20) - n["cota_m"]) > 1e-4:
            raise ValueError(f"pavimento {n['id']}: consulte GetStories e informe floorIndex e cota_m correspondentes")
    for material in d["materiais"]:
        item = mat_cfg.get(material["id"])
        material_id = item.get("buildingMaterialId") if isinstance(item, dict) else None
        guid = material_id.get("guid") if isinstance(material_id, dict) else None
        favorite = item.get("slabFavorite") if isinstance(item, dict) else None
        if (not isinstance(guid, str) or not guid.strip() or "SUBSTITUIR" in guid.upper() or
                not isinstance(favorite, str) or not favorite.strip() or "SUBSTITUIR" in favorite.upper()):
            raise ValueError(f"material {material['id']}: associe buildingMaterialId.guid e slabFavorite do template aberto")
    cols, beams, slabs = [], [], []
    ids = {"pilares": [], "vigas": [], "lajes": []}
    for p in d.get("pilares", []):
        cols.append({"coordinates": {"x": p["x_m"], "y": p["y_m"], "z": cotas[p["base"]]},
                     "height": cotas[p["topo"]] - cotas[p["base"]], "width": p["b_m"], "depth": p["h_m"],
                     "circleBased": False, "isWidthAndHeightLinked": False,
                     "buildingMaterialId": mat_cfg[p["material"]]["buildingMaterialId"],
                     "floorIndex": stories[p["base"]]["floorIndex"]})
        ids["pilares"].append(p["id"])
    for v in d.get("vigas", []):
        beams.append({"begCoordinate": {"x": v["de"][0], "y": v["de"][1]},
                      "endCoordinate": {"x": v["ate"][0], "y": v["ate"][1]},
                      "zCoordinate": cotas[v["nivel"]], "floorIndex": stories[v["nivel"]]["floorIndex"],
                      "width": v["b_m"], "height": v["h_m"], "isWidthAndHeightLinked": False,
                      "buildingMaterialId": mat_cfg[v["material"]]["buildingMaterialId"]})
        ids["vigas"].append(v["id"])
    for l in d.get("lajes", []):
        slabs.append({"favoriteName": mat_cfg[l["material"]]["slabFavorite"],
                      "level": cotas[l["nivel"]], "floorIndex": stories[l["nivel"]]["floorIndex"],
                      "thickness": l["espessura_m"], "referencePlaneLocation": "Top",
                      "polygonCoordinates": [{"x": x, "y": y} for x, y in l["contorno"]]})
        ids["lajes"].append(l["id"])
    ops = []
    if cols:
        ops.append({"tool": "create_elements", "args": {"element_type": "column", "items": cols, "dry_run": True},
                    "executar_apos_confirmacao": {"dry_run": False}, "ids_esperados": ids["pilares"]})
    if beams:
        ops.append({"tool": "describe_api_command", "args": {"name": "CreateBeams"}})
        ops.append({"tool": "execute_write_api_command", "args": {"name": "CreateBeams", "params": {"beamsData": beams}, "confirm": False},
                    "executar_apos_confirmacao": {"confirm": True}, "ids_esperados": ids["vigas"]})
    if slabs:
        ops.append({"tool": "create_elements", "args": {"element_type": "slab", "items": slabs, "dry_run": True},
                    "executar_apos_confirmacao": {"dry_run": False}, "ids_esperados": ids["lajes"]})
    return {"projeto": d["projeto"], "sha256_entrada": m.digest(d), "operacoes": ops,
            "aviso": "Salve cópia do PLN antes de ler propriedades ou gravar. Compare cada GUID retornado com ids_esperados e confirme geometria, material, pavimento e IFC no Archicad. Sem resultado real, nada está modelado."}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("modelo", type=Path)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--saida", type=Path, required=True)
    a = ap.parse_args()
    result = gerar(json.loads(a.modelo.read_text(encoding="utf-8")), json.loads(a.config.read_text(encoding="utf-8")))
    a.saida.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"operacoes": len(result["operacoes"]), "saida": str(a.saida)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
