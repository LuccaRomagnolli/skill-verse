---
name: skyciv-assistente
description: Analisa um modelo estrutural versionado na SkyCiv API v3, lê reações, esforços e deslocamentos, e guarda relatório e consumo de créditos. Use quando houver pedido de análise estrutural na nuvem ou consulta dos resultados SkyCiv de uma obra.
---

# Análise estrutural SkyCiv

Use o MCP `skyciv` com a conta e os créditos do cliente. Configure `SKYCIV_USERNAME` e `SKYCIV_API_KEY` somente no ambiente que inicia o Claude Code ou Codex. Não inclua credenciais em prompts, arquivos da obra ou configuração compartilhada. `skyciv_status` verifica apenas sua presença local; a conexão e o saldo dependem de chamada real.

## Antes da análise

1. Leia `projeto-contexto.json`, a revisão e o modelo da skill `modelo-estrutural`. Confira fontes públicas no índice `normas-publicas`; para NBR, use somente metadados e o exemplar licenciado do cliente. Resolva hipóteses de cargas, apoios, rigidez, liberações, malha, eixos, materiais e combinações com o responsável técnico. O desenho ou BIM não define esses dados automaticamente.
2. Execute `skyciv_validar_modelo` e confira o hash, número de nós, barras e placas. Faça também `python3 ../modelo-estrutural/scripts/modelo.py skyciv <modelo.json> --saida <previa.json>` para revisar o objeto S3D e os fatores. O exemplo incluído é didático, sem validação para obra.
3. Mostre ao usuário projeto, revisão, quantidade de peças, grupos/combinações e custo previsto. A [tabela SkyCiv](https://skyciv.com/api/v3/docs/api-calls/) informa um crédito para `S3D.model.solve` linear. **Peça confirmação explícita para cada envio**; depois use `skyciv_analisar` com `confirmar_envio=true`. A ferramenta não repete a solicitação automaticamente. Em erro de rede ou resposta incerta, consulte a atividade da conta antes de qualquer nova tentativa.

## Depois da análise

O MCP usa `validate_input`, confere o status de cada função e grava `modelo-s3d.json`, `resposta.json`, `resultados.json`, `manifesto.json` e, quando disponível, `relatorio.pdf` em `resultados/skyciv-*` ao lado do modelo. O manifesto registra SHA-256, IDs de peças/nós, créditos informados pela API e revisão técnica pendente. Consulte com `skyciv_resultados`; compare revisão e hash antes de transferir qualquer resultado para outra etapa.

Examine reações, equilíbrio global, deslocamentos, diagramas por combinação, sentidos e eixo local das barras. Compare esforços e reações com uma referência independente antes de dimensionar. As rotinas locais de concreto aceitam casos limitados de flexão/cisalhamento. Para uma viga retangular em flexão positiva uniaxial, transcreva da tabela/relatório os valores `Md`/`Vd`, estação, ID SkyCiv, eixos locais, torção/axial/momento secundário, fck, CAA e revisor para um JSON. `python3 scripts/triagem_viga.py modelo.json manifesto.json selecao.json --saida entrada-viga.json` confere revisão, ID, combinação ELU e limites e produz os argumentos para `viga.py`; não interpreta automaticamente o diagrama. Flexão negativa, biaxial, torção, axial, punção, segunda ordem, instabilidade, detalhamento e outros casos fora do domínio da rotina viram pendência. A [API de análise](https://skyciv.com/api/v3/docs/S3D.model/) não certifica dimensionamento NBR; os [verificadores RC da SkyCiv](https://skyciv.com/api/v3/docs/S3D.design/) não devem ser anunciados como NBR 6118.

Registre modelo, resultados, relatório, consumo de créditos, comparação independente e pendências em `projeto-contexto.json` com `contexto.py artefato`, `decisao` e `pendencia`. Libere a mesma revisão para `autocad-assistente` e **um** destino BIM escolhido pelo usuário: `revit-assistente` ou `archicad-assistente`. Uma mudança em entrada exige nova revisão e nova análise.

## Limites e responsabilidade

O pack está em versão candidata até que haja análise com conta real, comparação independente de caso de referência, conferência de premissas normativas e abertura/medição dos arquivos em AutoCAD e no BIM escolhido. Não apresente validação local ou sucesso da API como aprovação estrutural. O responsável técnico escolhe hipóteses, confere o modelo e assina as entregas.
