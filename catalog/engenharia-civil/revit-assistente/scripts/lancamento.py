#!/usr/bin/env python3
"""Lançamento estrutural → chamadas do MCP `revit`, em ordem e com unidades convertidas.

Entrada (JSON, metros para posições/cotas e centímetros para seções; ver assets/lancamento.exemplo.json):
  niveis   [{nome, cota_m}]
  eixos    {x: [{nome, pos_m}], y: [{nome, pos_m}]}    (x = eixos verticais em planta, posição em X)
  pilares  [{nome, x_m, y_m, b_cm, h_cm, base, topo}]  (base/topo = nomes de níveis)
  vigas    [{nome, de: [x,y], ate: [x,y], b_cm, h_cm, nivel}]
  lajes    [{nome, contorno: [[x,y], ...], h_cm, nivel}]

Saída (--saida arquivo.json):
  tipos_csharp  código C# para `send_code_to_revit` que garante os tipos de pilar/viga com a seção certa
                (duplica uma família retangular existente). Devolve {tipos: {"P 20x50": "<id>"}, avisos}.
  ops           lista de {tool, args}. Onde aparecer "$tipo:<nome>", troque pelo id devolvido por tipos_csharp.
  marcas_csharp (com --marcar ids.json) código C# que grava a Marca (P1, V1…) nos elementos criados.

Exemplo:
  python3 lancamento.py assets/lancamento.exemplo.json --saida lancamento-ops.json
  python3 lancamento.py --marcar ids.json --saida marcas.json      # ids.json = {"P1": 123456, "V1": 123789}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from revit_unidades import converter  # noqa: E402


def mm(valor: float, unidade: str) -> float:
    return round(converter(float(valor), unidade, "mm"), 3)


def nome_tipo(prefixo: str, b_cm: float, h_cm: float) -> str:
    return f"{prefixo} {b_cm:g}x{h_cm:g}"


def espacamento_uniforme(posicoes: list[float], tol: float = 1e-6) -> float | None:
    if len(posicoes) < 2:
        return None
    passos = [b - a for a, b in zip(posicoes, posicoes[1:])]
    return passos[0] if all(abs(p - passos[0]) < tol and p > 0 for p in passos) else None


def cs_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def tipos_csharp(tipos: list[dict]) -> str:
    """C# que roda DENTRO da transação do `send_code_to_revit` (variáveis `document` e `parameters`)."""
    chamadas = "\n".join(
        f"res[{cs_str(t['nome'])}] = Garantir(BuiltInCategory.{t['categoria']}, {cs_str(t['nome'])}, "
        f"{t['b_mm']}, {t['h_mm']});" for t in tipos)
    return f"""var res = new Dictionary<string, string>();
var avisos = new List<string>();
string[][] pares = {{ new[] {{"b", "h"}}, new[] {{"Largura", "Altura"}}, new[] {{"Largura", "Profundidade"}},
                      new[] {{"Width", "Depth"}}, new[] {{"B", "H"}} }};
string Garantir(BuiltInCategory cat, string nome, double bMm, double hMm)
{{
    var simbolos = new FilteredElementCollector(document).OfClass(typeof(FamilySymbol)).OfCategory(cat)
        .Cast<FamilySymbol>().ToList();
    var ja = simbolos.FirstOrDefault(s => s.Name == nome);
    if (ja != null) return ja.Id.ToString();
    foreach (var s in simbolos)
        foreach (var p in pares)
        {{
            var pb = s.LookupParameter(p[0]);
            var ph = s.LookupParameter(p[1]);
            if (pb == null || ph == null || pb.IsReadOnly || ph.IsReadOnly || pb.StorageType != StorageType.Double)
                continue;
            var novo = (FamilySymbol)s.Duplicate(nome);
            novo.LookupParameter(p[0]).Set(bMm / 304.8);   // unidade interna: pés
            novo.LookupParameter(p[1]).Set(hMm / 304.8);
            return novo.Id.ToString();
        }}
    avisos.Add("Nenhuma família retangular editável em " + cat + " para " + nome +
               ": carregue uma família de concreto retangular e rode de novo.");
    return null;
}}
{chamadas}
return new {{ tipos = res, avisos = avisos }};"""


def grids_csharp(eixos: dict, ext: dict) -> str:
    linhas = []
    for e in eixos.get("x", []):
        x = mm(e["pos_m"], "m")
        linhas.append(f"G({x}, {ext['ymin']}, {x}, {ext['ymax']}, {cs_str(str(e['nome']))});")
    for e in eixos.get("y", []):
        y = mm(e["pos_m"], "m")
        linhas.append(f"G({ext['xmin']}, {y}, {ext['xmax']}, {y}, {cs_str(str(e['nome']))});")
    corpo = "\n".join(linhas)
    return f"""var criados = new List<string>();
var existentes = new FilteredElementCollector(document).OfClass(typeof(Grid)).Cast<Grid>().Select(g => g.Name).ToList();
void G(double x1, double y1, double x2, double y2, string nome)
{{
    if (existentes.Contains(nome)) return;
    var g = Grid.Create(document, Line.CreateBound(new XYZ(x1 / 304.8, y1 / 304.8, 0), new XYZ(x2 / 304.8, y2 / 304.8, 0)));
    g.Name = nome;
    criados.Add(nome);
}}
{corpo}
return criados;"""


def marcas_csharp(ids: dict) -> str:
    linhas = "\n".join(f"M({cs_str(str(int(i)))}, {cs_str(str(marca))});" for marca, i in ids.items())
    # busca pelo texto do id: ElementId(long) só existe no Revit 2024+ e ElementId(int) sumiu nas versões novas
    return f"""var feitos = new List<string>();
var porId = new FilteredElementCollector(document).WhereElementIsNotElementType().ToElements()
    .ToDictionary(x => x.Id.ToString(), x => x);
void M(string id, string marca)
{{
    porId.TryGetValue(id, out var e);
    var p = e?.get_Parameter(BuiltInParameter.ALL_MODEL_MARK);
    if (p != null && !p.IsReadOnly) {{ p.Set(marca); feitos.Add(marca); }}
}}
{linhas}
return feitos;"""


def gerar(dados: dict, folga_eixo_m: float = 1.0) -> dict:
    niveis = {n["nome"]: mm(n["cota_m"], "m") for n in dados.get("niveis", [])}
    faltando = set()

    def cota(nome):
        if nome not in niveis:
            faltando.add(nome)
            return 0.0
        return niveis[nome]

    ops: list[dict] = []
    if niveis:
        ops.append({"tool": "create_level", "args": {"data": [
            {"name": n, "elevation": c, "createFloorPlan": True, "createCeilingPlan": False}
            for n, c in sorted(niveis.items(), key=lambda kv: kv[1])]},
            "nota": "antes, liste os níveis existentes (ai_element_filter filterCategory OST_Levels) e remova os que já existem"})

    # extensão dos eixos: envolve todas as posições conhecidas, com folga
    xs = [e["pos_m"] for e in dados.get("eixos", {}).get("x", [])] + [p["x_m"] for p in dados.get("pilares", [])]
    ys = [e["pos_m"] for e in dados.get("eixos", {}).get("y", [])] + [p["y_m"] for p in dados.get("pilares", [])]
    out = {"ops": ops, "tipos": [], "avisos": []}
    eixos = dados.get("eixos") or {}
    if eixos.get("x") or eixos.get("y"):
        ext = {"xmin": mm(min(xs) - folga_eixo_m, "m"), "xmax": mm(max(xs) + folga_eixo_m, "m"),
               "ymin": mm(min(ys) - folga_eixo_m, "m"), "ymax": mm(max(ys) + folga_eixo_m, "m")}
        px = [e["pos_m"] for e in eixos.get("x", [])]
        py = [e["pos_m"] for e in eixos.get("y", [])]
        sx, sy = espacamento_uniforme(px), espacamento_uniforme(py)
        if sx and sy:
            nx0, ny0 = str(eixos["x"][0]["nome"]), str(eixos["y"][0]["nome"])
            ops.append({"tool": "create_grid", "args": {
                "xCount": len(px), "xSpacing": mm(sx, "m"), "xStartPosition": mm(px[0], "m"),
                "xStartLabel": nx0, "xNamingStyle": "numeric" if nx0.isdigit() else "alphabetic",
                "yCount": len(py), "ySpacing": mm(sy, "m"), "yStartPosition": mm(py[0], "m"),
                "yStartLabel": ny0, "yNamingStyle": "numeric" if ny0.isdigit() else "alphabetic",
                "xExtentMin": ext["xmin"], "xExtentMax": ext["xmax"],
                "yExtentMin": ext["ymin"], "yExtentMax": ext["ymax"]}})
        else:
            ops.append({"tool": "send_code_to_revit", "args": {"code": grids_csharp(eixos, ext)},
                        "requer_confirmacao": True, "nota": "eixos com espaçamento irregular"})

    tipos: dict[str, dict] = {}
    pontos = []
    for p in dados.get("pilares", []):
        t = nome_tipo("P", p["b_cm"], p["h_cm"])
        tipos[t] = {"nome": t, "categoria": "OST_StructuralColumns", "b_mm": mm(p["b_cm"], "cm"), "h_mm": mm(p["h_cm"], "cm")}
        base, topo = cota(p["base"]), cota(p["topo"])
        if topo <= base and p["topo"] in niveis and p["base"] in niveis:
            out["avisos"].append(f"{p['nome']}: topo ({p['topo']}) não está acima da base ({p['base']})")
        pontos.append({"name": p["nome"], "typeId": f"$tipo:{t}",
                       "locationPoint": {"x": mm(p["x_m"], "m"), "y": mm(p["y_m"], "m"), "z": base},
                       "width": mm(p["b_cm"], "cm"), "depth": mm(p["h_cm"], "cm"), "height": round(topo - base, 3),
                       "baseLevel": base, "baseOffset": 0, "rotation": p.get("rot_graus", 0)})
    if pontos:
        ops.append({"tool": "create_point_based_element", "args": {"data": pontos}})

    linhas = []
    for v in dados.get("vigas", []):
        t = nome_tipo("V", v["b_cm"], v["h_cm"])
        tipos[t] = {"nome": t, "categoria": "OST_StructuralFraming", "b_mm": mm(v["b_cm"], "cm"), "h_mm": mm(v["h_cm"], "cm")}
        z = cota(v["nivel"])
        (x1, y1), (x2, y2) = v["de"], v["ate"]
        if (x1, y1) == (x2, y2):
            out["avisos"].append(f"{v['nome']}: início e fim coincidem")
            continue
        linhas.append({"category": "OST_StructuralFraming", "typeId": f"$tipo:{t}",
                       "locationLine": {"p0": {"x": mm(x1, "m"), "y": mm(y1, "m"), "z": z},
                                        "p1": {"x": mm(x2, "m"), "y": mm(y2, "m"), "z": z}},
                       "thickness": mm(v["b_cm"], "cm"), "height": mm(v["h_cm"], "cm"),
                       "baseLevel": z, "baseOffset": 0})
    if linhas:
        ops.append({"tool": "create_line_based_element", "args": {"data": linhas}})

    sup = []
    for laje in dados.get("lajes", []):
        pts = laje["contorno"]
        if len(pts) < 3:
            out["avisos"].append(f"{laje['nome']}: contorno com menos de 3 pontos")
            continue
        z = cota(laje["nivel"])
        segs = [{"p0": {"x": mm(a[0], "m"), "y": mm(a[1], "m"), "z": z},
                 "p1": {"x": mm(b[0], "m"), "y": mm(b[1], "m"), "z": z}}
                for a, b in zip(pts, pts[1:] + pts[:1])]
        # sem typeId: o add-in cria/usa um tipo de piso com a espessura pedida
        sup.append({"name": laje["nome"], "category": "OST_Floors", "boundary": {"outerLoop": segs},
                    "thickness": mm(laje["h_cm"], "cm"), "baseLevel": z, "baseOffset": 0})
    if sup:
        ops.append({"tool": "create_surface_based_element", "args": {"data": sup}})

    if faltando:
        out["avisos"].append("níveis não declarados: " + ", ".join(sorted(faltando)))
    out["tipos"] = list(tipos.values())
    if tipos:
        out["tipos_csharp"] = tipos_csharp(out["tipos"])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada", nargs="?", help="JSON do lançamento")
    ap.add_argument("--marcar", help='JSON {"P1": id, ...} com os ids devolvidos pelo MCP')
    ap.add_argument("--saida", help="grava o resultado neste arquivo (senão imprime)")
    a = ap.parse_args(argv)
    if a.marcar:
        res = {"marcas_csharp": marcas_csharp(json.loads(Path(a.marcar).read_text(encoding="utf-8")))}
    elif a.entrada:
        res = gerar(json.loads(Path(a.entrada).read_text(encoding="utf-8")))
    else:
        ap.error("informe o JSON do lançamento ou --marcar")
    txt = json.dumps(res, indent=1, ensure_ascii=False)
    if a.saida:
        Path(a.saida).write_text(txt, encoding="utf-8")
        resumo = {k: (len(v) if isinstance(v, list) else "ok") for k, v in res.items()}
        print(json.dumps({"saida": a.saida, **resumo, "avisos": res.get("avisos", [])}, ensure_ascii=False))
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
