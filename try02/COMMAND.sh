ollama run  qwen3:30b-a3b-instruct-2507-q4_K_M --format json << 'EOF'
You are an expert classifier for plastic PYROLYSIS research.

Your task:
Determine whether the following abstract describes research directly related to
plastic or polymer pyrolysis (thermal or catalytic decomposition of plastics).

Return STRICT JSON with fields:
{
  "pyrolysis_related": "YES" or "NO",
  "reason": "<one sentence>"
}

Here is the abstract:
<<<
Plastics in many forms have been regarded as one of the most polluting material in the modern world. Therefore, a study has been conducted to check the effectiveness of catalyst-fly ash and zeolite on the production of biofuel from plastics as an attempt to contribute in the reduction of plastic waste pollution to the environment. A lab scale plastic pyrolysis plant has been constructed and feed particle size of 3 ± 1.5 cm2 were used as raw materials. The samples were tested in the pyrolysis plant at about 500 ± 30 °C with and without the presence of catalyst. The catalyst loading ratio of 1:10 catalyst to feed is applied. The result shows that plastic pyrolysis (bottle) without any catalysts have the highest liquid fraction yield with an average yield of 24% while those with catalyst has lower yield (16–22%). Carry bags with zeolite catalyst yield liquid fraction of 22% at a conversion rate of 47%. The inclusion of catalyst has lowered the yield but has produce oil yield of superior quality compared with the samples without catalyst. Engine characteristics study showed that blend fuel D80PO20 (80:20 diesel: plastic pyrolytic oil) have shown similar cylinder pressure during combustion with diesel. Higher brake thermal efficiency and lower brake specific energy consumption were also observed from the engine testing using the blend fuel. The blend fuel has lower hydrocarbon emissions while oxides of nitrogen reduces by 19% and 26% compared to pure diesel and PPO respectively.
>>>
EOF

