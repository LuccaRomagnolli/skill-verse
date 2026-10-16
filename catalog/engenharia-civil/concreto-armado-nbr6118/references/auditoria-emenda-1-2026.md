# Matriz de impacto — Emenda 1:2026 da NBR 6118

Matriz **original de rastreabilidade**, conferida em 2026-10-15 com a Emenda 1 fornecida pelo usuário e com a edição-base NBR 6118:2023. A emenda altera apenas parte da edição-base; ambas compõem a referência declarada **NBR 6118:2026**. Esta matriz não reproduz o texto normativo. Não incluir os PDFs fornecidos no repositório, índice público ou ZIP. Para os critérios herdados efetivamente usados pelos scripts, leia [auditoria-base-2023-para-2026.md](auditoria-base-2023-para-2026.md).

| Itens alterados | Efeito no pack | Estado / ação |
|---|---|---|
| Prefácio; Seção 2 | Transição por data de protocolo e revisão da lista de referências. | Registrar comprovante de protocolo e edição escolhida; não inferir a edição pela data do cálculo. |
| 5.1.2.3; 5.2.1 | Durabilidade e qualidade da solução passam a enfatizar premissas ambientais e sustentabilidade. | Exigir registro das premissas; nenhuma métrica de sustentabilidade é calculada. |
| 5.3 | ATP antes da construção; classe de consequência define profundidade da revisão, inclusive modelos independentes em CC3. | `contexto.py atp` e memorial registram situação e documento. Classificação, acordo de dispensa em CC1/CC2, habilitação e independência do avaliador exigem conferência humana. |
| 6.2.2; 6.2.4; 6.3.2.4 | Vida útil de referência e avaliação de mecanismos de durabilidade, incluindo etringita tardia. | Pedir vida útil e condições de exposição; projeto de dosagem, temperatura e proteção não são verificados. |
| 8.1; 8.2.11; 8.3.1, 8.3.7; 8.4.6 | Atualização de simbologia, remissões para fluência/retração e material de armaduras. | Valores de Eci, Ecs e aço foram confrontados com a base; propriedades específicas e execução continuam dependentes de certificados e análise do responsável. |
| 9.2.1; 9.5.2–9.5.3; 9.6.3.3.2.2; 9.6.3.4.2 | Aderência, emendas e perdas de protensão. | Ancoragem/emendas não são calculadas; protensão não é suportada. |
| 11.2.2; 11.3.3.2; Figura 11.1; 11.8.3.1 | Ações de água, fluência, imperfeições e combinações de serviço. | Confrontar ação e combinação por caso; `laje.py` calcula apenas estimativa de flecha, sem verificação final de ELS. |
| 12.3.3; 12.4.1 | Resistência em idade inferior a 28 dias e uso de coeficiente de material específico quando aplicável. | `fcd=fck/1,4` dos scripts só representa o caso normal a partir de 28 dias. Para idade precoce ou γc distinto, não usar a saída sem recálculo técnico. |
| 13.2.5.1; Tabelas 13.3–13.4 | Furos de laje, interpretação de deslocamento total e caso de laje protendida. | Furos, fases de deslocamento e protensão ficam pendentes; limite simples de flecha não conclui ELS. |
| 14.6.4.2–14.6.4.3; 14.7.8 | Redistribuição e estabilidade global; definição de laje-cogumelo/lisa. | Scripts não fazem redistribuição, análise global ou punção. Conferir limite de redistribuição e método aplicável no modelo externo. |
| Figura 15.3; 15.7.3; 15.8.1 | Análise global, rigidez de elementos pouco comprimidos e limite de esbeltez. | `pilar.py` restringe-se a λ ≤ 90, seção constante e hipóteses locais; não extrapolar para análise global. |
| 17.1; 17.2.4.1; 17.3.1, 17.3.2.1.1, 17.3.3.2, 17.3.5.2.4 | Centroide de armadura, flecha refinada de viga, fissuração e limite de armadura longitudinal. | Bloco retangular e limite fora da zona de emendas auditados; `laje.py` não implementa a rigidez refinada de viga nem ELS-W. |
| 17.4.1.1.3; 17.4.2.2; 17.5.1.4.1 | Detalhes de armadura de cortante e torção. | `viga.py` cobre somente estribos verticais do Modelo I para flexão simples; torção, barras dobradas e detalhes de apoio não são verificados. |
| 18.1; 18.2.4; 18.3.2.4–18.3.2.4.1; 18.3.3.2; 18.3.4; 18.3.6 | Detalhamento de grampos, ancoragem nos apoios, barras de amarração, torção e suspensão. | Sugestões de barras e estribos não equivalem a detalhamento executivo; conferência específica obrigatória. |
| 19.5.2.3; 19.5.4 | Punção em pilares de borda e armadura de integridade. | Fora do escopo de laje retangular apoiada em vigas; não utilizar para lajes lisas/cogumelo. |
| 20.1; Figura 20.1; 20.4; 20.5.1–20.5.2; 20.6 | Armadura secundária, aberturas, lajes nervuradas, telas e armadura inferior de segurança em balanço. | Armadura secundária simplificada é calculada; demais detalhes não. `laje.py` alerta explicitamente para o item 20.6. |
| 22.1; 22.5.1.2; Figuras 22.5 e 22.7 | Bielas/tirantes, consolos e regiões de descontinuidade. | Fora do escopo; exige modelo e detalhamento específicos. |
| 23.3 | Vibração de pisos. | Frequência modal não calculada; abrir pendência quando aplicável. |
| 24.6.1; 24.6.3 | Critérios relativos a fadiga. | Fora do escopo. |
| Anexo A (A.2.1, A.2.2.1, A.2.2.3, A.2.5) | Correções de variáveis e expressões de fluência/retração. | `laje.py` usa multiplicador simplificado, não o Anexo A; análise dependente do tempo deve ser feita à parte. |

**Regra de liberação:** esta matriz prova a identificação das alterações relevantes ao pack, não a conformidade integral da estrutura. Continuam necessários: revisão das hipóteses e do projeto completo por engenheiro habilitado, ATP conforme a classe, ensaios/certificados quando cabíveis e validação de casos reais nos softwares anunciados.
