# Respostas e arquivos para o formulário

## Nome da dupla

Preencher manualmente exatamente como aparece no Classroom.

## Caso padrão: Mach 0,8

### Malha próxima ao aerofólio

Enviar: `figuras/01_malha_proxima_aerofolio.png`

### Contornos de pressão

Enviar: `figuras/02_pressao_M08_AoA_1p25.png`

### Cp versus x/c

Enviar: `figuras/03_Cp_M08_AoA_1p25.png`

### Comentário sobre as figuras

A malha não estruturada é formada por elementos triangulares e apresenta forte
refinamento junto à superfície do aerofólio, especialmente nos bordos de ataque
e de fuga, com aumento gradual do tamanho dos elementos em direção ao campo
distante. No caso padrão, com Mach 0,8 e ângulo de ataque de 1,25°, observa-se
uma região de alta pressão no ponto de estagnação do bordo de ataque e uma forte
redução de pressão no extradorso, responsável pela sustentação. A distribuição
de Cp mostra uma recuperação abrupta de pressão no extradorso em torno de
x/c ≈ 0,63, característica de uma onda de choque em escoamento transônico. No
intradorso a recuperação é mais suave. A integração das pressões resultou em
CL = 0,3285, CD = 0,02148 e CMz = 0,03412. Como o modelo é de Euler, não há
arrasto de atrito; o arrasto calculado é essencialmente arrasto de pressão/onda.

## Estudo paramétrico: Mach 0,3

### CL versus ângulo de ataque

Enviar: `figuras/04_CL_vs_AoA_com_experimento.png`

### Contornos de pressão para 0°, 8° e 16°

Enviar os três arquivos:

- `figuras/05_pressao_M03_AoA_00.png`
- `figuras/05_pressao_M03_AoA_08.png`
- `figuras/05_pressao_M03_AoA_16.png`

### Cp versus x/c para 0°, 8° e 16°

Enviar os três arquivos:

- `figuras/06_Cp_M03_AoA_00_com_experimento.png`
- `figuras/06_Cp_M03_AoA_08_com_experimento.png`
- `figuras/06_Cp_M03_AoA_16_com_experimento.png`

### Comparação com os dados experimentais

Em α = 0° há boa concordância entre as distribuições de Cp, com simetria entre
extradorso e intradorso e CL próximo de zero. Entre 2° e 14°, o SU2 reproduz a
tendência aproximadamente linear de CL com o ângulo de ataque, mas superestima
os valores experimentais em cerca de 12% a 15% (erro médio de 13,1%). Em 8°, por
exemplo, o SU2 fornece CL = 1,000, enquanto a interpolação dos dados experimentais
fornece aproximadamente 0,889. O gráfico de Cp mostra que essa diferença está
associada principalmente a um pico de sucção mais intenso previsto no
extradorso pelo modelo invíscido.

As principais fontes de discrepância são o uso das equações de Euler, que
desconsideram camada limite, atrito, transição, espessura de deslocamento e
separação viscosa; os efeitos de Reynolds e as condições do túnel de vento; a
resolução e discretização da malha; e as pequenas diferenças entre os ângulos
simulados (0°, 8° e 16°) e os experimentais (0,0169°, 8,0221° e 16,0373° para
Cp, e valores próximos para CL). Os dados experimentais mostram início de
estol entre aproximadamente 14° e 15°, com queda de CL, fenômeno essencialmente
viscoso que um modelo de Euler estacionário não consegue representar
corretamente.

O caso de 16° não atingiu o critério de convergência mesmo após 9.999 iterações
e uma segunda tentativa por continuação a partir de 14°. Portanto, seu ponto de
CL e suas distribuições de pressão/Cp devem ser interpretados apenas
qualitativamente. Essa falta de convergência é, por si só, uma indicação da
limitação da hipótese de escoamento invíscido estacionário nessa condição de
alto ângulo de ataque, onde o escoamento real é separado e não estacionário.

## Resultados numéricos auxiliares

Os coeficientes calculados estão em `coeficientes_su2.csv`, e a comparação de
CL interpolada nos ângulos simulados está em `comparacao_CL.csv`.
