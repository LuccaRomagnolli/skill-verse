# SolidWorks na engenharia civil: peças metálicas, ligações, fôrmas e equipamentos

## Onde o SolidWorks entra num escritório de estruturas/obras
- **Peças de ligação** de estruturas metálicas e mistas: chapas de base de pilar com chumbadores, chapas de ligação, cantoneiras de apoio, consoles, insertos metálicos em concreto (pré-moldado).
- **Estruturas leves**: mezaninos, passarelas, coberturas de pequeno porte, suportes de reservatório e de equipamentos, guarda-corpos.
- **Fôrmas e escoramentos especiais**: fôrma metálica de pilar circular, gabaritos, peças de içamento.
- **Montagem e compatibilização**: conferir interferência entre peças e com o concreto (STEP do Revit como referência).
- **Fabricação**: peso para orçamento, lista de peças, STEP/DXF para corte (plasma/laser) e dobra.

## Normas (citadas por número; o agente não reproduz texto)
| Tema | Norma |
|---|---|
| Projeto de estruturas de aço e mistas de edifícios | NBR 8800:2024, corrigida em 2025; confirme no Catálogo ABNT |
| Perfis formados a frio (dimensionamento) | NBR 14762 — confira a edição vigente no Catálogo ABNT |
| Perfis formados a frio (padronização de seções) | NBR 6355 — confira a edição vigente no Catálogo ABNT |
| Ações e segurança | NBR 8681, NBR 6120 e NBR 6123 — confira as edições vigentes; o script de vento usa a base de 2023, com confronto da Errata 1:2025 pendente. O perfil geral de combinações não substitui as verificações específicas do aço. |
| Soldagem / parafusos | especificações AWS/ASTM indicadas no projeto. Confirme com o projetista |

Edição vigente: confira com a skill `consulta-normas`. **O SolidWorks não dimensiona** a peça pela NBR 8800. O dimensionamento é do engenheiro (esta ferramenta não inclui script de verificação de aço). O modelo só materializa a geometria definida.

## Perfis
- Dimensões nominais (d, bf, tw, tf) vêm do **catálogo do fabricante** que o usuário usa (laminados W/HP) ou da NBR 6355 (formados a frio U, Ue, L, Z). Peça a designação (ex.: "W200 × 22,5" ou "Ue 150×60×20×2,65") e confirme as medidas com o catálogo do usuário. Não invente dimensões.
- `scripts/perfis.py` gera a seção (cantos vivos), a área, a massa por metro e o peso, além das chamadas do MCP. A massa nominal do catálogo prevalece (perfis laminados têm raios de concordância).
- Comprimento de barras: cota de eixo a eixo menos folgas de ligação, definidas pelo projetista.

## Chapa de base de pilar (exemplo completo)
```bash
python3 scripts/perfis.py chapa --b 300 --h 300 --t 16 --furos "-110,-110,22;110,-110,22;110,110,22;-110,110,22" \
    --nome "Chapa de base P1" --ops chapa-p1.json
```
Execute as ops em ordem. Troque `$ultima_extrusao` pelo nome devolvido por `create_extrusion`. Depois, opcionalmente: perfil do pilar como segundo corpo ou peça, enrijecedores (`sketch_profile` triangular + `create_extrusion` com `merge`), `fillet` de cantos da chapa. Por fim, `get_mass_properties` e `look_at_model`.
- Furos para chumbadores: diâmetro e distâncias de borda definidos pelo projetista (NBR 8800 traz os mínimos). Pergunte. Não presuma.

## Peso → orçamento
- Peso total (kg) de `get_mass_properties`/`get_assembly_mass_properties`, ou de `perfis.py` × quantidade.
- Orce com `quantitativos-sinapi` (composições de estrutura metálica em kg: fabricação + montagem; pintura em m², com a área de superfície devolvida por `get_mass_properties`).

## Saídas para outros softwares
- **STEP** (`save_document` com `.STEP`): para Revit (família genérica), compatibilização e fabricante.
- **DXF de chapas para corte** e **folha de desenho**: macro de `api-vba.md`.
