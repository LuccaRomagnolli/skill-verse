# Vento — base ABNT NBR 6123:2023

O exemplar fornecido é a segunda edição de 20.12.2023. A [ABNT divulgou a Errata 1:2025](https://pt.linkedin.com/posts/abnt-associacao-brasileira-de-normas-tecnicas_abnt-normaliza%C3%A7%C3%A3o-capacita%C3%A7%C3%A3o-activity-7339396155383910401-thRx), ainda não presente nos arquivos conferidos. Antes de liberação, obter/confrontar a errata e confirmar vigência no [Catálogo ABNT](https://www.abntcatalogo.com.br/). Não declare conformidade à versão corrigida com base apenas neste guia.

| Parâmetro | Origem e decisão necessária |
|---|---|
| V0 (m/s) | Figura 1, isopletas; registrar posição da obra, interpolação/estudo específico e direção considerada (5.1) |
| S1 | Topografia da obra; plano ≠ morro/talude/vale protegido; 5.2 |
| S2 | Rugosidade por direção (5.3.1), classe pela superfície frontal/continuidade (5.3.2), altura z e limites da camada (5.3.3, Tabelas 1–3) |
| S3 | Grupo de segurança/vida útil da Tabela 4; residência usual é **grupo 3**, não grupo 2 |
| Ca | Coeficiente aerodinâmico da geometria e regime de turbulência; Figura 4/5 ou outra seção aplicável |
| fv | Fator de vizinhança conforme 6.4; não presumir 1 sem inspeção do entorno |

O script usa Vk = V0·S1·S2·S3 e q = 0,613·Vk² N/m² (4.2), com S2 = bm·Fr·(z/10)^p até zg (5.3.3, Tabelas 1–2). Valores da Tabela 4 conferidos na base 2023: grupos 1–5 correspondem a S3 de 1,11; 1,06; 1,00; 0,95; 0,83. Na Categoria V, S2 permanece constante até 10 m. Os fatores e a seleção de grupo devem ser reavaliados após acesso à errata.

Força de arrasto global simplificada: Fa = q·Ca·Ae·fv (4.3.3). O script calcula Ae como largura × faixa vertical até cada cota e toma q da cota superior — aproximação que precisa ser confrontada com o modelo de vento do projeto. Verifique pressão externa/interna, sucção local, cobertura, elementos de vedação, direções, excentricidade, vizinhança e dinâmica em ferramenta e memorial próprios; não são resultados do script.
