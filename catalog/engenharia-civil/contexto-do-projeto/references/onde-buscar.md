# Onde buscar requisitos locais — por esfera

Troque `<município>`, `<UF>` e `<estado por extenso>` pelos dados da ficha. Faça **uma busca por item do checklist**, abra o resultado oficial e registre com `contexto.py fonte`.

## Ordem de confiança das fontes
1. **Oficial primário**: site da prefeitura (`*.<município>.<uf>.gov.br`, `prefeitura.*`), câmara municipal (`*.leg.br`, `camara*`), diário oficial, sistema oficial de legislação, Corpo de Bombeiros (`cbm*.gov.br`, `bombeiros.*.gov.br`, `corpodebombeiros.*`), concessionária (site da própria empresa), CREA/CONFEA (`crea-<uf>.org.br`, `confea.org.br`).
2. **Agregador de legislação** (ex.: Leis Municipais, LegisWeb): aceitável para achar o número e o texto, mas **confira a vigência e alterações na fonte oficial** e registre isso.
3. **Secundário** (blogs, cursinhos, fóruns): só para descobrir o nome/número do documento. Nunca como fonte do requisito.

**Nunca use** sites de cópias (Scribd, Passei Direto, Studocu, Docero, PDFCoffee, SlideShare, Academia.edu, DocPlayer…) e nunca baixe ou cite texto integral de NBR encontrado na internet: é cópia não autorizada de conteúdo vendido pela ABNT.

## Municipal
| Item | Consultas sugeridas | Observações |
|---|---|---|
| Código de Obras e Edificações | `código de obras <município> lei`, `código de edificações <município> <UF>` | ver se há decreto regulamentador e alterações; anotar número/ano |
| Plano Diretor / Uso e Ocupação do Solo | `plano diretor <município> lei`, `lei de uso e ocupação do solo <município>`, `zoneamento <município> mapa` | parâmetros urbanísticos dependem da **zona do lote**: peça endereço ou inscrição do lote ao usuário |
| Aprovação / alvará | `aprovação de projeto <município> documentos alvará de construção`, `licenciamento de obras <município>` | quase sempre há página de serviço da prefeitura com lista de documentos |
| Acessibilidade e calçadas | `lei calçadas <município>`, `padrão de calçada <município>` | NBR 9050 (gratuita) + lei municipal |
| Outros comuns | `lei de drenagem/permeabilidade <município>`, `reservatório de retenção lei <município>`, `lei de muros e cercas <município>` | conforme o caso |

Distrito Federal: o "município" é o DF; códigos e parâmetros são distritais (ex.: COE-DF, LUOS, PDOT).

## Estadual
| Item | Consultas sugeridas | Observações |
|---|---|---|
| Segurança contra incêndio | `corpo de bombeiros <UF> instruções técnicas`, `norma técnica <n> corpo de bombeiros <UF>`, `regulamento de segurança contra incêndio <estado>` | muitos estados seguem as ITs de SP com numeração própria; confirme se a edificação é isenta (ex.: residencial unifamiliar) **na norma do estado** |
| Vigilância sanitária | `vigilância sanitária <UF> projeto arquitetônico` | uso saúde/alimentação: RDC ANVISA 50/2002 (federal, pública) |
| Ambiental | `licenciamento ambiental <UF> órgão` | indústria, loteamento, grandes empreendimentos |

## Concessionárias
| Item | Consultas sugeridas | Observações |
|---|---|---|
| Energia | `<distribuidora> norma de fornecimento baixa tensão`, `padrão de entrada <distribuidora>` | descubra a distribuidora do município primeiro (`distribuidora de energia <município>`) |
| Água e esgoto | `<companhia> norma técnica ligação de água`, `<companhia> padrão de ligação esgoto` | companhia estadual ou serviço municipal (SAAE/DAE) |
| Gás | `<distribuidora de gás> regulamento instalações internas` | quando houver gás canalizado |

## Conselho profissional
| Item | Consultas sugeridas | Observações |
|---|---|---|
| ART | `CREA-<UF> ART obra ou serviço`, `CONFEA resolução 1.137/2023 ART` | o CREA **não** define requisitos de projeto: define registro da responsabilidade técnica e atribuições |
| Atribuições | `CONFEA resolução atribuições engenheiro civil` | quando houver dúvida se o profissional pode assinar a atividade |

## ABNT (só metadados)
- Consulta: `ABNT NBR <número> em vigor`, catálogo da ABNT (abntcatalogo.com.br / abnt.org.br): registre **número, ano da edição vigente, título e se há emenda/errata**.
- Para entender o conteúdo: guias e artigos públicos (ex.: guias da CBIC sobre a NBR 15575, publicações de universidades e entidades técnicas), citando-os como fonte secundária.
- O requisito numérico da NBR vem das sínteses das skills de cálculo (`references/`) ou da cópia licenciada do usuário.
- Normas ABNT de acessibilidade são gratuitas no catálogo da ABNT, mediante cadastro: oriente o usuário a baixar e, se quiser, importar no índice (`normas.py importar`).
