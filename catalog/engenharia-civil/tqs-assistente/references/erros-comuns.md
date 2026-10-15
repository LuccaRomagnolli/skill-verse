# Erros comuns na automação do TQS

| Sintoma | Causa provável | Solução |
|---|---|---|
| `ModuleNotFoundError: TQS` | wheel não instalado neste Python | `tqs_ambiente.py` mostra o `.whl` e o comando `pip install` (com permissão) |
| `OSError`/`WinError 193`/"DLL" ao importar | arquitetura do Python (32/64 bits) diferente da exigida | usar o Python indicado por `tqs_ambiente.py` (`py -3-32` ou `py -3-64`) |
| `AttributeError` em nome da API | nome diferente nesta versão do TQS | `tqs_ambiente.py --introspectar <Módulo>` e ajustar |
| `file.Open` devolve ≠ 0 | nome do edifício errado ou fora da árvore | listar a raiz (`BuildingRoot`) e conferir o nome exato (acentos, espaços) |
| `OpenModel` devolve ≠ 0 | pasta atual não é do edifício | entrar antes com `RootFolder(nome)` |
| Gravação sem efeito / arquivo travado | edifício aberto no TQS ao mesmo tempo | fechar o edifício no TQS antes de gravar/processar |
| Processamento termina rápido demais | pasta atual errada (`TaskFolder`) ou edifício inexistente | conferir o plano (`tqs_processar.py` sem `--executar`) e os relatórios do Gerenciador |
| Contorno de laje "sem contorno definido" após alterar pilares/vigas | intersecções desatualizadas | `floor.util.DoIntersections()` em todas as plantas antes de salvar o modelo |
| Fundação com erro de extração após mudar seção de pilar | excentricidade pilar × fundação | pilar fictício na fundação (dados de fundação) ou reposicionar |
| Valores 100× errados | cm × m (Modelador/TQSDwg em cm; cotas de piso em m) | converter por script. Ver unidades em `tqspy-api.md` |
| Cargas estranhas | tf × kN | TQS em tf. Converter por script (1 tf = 9,80665 kN) |
