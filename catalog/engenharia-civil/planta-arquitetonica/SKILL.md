---
name: planta-arquitetonica
description: Organiza uma planta baixa de DWG/DXF ou de PDF/imagem calibrada, gera cortes verticais arquitetônicos em DXF e prepara a modelagem de paredes, pisos, portas e janelas no Revit ou Archicad. Use quando o usuário pedir "cortes da planta baixa", "corte A-A no CAD", "transforme esta planta em modelo BIM", "modele a arquitetura no Revit/Archicad" ou trouxer uma planta 2D para cortar ou modelar.
---

# Planta arquitetônica, cortes e modelo BIM

A fonte única é um `planta-arquitetonica.json` com medidas em metros, revisão, origem, níveis, paredes, aberturas, pisos e linhas de corte. Consulte `assets/planta.exemplo.json`. A planta 2D não fornece automaticamente pé-direito, espessura, peitoril, altura de porta/janela, estrutura de piso, cobertura ou escada. Solicite esses dados e marque como pendência o que não estiver documentado; não invente medidas.

## 1. Ler a fonte e registrar a revisão

Leia `projeto-contexto.json` quando existir e registre arquivo original, revisão, unidade, ponto de origem e ao menos duas medidas conhecidas. Trabalhe numa cópia da obra. No CAD, use `autocad-assistente` para abrir DWG/DXF, inspecionar layers e blocos e medir duas distâncias; confirme `INSUNITS` com geometria conhecida. DWG requer AutoCAD ou conversão autorizada para DXF. Se houver um layer com **eixos de parede** em LINE/LWPOLYLINE no DXF ASCII, gere um rascunho (coordenadas do corte em metros):

```bash
python3 scripts/planta.py extrair-dxf planta.dxf --layer ARQ-EIXO-PAREDE --unidade m --projeto Obra-1 --revisao A --nivel Terreo --cota-m 0 --altura-m 3 --espessura-m 0.15 --corte A-A 2 -1 2 4 --saida planta-arquitetonica.json
```

O script confere `$INSUNITS` quando definido. Sem layer de eixos, use o AutoCAD para medir/transcrever o centro das paredes e as posições de vãos; contornos duplos, hachuras, blocos e xrefs não são reconhecidos automaticamente como elementos BIM. Acrescente pisos e aberturas ao JSON e mostre o mapa ao usuário antes de avançar.

Para PDF/imagem, abra a página e identifique uma cota escrita ou medida de levantamento, escala e origem. Rasterize a página PDF em imagem por ferramenta local disponível ou use uma captura da página inteira, sem redimensionar depois. Trace os pontos visíveis em pixels no formato do exemplo `assets/planta-pixels.exemplo.json`. `centro_px` e `largura_px` são medidas ao longo da parede. Peitoril, altura da abertura, espessura, pé-direito e níveis continuam em metros fornecidos pelo projeto. Calibre:

```bash
python3 scripts/planta.py calibrar planta-pixels.json --origem-px 100 100 --referencia-px 500 100 --distancia-m 4 --controle-px 500 100 500 400 --controle-distancia-m 3 --saida planta-arquitetonica.json
```

Confira uma **segunda dimensão independente** no arquivo calibrado; o comando reprova desvio acima de 2%. Sem esse controle, o manifesto mantém a conferência pendente. Se não coincidir, corrija escala, rotação ou traçado antes de gerar. PDF vetorial pode permitir leitura mais precisa no CAD; PDF escaneado e imagem dependem do traçado e da qualidade da fonte. Guarde a fonte original e o registro das medidas conferidas.

## 2. Validar e gerar os cortes

Use `scripts/planta.py` a partir desta skill. A linha `cortes[].de/ate` determina o sentido da vista; o DXF representa o plano de corte com interseções de paredes, aberturas que ele atravessa, pisos e níveis. Não projeta elementos atrás do plano nem calcula cobertura, escada, terreno ou detalhes executivos.

```bash
python3 scripts/planta.py validar planta-arquitetonica.json
python3 scripts/planta.py gerar planta-arquitetonica.json --saida desenhos-arquitetura
```

O diretório contém `corte-<id>.dxf`, `planos-bim.json` e `manifesto-arquitetura.json` com revisão, SHA-256 e avisos. Abra cada DXF no AutoCAD, confira escala, cotas e aberturas contra a planta e redesenhe cotas associativas; salve DWG/PDF no aplicativo. Uma parede que o corte não atravessa não aparece. Corte quase paralelo ou sem interseções exige revisão manual. Registre arquivos e pendências em `projeto-contexto.json`.

## 3. Modelar no Revit

Use a skill `revit-assistente` para diagnosticar o MCP e o projeto aberto. Leia `planos-bim.json.revit` como **plano**, não como lote pronto para execução. Antes de criar, remova níveis existentes da proposta, confira famílias/tipos de parede e piso, e substitua `$tipo:<id>` das portas/janelas pelos `typeId` lidos com `get_available_family_types`. Crie paredes primeiro, salve o ID retornado para cada `id_origem` e substitua `$parede:<id>` por `hostWallId`. Remova `id_origem` dos argumentos enviados ao MCP. Mostre ao usuário categoria, número de elementos, níveis, unidades, tipos e RVT de destino; execute somente após confirmação em cópia salva. Leia de volta IDs, níveis, geometrias, alturas, espessuras, peitoris e hospedeiros; compare com o JSON e salve o RVT. O pack ainda não cria vistas de corte do Revit automaticamente: abra as vistas manualmente e confira o resultado.

## 4. Modelar no Archicad

Use `archicad-assistente` para escolher a instância e confirmar Tapir, PLN e pavimentos reais com `GetStories`. Em `planos-bim.json.archicad`, resolva `$pavimento:<id>` com `floorIndex` e `$favorito:*` com favoritos reais do template; confira material/estrutura Basic do piso. Remova `id_origem` dos parâmetros enviados. Chame `describe_api_command` para validar cada schema, faça prévia com `confirm=false`, mostre os lotes e peça confirmação no PLN copiado. Após criar paredes, mapeie `id_origem` aos GUIDs; só então resolva `$parede:<id>` para portas e janelas. Confira `centerOffset`, orientação, lado de abertura, biblioteca, espessura e peitoril no PLN. Leia todos os elementos criados de volta; salve e audite IFC apenas depois de inspecionar as diferenças. A disponibilidade de portas/janelas depende dos favoritos e bibliotecas do template.

## 5. Outros softwares

Não converta automaticamente paredes arquitetônicas em elementos resistentes. SOLIDWORKS modela componentes e conjuntos específicos, não substitui o modelo arquitetônico da obra. Para troca entre programas, exporte IFC do BIM revisado, reabra no destino e confira classes, unidades, coordenadas e aberturas. O DXF do corte é um desenho 2D.

## Limites e responsabilidade

Os scripts fazem cortes geométricos de apoio e geram prévias de chamadas; não interpretam DWG/PDF/imagem arbitrários, não executam gravações no software e não produzem projeto executivo. PDF/imagem exige traçado e calibração conferidos; DWG/DXF exige mapeamento semântico e revisão das dimensões. Não declare modelagem concluída pelo retorno do MCP: confira a geometria no aplicativo, salve uma cópia e obtenha revisão do profissional responsável. Lotes BIM alteram o projeto e exigem confirmação explícita.
