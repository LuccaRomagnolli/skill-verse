# Continuidade do projeto entre sessões

`projeto-contexto.json` é a fonte compartilhada pelas skills do pack; `projeto-contexto.md` é a leitura humana. Execute `scripts/contexto.py` a partir da pasta da skill e passe `--pasta <pasta-da-obra>` em todos os comandos. A pasta da obra contém também cálculos, desenhos e documentos produzidos pelo cliente. Não coloque nela cópias de normas licenciadas por padrão.

## Ao iniciar ou retomar

```bash
python3 scripts/contexto.py resumo --pasta <pasta-da-obra>
```

Leia `municipio`, `uf`, uso, CAA, fontes, requisitos, decisões, artefatos, **atp**, pendências e `checklist_faltante`. Confira se um artefato citado ainda existe antes de usá-lo. Se a ficha não existir, use `iniciar`; não use `--forcar` numa ficha existente. Confirme com o usuário a obra e a revisão em que continuará.

## Registrar evidência e decisões

```bash
python3 scripts/contexto.py fonte --pasta <pasta-da-obra> --checklist c1 --esfera municipal \
  --tipo "Código de Obras" --titulo "Lei ..." --url "https://fonte-oficial/..." --vigente sim
python3 scripts/contexto.py requisito --pasta <pasta-da-obra> --fonte f1 --item "art. ..." \
  --criterio "afastamento frontal" --valor 5 --unidade m --impacto "recuar a implantação"
python3 scripts/contexto.py decisao --pasta <pasta-da-obra> --assunto "hipótese de apoio da laje L1" \
  --decisao "bordas AEAA, a confirmar na planta" --origem hipotese
python3 scripts/contexto.py pendencia --pasta <pasta-da-obra> --texto "confirmar classe de agressividade" \
  --responsavel "responsável técnico"
```

`fonte` devolve seu ID. Um `requisito` exige URL e vigência confirmada; registre o artigo/item e a unidade, sem transformar uma recomendação em obrigação. Fontes sem vigência comprovada permanecem no checklist. `decisao` registra a origem (`usuario`, `projetista`, `fonte-oficial` ou `hipotese`); uma hipótese não vira dado confirmado por ter sido salva.

Para projeto de estruturas de concreto, registre também a data de protocolo e a escolha da edição normativa em `decisao`, com evidência. A Emenda 1:2026 traz regra transitória de 180 dias; não deduza a edição aplicável só da data atual. A ATP do item 5.3 deve ter classe atribuída pelo projetista e estado rastreável:

```bash
python3 scripts/contexto.py atp --pasta <pasta-da-obra> --classe CC3 --situacao em-andamento \
  --fundamento "edifício com subsolo, classificação informada pelo projetista" --avaliador "profissional independente"
python3 scripts/contexto.py atp --pasta <pasta-da-obra> --classe CC2 --situacao dispensada \
  --fundamento "classificação confirmada; acordo de projetista e contratante" --documento "atp/acordo-assinado.pdf"
```

`dispensada` não é aceita para CC3; `parecer-recebido` exige avaliador e documento. O script confere o arquivo e a coerência básica, **não** verifica a assinatura, a independência, a classificação ou a suficiência da ATP. O responsável técnico confirma esses pontos.

## Registrar a saída e encerrar uma etapa

```bash
python3 scripts/contexto.py artefato --pasta <pasta-da-obra> --tipo "memorial" \
  --caminho "memorial/MEMORIAL.docx" --revisao 0 --estado em-revisao
python3 scripts/contexto.py resolver-pendencia --pasta <pasta-da-obra> --id p1 \
  --solucao "confirmada pela certidão municipal ..."
```

Registre só arquivos que existem dentro da pasta da obra. Estados: `rascunho`, `em-revisao`, `revisado`; use `revisado` somente após a conferência feita pelo responsável competente. Se uma saída vier com alerta de cálculo, conexão ou norma, registre a pendência antes de avançar. Ao terminar a sessão, mostre os arquivos produzidos, as hipóteses ainda abertas e o próximo passo concreto.
