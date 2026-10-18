# Validação do Archicad 30 no macOS

Data: 2026-10-18  
Estado: integração funcional com pendências de entrega; candidato

## Ambiente observado

- Archicad 30 INT `30.0.0 v1`, build 3001, licença Education.
- Projeto de teste salvo `SkillVerse-Archicad30-Test.pln`, não Teamwork, porta JSON API 19723.
- `archicad-mcp-server==0.8.0`, modo `full`, transporte stdio, 41 tools.
- Tapir 1.7.1, bundle universal macOS assinado por enzyme apd Limited e com ticket de notarização.
- Regras do pack: 13 carregadas, sem erro de leitura.

## Ensaio de modelagem

Após prévia sem escrita e confirmação, o MCP criou nove elementos:

| Elemento | Quantidade | Geometria conferida |
|---|---:|---|
| Pilar | 4 | 3,00 m; seção 0,20 × 0,30 m; coordenadas 0/4 × 0/5 m |
| Viga | 4 | perímetro 4,00 × 5,00 m; seção 0,20 × 0,40 m; cota 3,00 m |
| Laje | 1 | contorno 4,00 × 5,00 m; laje Basic de 0,15 m; cota 3,00 m |

Cada ID do modelo foi associado ao GUID retornado. `GetDetailsOfElements` confirmou tipo, pavimento, coordenadas, seções, material, contorno e espessura; `verificar_lancamento.py` aprovou 9 de 9 elementos sem divergência. O modelo foi inspecionado em planta e 3D e salvo como PLN.

### Desvio de laje encontrado e corrigido

O primeiro `CreateSlabs`, sem favorito Basic, criou uma laje Composite de 0,30 m embora o payload pedisse 0,15 m. `ModifySlabs` alterou o mesmo GUID para `structureType=Basic`, espessura 0,15 m e material configurado. Um ensaio adicional com o favorito `Slab - Basic Reinforced Concrete` criou espessura e estrutura corretas, porém herdou o material próprio do favorito.

O pack passou a exigir favorito Basic, declarar `slabStructureType`, reler cada elemento e comparar a propriedade efetiva. O plano também fornece uma receita de `ModifySlabs` para correção confirmada quando estrutura, espessura ou material divergirem.

## PLN, BCF e IFC

- PLN: salvo após a criação e relido pelo MCP com 4 Column, 4 Beam e 1 Slab, além dos objetos do template.
- BCF: uma issue foi criada, comentada, associada ao GUID da laje, exportada e reimportada.
- IFC: exportado pelo comando `IFCFileOperation`; o arquivo IFC2X3 contém 4 `IFCCOLUMN`, 4 `IFCBEAM`, 1 `IFCSLAB` e 2 `IFCBUILDINGSTOREY`.
- Reabertura IFC: as nove geometrias permaneceram visíveis e com a contagem esperada. Com o tradutor padrão desta instalação, as oito barras foram importadas como `Object` e a laje como `Slab`. A configuração de tradução e a preservação semântica continuam pendentes antes de usar esse round trip como entrega.

## Auditoria final

O modelo preenchido retornou `element_count=37` incluindo objetos do template e segmentos internos. Não houve regra ignorada. O interpretador conservador reprovou a prontidão por dez resultados falhos entre os dois conjuntos:

- classificação ausente nas 4 vigas, 4 pilares e 1 laje segundo a regra configurada;
- `LoadBearing` IFC ausente nas mesmas nove peças;
- 37 elementos em layers que não correspondem ao padrão de exemplo do pack.

O upstream retornou `pass=true` com scores 46 e 40 porque as regras são warnings. `validar_auditoria.py` bloqueou a entrega ao encontrar qualquer falha. As regras de layer e classificação precisam ser adaptadas ao template do escritório antes de uma aprovação real.

## Alcance comprovado e pendências

O ensaio comprova conexão, Tapir, leitura de pavimentos e atributos, prévia, escrita de pilares/vigas/laje, associação de GUIDs, leitura geométrica, correção de laje, salvamento PLN, issue BCF e exportação/reabertura IFC no ambiente descrito.

Permanecem pendentes:

1. configurar classificação, propriedades IFC e layers conforme o template de entrega do cliente;
2. escolher e validar um tradutor IFC que preserve a semântica das barras na reimportação;
3. repetir no Archicad 29 e no Windows, se essas plataformas fizerem parte da entrega;
4. executar o processo com licença apropriada ao uso comercial; o ensaio local usou Education;
5. revisão do modelo e dos critérios por projetista BIM e responsável técnico.

O fluxo de paredes, portas, janelas, ambientes, anotações e composição de plantas arquitetônicas permanece fora deste conversor estrutural.
