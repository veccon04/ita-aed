# Resposta sugerida — comentário final

A solução analítica de choque oblíquo para Mach 2 e cunha de
10° fornece β ≈ 39.314°, pressão pós-choque
≈ 170.66 kPa e interseção do choque com y = 0,5 m em
x ≈ 1.1106 m.

Na malha fornecida, a ordem crescente da largura numérica 10–90% do choque foi:

**HLLC — 2ª ordem (0.0439 m) < Roe — 2ª ordem (0.0441 m) < JST — 2ª ordem (0.0522 m) < HLLC — 1ª ordem (0.2123 m) < Lax–Friedrich — solicitado como 2ª ordem (0.2601 m)**

A reconstrução de segunda ordem reduz a dissipação nas regiões suaves e tende a
representar o choque em menos células que o HLLC de primeira ordem. HLLC e Roe
usam a estrutura característica do problema e produzem transições mais nítidas,
mas, sem limitador, podem apresentar overshoot/undershoot (erro dispersivo).
JST é um esquema central estabilizado por dissipação artificial; sua resolução
depende do sensor de pressão. Lax–Friedrich é mais dissipativo e espalha a
descontinuidade por mais células. No SU2 8.5, esquemas centrais não usam MUSCL;
portanto, a opção antiga SPATIAL_ORDER_FLOW foi traduzida para a formulação
compatível com essa versão.
