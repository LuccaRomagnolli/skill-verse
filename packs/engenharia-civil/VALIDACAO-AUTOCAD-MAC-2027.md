# Validação AutoCAD para Mac 2027 — 2026-10-17

## Ambiente e método

- Aplicativo: AutoCAD para Mac 2027, licença Education (uso não comercial), versão 26.0.60.171.
- Entrada: `modelo.exemplo.json`, revisão A, convertido por `autocad-assistente/scripts/plantas.py` em DXF de planta e prancha.
- Teste no aplicativo: abertura do DXF; script `.scr` de inicialização com AutoLISP para consultar entidades, unidades e comprimentos; `SAVEAS` para DWG; reabertura do DWG e repetição das consultas; `-PLOT` para PDF.
- Plotagem: `AutoCAD PDF (General Documentation).pc3`, `ISO full bleed A3 (420.00 x 297.00 MM)`, milímetros, paisagem, `Extents`, escala `1=0.05` (1:50 para desenho em metros), centralizada, `monochrome.ctb`.

## Resultado

| Verificação | DXF aberto | DWG reaberto |
|---|---:|---:|
| `INSUNITS` | 6 (m) | 6 (m) |
| Pilares (`EST-PILAR`) | 4 | 4 |
| Linhas de viga (`EST-VIGA`) | 8 | 8 |
| Linhas de laje (`EST-LAJE`) | 4 | 4 |
| Linhas de cota (`EST-COTA`) | 6 | 6 |
| Comprimentos geométricos das cotas principais | 4,000 e 5,000 m | 4,000 e 5,000 m |

O DWG foi salvo pelo AutoCAD no formato 2018/2019/2020. O PDF tem uma página A3 (1191 × 842 pt), manteve a moldura e o carimbo e foi inspecionado visualmente; o texto TrueType preservou `CONTEÚDO` e `RESPONSÁVEL TÉCNICO` e permite extração de texto. As cotas produzidas pelo gerador continuam estáticas e exigem revisão ou recriação associativa no projeto real.

## Evidência local

- `dist/validacao-autocad-2027/final/planta-Pav-1.dxf` — SHA-256 `b9a0cf966aeb2a0bb2034e71f146a7202be69f63566a08a56c1a067ade0c8367`.
- `dist/validacao-autocad-2027/final/planta-Pav-1-autocad-2027.dwg` — SHA-256 `dbba6af0baa205459aa37ec42ab2daf5ff86cdd90fd3e5c7cc48d2c56c03b788`.
- `dist/validacao-autocad-2027/final/prancha-Pav-1-autocad-2027.pdf` — SHA-256 `9cbee96f4bbb021621f1be0fb9b5ea247593aef8552e09e20831a12ca3b0a3a3`.
- `dist/validacao-autocad-2027/final/medidas-autocad-2027.txt`, `medidas-dwg-reaberto.txt` e `prancha-Pav-1-preview.png` registram as consultas e a inspeção visual.

O MCP AutoCAD fixado no pack usa `ezdxf` no macOS, mesmo com o aplicativo instalado. O teste comprova abertura, medição e saída DWG/PDF no AutoCAD real via `.scr`/AutoLISP; o controle do aplicativo por esse MCP ainda não foi validado. A licença Education não comprova uso comercial.
