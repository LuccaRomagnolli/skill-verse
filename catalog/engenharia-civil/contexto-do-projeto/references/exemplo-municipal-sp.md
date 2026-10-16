# Projeto demonstrativo — São Paulo/SP

Exemplo de exercício para testar a ficha, **não** projeto aprovado. Obra fictícia: residência unifamiliar, dois pavimentos, 180 m², ambiente urbano. Não há endereço/lote, portanto **não** se concluem zoneamento, recuos, coeficientes, exigências dos Bombeiros nem aprovação. Reconfirme a versão consolidada das fontes na data do uso.

Fontes municipais oficiais consultadas em 2026-10-15:
- [Lei municipal 16.642/2017, Código de Obras e Edificações, texto consolidado](https://legislacao.prefeitura.sp.gov.br/lei-16642-de-09-de-maio-de-2017/consolidado), art. 1º: escopo geral das regras de projeto/licenciamento/execução.
- [Lei municipal 16.402/2016, parcelamento, uso e ocupação do solo, texto consolidado](https://legislacao.prefeitura.sp.gov.br/lei-16402-de-22-de-marco-de-2016/consolidado), art. 1º: disciplina uso e ocupação do solo; parâmetros do lote dependem do zoneamento concreto.

Na pasta vazia do exercício, a partir da pasta da skill:

```bash
python3 scripts/contexto.py iniciar --pasta <pasta-demo> --projeto "Residência demonstrativa" --municipio "São Paulo" --uf SP --uso residencial-unifamiliar --pavimentos 2 --area 180 --ambiente urbano
python3 scripts/contexto.py fonte --pasta <pasta-demo> --checklist c1 --esfera municipal --tipo "Código de Obras" --titulo "Lei municipal 16.642/2017, texto consolidado" --numero 16642 --ano 2017 --url "https://legislacao.prefeitura.sp.gov.br/lei-16642-de-09-de-maio-de-2017/consolidado" --vigente sim
python3 scripts/contexto.py requisito --pasta <pasta-demo> --fonte f1 --item "art. 1º" --criterio "aplicar o COE ao projeto e licenciamento" --impacto "identificar procedimento e parâmetros aplicáveis ao lote"
python3 scripts/contexto.py fonte --pasta <pasta-demo> --checklist c2 --esfera municipal --tipo "Uso e Ocupação do Solo" --titulo "Lei municipal 16.402/2016, texto consolidado" --numero 16402 --ano 2016 --url "https://legislacao.prefeitura.sp.gov.br/lei-16402-de-22-de-marco-de-2016/consolidado" --vigente sim
python3 scripts/contexto.py requisito --pasta <pasta-demo> --fonte f2 --item "art. 1º" --criterio "identificar o zoneamento e a disciplina de uso do lote" --impacto "consultar mapas e parâmetros oficiais para o endereço"
python3 scripts/contexto.py pendencia --pasta <pasta-demo> --texto "Obter endereço/cadastro do lote e conferir zoneamento, recuos e parâmetros específicos nas fontes vigentes" --responsavel "projetista"
python3 scripts/contexto.py resumo --pasta <pasta-demo>
```

O resumo deve mostrar duas fontes, dois requisitos e a pendência do lote. Na sessão seguinte, rode `resumo` antes de projetar. Não converta este exemplo em aprovação automática: o art. 1º de cada lei apenas estabelece o escopo geral; valores numéricos precisam de itens específicos e confirmação para o lote.
