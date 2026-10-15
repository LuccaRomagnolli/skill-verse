---
name: tqs-assistente
description: Torna o agente proficiente no TQS (software brasileiro de cálculo de estruturas de concreto). Orienta o fluxo completo (dados do edifício, Modelador, processamento global, análise, detalhamento, plotagem) e automatiza pela API Python oficial do TQS. Lê e confere os dados do edifício (pisos, cotas, CAA, fck, cobrimentos, cargas) contra a NBR 6118, cria variantes do edifício (fck, Modelo IV/VI) numa cópia, roda o processamento global em fila, lista pilares, vigas e lajes do modelo, converte o modelo para o Revit, lê e exporta desenhos DWG em DXF/PDF e converte tf↔kN. Use quando o usuário mencionar TQS, Modelador Estrutural, Gerenciador TQS, processamento global, pórtico espacial, grelha, γz, edifício TQS, TQSPy ou disser "confere os dados do edifício no TQS", "processa o edifício", "testa com fck 30", "lista os pilares do TQS", "manda o TQS para o Revit" ou "exporta a planta de formas em DXF".
---

# Assistente TQS

O TQS não tem MCP. A automação é feita por **scripts Python que usam a API oficial do TQS** (pacote `TQS`, wheel TQSPythonInterface, que vem com o TQS V23 ou mais novo). Ela só roda **no Windows, com o TQS instalado**. Fora disso, a skill orienta o uso da interface e confere arquivos JSON exportados.

## 1. Sempre primeiro: diagnóstico
```bash
python scripts/tqs_ambiente.py
```
Informa sistema, Python (32/64 bits), pasta TQSW, wheel, quais módulos `TQS.*` importam, raiz dos edifícios e o que fazer se algo faltar. **Instalar o wheel exige permissão do usuário.** Use o Python que funcionou (ex.: `py -3-32`) em todos os comandos seguintes.

Como os nomes da API mudam entre versões do TQS e esta skill não foi testada em todas, antes de escrever código novo (ou se um script der `AttributeError`) rode:
```bash
python scripts/tqs_ambiente.py --introspectar TQSModel --saida api-tqsmodel.json
```
e use os nomes reais da versão instalada. A síntese da API (módulos, objetos, unidades, padrões) está em `references/tqspy-api.md`.

## 2. Dados do edifício (TQSBuild)
```bash
python scripts/tqs_edificio.py ler --edificio "<nome>" --saida ed.json
python scripts/tqs_edificio.py conferir --edificio "<nome>"            # ou --json ed.json (fora do Windows)
```
- `ler`: plantas (nome, classe, altura, repetições e **cota calculada**), materiais (CAA, fck), cobrimentos, modelo estrutural (IV/VI, γz/P-Delta), coeficientes dos carregamentos.
- `conferir`: fck mínimo por CAA (NBR 6118:2023, Tab. 7.1) e cobrimentos mínimos (Tab. 7.2, com Δc = 5 mm se houver controle de qualidade), comparando com a ficha do projeto (`projeto-contexto.json`, skill `contexto-do-projeto`). Mostre a tabela de OK/ALERTA ao usuário.
- **Alterar**: só numa cópia, com "sim" do usuário:
  ```bash
  python scripts/tqs_edificio.py aplicar --edificio "<nome>" --dados alt.json --salvar-como "<nome>-C30"
  ```
  `alt.json` = `{"materials": {"beamConcreteStrength": "C30", "columnConcreteStrength": "C30"}}`. `--sobrescrever` (original) só se o usuário pedir explicitamente.

## 3. Processamento global (TQSExec)
```bash
python scripts/tqs_processar.py --edificios "<nome>" --preset completo --tabela-ferros            # mostra o plano
python scripts/tqs_processar.py --edificios "<nome>" --preset completo --tabela-ferros --executar  # após o "sim"
```
Presets `esforcos` (só análise) e `completo` (análise + dimensionamento, detalhamento e desenhos). Ajuste com `--param beams=2`. Vários edifícios em fila: `--edificios "A,B,C"`. Peça para **fechar o edifício no TQS** antes de executar. Depois, oriente a ler os avisos/erros do processamento no Gerenciador. O agente não aprova resultado.

**Estudo de alternativas** (variantes de fck, Modelo IV × VI): roteiro em `references/fluxo-tqs.md`.

## 4. Modelo estrutural (TQSModel)
```bash
python scripts/tqs_modelo.py listar --edificio "<nome>" --saida modelo.json
```
Por planta: pilares (número, seção, ângulo, inserção), vigas (nós e trechos com b × h) e lajes (espessura). Só leitura. Útil para conferir o lançamento, montar quadros e alimentar orçamento ou Revit.

**Para o Revit**: `tqs_modelo.py para-revit --modelo modelo.json --edificio-json ed.json --saida lancamento.json` → skill `revit-assistente` (`lancamento.py`). Leia os `avisos`. Para o modelo completo (lajes, fundações), o caminho recomendado é o **IFC exportado pelo TQS**. Ver `references/interoperabilidade.md`.

## 5. Desenhos (TQSDwg)
```bash
python scripts/tqs_dwg.py ler FORMAS.DWG --saida resumo.json        # contagens por tipo/nível, extensão, textos
python scripts/tqs_dwg.py exportar FORMAS.DWG FORMAS.DXF             # ou .PDF (plotagem do TQS)
python scripts/tqs_dwg.py desenhar ops.json NOVO.DWG --escala 50     # desenho novo a partir de operações simples
```
Desenhos gerados pelo TQS (formas, armações) se alteram **no TQS**. O script não edita esses arquivos. Para prancha/carimbo em CAD: DXF → skill `autocad-assistente`.

## 6. Unidades
O TQS trabalha em **tf, tf/m, tf/m², tf·m**; cotas em m; Modelador e desenhos em cm. Converta sempre por script:
```bash
python scripts/tqs_unidades.py 12.5 tf kN
```

## 7. Orientação de uso da interface
Fluxo completo do projeto no TQS (o que cada etapa faz, o que conferir, onde a automação ajuda): `references/fluxo-tqs.md`. Erros comuns de ambiente e de API: `references/erros-comuns.md`. Preparação da arquitetura para o Modelador: skill `autocad-assistente` ("base para cálculo").

## Limites e responsabilidade
- O TQS calcula, e o **engenheiro analisa e assina** (responsável técnico). O agente confere dados de entrada, organiza, automatiza tarefas repetitivas e explica, mas não valida estabilidade global, dimensionamento nem detalhamento.
- Alterações no edifício são feitas numa **cópia** por padrão. Sobrescrever o original e executar o processamento exigem "sim" explícito.
- A conferência normativa cobre só itens objetivos (fck mínimo e cobrimentos por CAA, NBR 6118:2023, Tab. 7.1 e 7.2). Normas citadas por número. Nenhum texto de norma ou da documentação do TQS é reproduzido.
- A API do TQS varia entre versões. Os scripts toleram diferenças e avisam, mas resultados de leitura devem ser conferidos na interface do TQS na primeira vez em cada versão.
- Requer Windows com TQS licenciado (V23+). TQS é marca da TQS Informática Ltda. Esta skill não tem vínculo com a empresa.
