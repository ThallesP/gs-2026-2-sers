#!/usr/bin/env python3
"""
Modelo de cálculos energéticos, dimensionamento fotovoltaico/bateria,
análise econômico-ambiental e simulação de telemetria para o módulo SERS
do Neighborhood Action Dashboard (Global Solution 2026.2 — CitizenTech).

Integrantes (1CCPA):
- Thalles Passos da Cunha (RM 574879)
- Waldir Arthur Holanda de Sousa (RM 576869)

Premissas e referências:
- Equação base: E = (P * t) / 1000
- Período mensal padrão: 30 dias; ano comercial: 360 dias (sensibilidade 365 dias)
- Fatores médios anuais do SIN (MCTI/SIRENE):
  * 2025: 0,0461 tCO2/MWh
  * 2024: 0,0545 tCO2/MWh
  * 2023: 0,0385 tCO2/MWh
  * 2021 (estresse hídrico): 0,1263 tCO2/MWh
  * Referência ilustrativa de meses secos (vídeo): 0,0850 tCO2/MWh
"""

from __future__ import annotations

import json
from pathlib import Path


def energia_kwh(potencia_w: float, horas: float, quantidade: int = 1) -> float:
    """Calcula energia elétrica consumida em kWh: E = (P * t) / 1000 * qtd."""
    return (potencia_w * horas / 1000.0) * quantidade


def calcular_modelo() -> dict:
    # Parâmetros gerais do espaço comunitário (Praça Comunitária Urbana)
    qtd_postes = 10
    horas_noite = 12.0  # 18h00 às 06h00
    horas_pico = 5.0    # 18h00 às 23h00
    horas_madrugada = 7.0  # 23h00 às 06h00
    dias_mes = 30
    dias_ano_comercial = 360  # 12 meses de 30 dias (base principal alinhada ao vídeo)
    dias_ano_civil = 365      # sensibilidade de ano calendário
    tarifa_brl_kwh = 0.85     # R$/kWh (premissa de referência ANEEL)

    # Fatores de emissão do SIN (tCO2/MWh = kg CO2/kWh * 1000 -> kg CO2/MWh / 1000)
    fatores_sin = {
        "mcti_2025": {
            "label": "MCTI SIN 2025 (média anual oficial)",
            "tco2_mwh": 0.0461,
            "fonte": "MCTI / SIRENE — Fator Médio Anual SIN 2025",
        },
        "mcti_2024": {
            "label": "MCTI SIN 2024 (média anual oficial)",
            "tco2_mwh": 0.0545,
            "fonte": "MCTI / SIRENE — Fator Médio Anual SIN 2024",
        },
        "mcti_2023": {
            "label": "MCTI SIN 2023 (mínimo histórico recente)",
            "tco2_mwh": 0.0385,
            "fonte": "MCTI / SIRENE — Fator Médio Anual SIN 2023",
        },
        "referencia_seca_video": {
            "label": "Cenário seco ilustrativo do SIN (referência do vídeo)",
            "tco2_mwh": 0.0850,
            "fonte": "Premissa ilustrativa de meses secos do SIN (ex.: set–out/2024: 0,0917–0,1127 tCO2/MWh)",
        },
        "mcti_2021_estresse": {
            "label": "MCTI SIN 2021 (estresse hídrico severo)",
            "tco2_mwh": 0.1263,
            "fonte": "MCTI / SIRENE — Fator Médio Anual SIN 2021",
        },
    }

    # --- Cenário Atual: Vapor de Sódio 250 W na rede ---
    p_atual_w = 250.0
    e_dia_atual = energia_kwh(p_atual_w, horas_noite, qtd_postes)
    e_mes_atual = e_dia_atual * dias_mes
    e_ano_360_atual = e_dia_atual * dias_ano_comercial
    e_ano_365_atual = e_dia_atual * dias_ano_civil
    custo_mes_atual = e_mes_atual * tarifa_brl_kwh
    custo_ano_360_atual = e_ano_360_atual * tarifa_brl_kwh

    # --- Alternativa A: LED 100 W convencional na rede ---
    p_alt_a_w = 100.0
    e_dia_a = energia_kwh(p_alt_a_w, horas_noite, qtd_postes)
    e_mes_a = e_dia_a * dias_mes
    e_ano_360_a = e_dia_a * dias_ano_comercial
    e_ano_365_a = e_dia_a * dias_ano_civil
    custo_mes_a = e_mes_a * tarifa_brl_kwh
    custo_ano_360_a = e_ano_360_a * tarifa_brl_kwh
    econ_mes_kwh_a = e_mes_atual - e_mes_a
    econ_pct_a = (econ_mes_kwh_a / e_mes_atual) * 100.0
    econ_mes_brl_a = custo_mes_atual - custo_mes_a
    capex_a_brl = 6000.0  # 10x (R$ 450 luminária LED pública 100W + R$ 150 instalação)
    opex_manut_mes_a = 30.0  # reserva de manutenção preventiva (R$ 360/ano)
    payback_simples_meses_a = capex_a_brl / econ_mes_brl_a

    # --- Alternativa B: Solar Fotovoltaica Off-Grid (LED 80 W + LiFePO4 + PIR) ---
    p_alt_b_w = 80.0
    dimerizacao_pct = 0.30
    p_alt_b_dim_w = p_alt_b_w * dimerizacao_pct  # 24 W
    acionamentos_pir_noite = 15
    duracao_pir_min = 2.0
    horas_boost_pir = (acionamentos_pir_noite * duracao_pir_min) / 60.0  # 0,5 h

    # Carga elétrica local suprida pelo sistema solar (não retirada da rede)
    wh_dia_poste_pico = p_alt_b_w * horas_pico  # 400 Wh
    wh_dia_poste_madrugada_base = p_alt_b_dim_w * horas_madrugada  # 168 Wh
    wh_dia_poste_sem_pir = wh_dia_poste_pico + wh_dia_poste_madrugada_base  # 568 Wh
    wh_dia_poste_boost_pir = (p_alt_b_w - p_alt_b_dim_w) * horas_boost_pir  # 28 Wh
    wh_dia_poste_realista = wh_dia_poste_sem_pir + wh_dia_poste_boost_pir  # 596 Wh
    wh_dia_poste_100pct = p_alt_b_w * horas_noite  # 960 Wh (pior caso sem dimerização)

    e_mes_local_b_sem_pir = (wh_dia_poste_sem_pir / 1000.0) * qtd_postes * dias_mes
    e_mes_local_b_realista = (wh_dia_poste_realista / 1000.0) * qtd_postes * dias_mes
    e_mes_local_b_100pct = (wh_dia_poste_100pct / 1000.0) * qtd_postes * dias_mes

    # Dimensionamento de bateria LiFePO4 e módulo FV por poste
    eficiencia_driver_controlador = 0.90
    wh_bateria_dia_poste = wh_dia_poste_realista / eficiencia_driver_controlador  # ~662,2 Wh/dia
    dias_autonomia_alvo = 3
    dod_lifepo4 = 0.80
    capacidade_bat_min_kwh = (wh_bateria_dia_poste * dias_autonomia_alvo) / (dod_lifepo4 * 1000.0)  # 2,48 kWh
    bateria_especificada_v = 25.6
    bateria_especificada_ah = 100.0
    bateria_especificada_kwh = (bateria_especificada_v * bateria_especificada_ah) / 1000.0  # 2,56 kWh
    autonomia_real_dias = (bateria_especificada_kwh * dod_lifepo4 * 1000.0) / wh_bateria_dia_poste

    hsp_medio_sp = 4.5       # Horas de Sol Pleno média anual (CRESESB/INPE — Sudeste)
    hsp_inverno_sp = 3.5     # Pior mês típico de inverno
    performance_ratio = 0.75 # Perdas térmicas, sujeira, MPPT e ciclo carga/descarga
    potencia_fv_min_wp = wh_bateria_dia_poste / (hsp_inverno_sp * performance_ratio)  # ~252,3 Wp
    modulo_fv_especificado_wp = 330.0
    geracao_dia_media_wh = modulo_fv_especificado_wp * hsp_medio_sp * performance_ratio
    geracao_dia_inverno_wh = modulo_fv_especificado_wp * hsp_inverno_sp * performance_ratio

    # Custos estimados Alternativa B
    # Faixa compacta (luminária solar integrada comercial ~R$ 2.000/poste -> R$ 20.000 total -> payback ~26,1 meses)
    # Faixa autonomia estendida 3 dias (painel 330Wp + LiFePO4 2,56kWh dedicados ~R$ 3.200/poste -> R$ 32.000 total)
    capex_b_compacto_brl = 20000.0
    capex_b_estendido_brl = 32000.0
    opex_fatura_mes_b = 0.0
    opex_manut_mes_b = 50.0  # limpeza semestral de painéis + inspeção PIR (R$ 600/ano)
    vida_util_bateria_anos = 7  # ~2.500 a 3.000 ciclos LiFePO4
    payback_compacto_fatura_meses = capex_b_compacto_brl / custo_mes_atual
    payback_compacto_liquido_meses = capex_b_compacto_brl / (custo_mes_atual - opex_manut_mes_b)
    payback_estendido_fatura_meses = capex_b_estendido_brl / custo_mes_atual

    # Cálculo de emissões evitadas em todos os fatores SIN
    emissoes_evitadas = {}
    for key, f in fatores_sin.items():
        # tCO2/MWh * (kWh / 1000) * 1000 = tCO2/MWh * kWh = kg CO2
        kg_b_360 = e_ano_360_atual * f["tco2_mwh"]
        kg_b_365 = e_ano_365_atual * f["tco2_mwh"]
        kg_a_360 = (e_ano_360_atual - e_ano_360_a) * f["tco2_mwh"]
        emissoes_evitadas[key] = {
            **f,
            "alt_a_kg_co2_ano_360": round(kg_a_360, 1),
            "alt_b_kg_co2_ano_360": round(kg_b_360, 1),
            "alt_b_kg_co2_ano_365": round(kg_b_365, 1),
        }

    # Simulação horária de 72 horas (1 dia ensolarado + 2 dias nublados) para 1 poste da Alt B
    # Demonstra autonomia da bateria LiFePO4 (2,56 kWh) e atuação do sensor PIR
    simulacao_72h = []
    soc_wh = bateria_especificada_kwh * 1000.0 * 0.90  # inicia às 06h com 90% SoC
    bat_max_wh = bateria_especificada_kwh * 1000.0
    perfil_irradiacao = {
        6: 0.05, 7: 0.20, 8: 0.45, 9: 0.70, 10: 0.90, 11: 1.00,
        12: 1.00, 13: 0.92, 14: 0.75, 15: 0.50, 16: 0.25, 17: 0.08,
    }
    fator_clima_dia = [1.0, 0.25, 0.20]  # Dia 1: sol pleno; Dias 2 e 3: nublado/chuvoso
    pir_por_hora_madrugada = {23: 4, 0: 3, 1: 2, 2: 1, 3: 1, 4: 2, 5: 2}

    for dia in range(3):
        clima_mult = fator_clima_dia[dia]
        # Normaliza perfil solar para gerar geracao_dia_media_wh no dia de sol pleno
        soma_perfil = sum(perfil_irradiacao.values())
        for offset in range(24):
            hora = (6 + offset) % 24
            h_idx = dia * 24 + offset
            geracao_wh = (
                (perfil_irradiacao.get(hora, 0.0) / soma_perfil)
                * geracao_dia_media_wh
                * clima_mult
            )
            if 18 <= hora <= 22:
                modo = "Pico (100%)"
                pir_eventos = 0
                consumo_led_wh = p_alt_b_w
            elif hora == 23 or 0 <= hora <= 5:
                modo = "Dimerizado (30% + PIR)"
                pir_eventos = pir_por_hora_madrugada.get(hora, 1)
                boost_h = (pir_eventos * duracao_pir_min) / 60.0
                consumo_led_wh = p_alt_b_dim_w + (p_alt_b_w - p_alt_b_dim_w) * boost_h
            else:
                modo = "Desligado (Dia)"
                pir_eventos = 0
                consumo_led_wh = 0.0

            consumo_bat_wh = consumo_led_wh / eficiencia_driver_controlador
            soc_wh = max(bat_max_wh * (1.0 - dod_lifepo4), min(bat_max_wh, soc_wh + geracao_wh - consumo_bat_wh))
            simulacao_72h.append({
                "hora_seq": h_idx,
                "dia": dia + 1,
                "clima": "Ensolarado" if dia == 0 else "Nublado/Chuvoso",
                "hora_rel": f"{hora:02d}:00",
                "geracao_fv_wh": round(geracao_wh, 1),
                "consumo_led_wh": round(consumo_led_wh, 1),
                "pir_acionamentos": pir_eventos,
                "modo": modo,
                "soc_pct": round((soc_wh / bat_max_wh) * 100.0, 1),
            })

    # Telemetria simulada por poste (10 postes da Praça Comunitária)
    zonas_postes = [
        ("P-01", "Entrada Principal Norte", 88, 18, "Normal"),
        ("P-02", "Pista de Caminhada Leste", 85, 22, "Normal"),
        ("P-03", "Playground Infantil", 91, 12, "Normal"),
        ("P-04", "Quadra Poliesportiva", 84, 24, "Normal"),
        ("P-05", "Ponto de Ônibus Adjacente", 82, 26, "Normal"),
        ("P-06", "Área de Convivência Central", 89, 16, "Normal"),
        ("P-07", "Academia ao Ar Livre", 87, 14, "Normal"),
        ("P-08", "Passarela Sul", 76, 11, "Atenção (Sombra parcial)"),
        ("P-09", "Ciclovia Lateral Oeste", 86, 19, "Normal"),
        ("P-10", "Entrada Secundária Sul", 90, 13, "Normal"),
    ]
    postes = [
        {
            "id": pid,
            "localizacao": loc,
            "potencia_nominal_w": int(p_alt_b_w),
            "soc_bateria_pct": soc,
            "acionamentos_pir_ultima_noite": pir,
            "consumo_local_noite_wh": round(
                wh_dia_poste_sem_pir + (p_alt_b_w - p_alt_b_dim_w) * (pir * duracao_pir_min / 60.0), 1
            ),
            "consumo_rede_kwh": 0.0,
            "status": status,
        }
        for pid, loc, soc, pir, status in zonas_postes
    ]

    return {
        "projeto": {
            "nome": "Neighborhood Action Dashboard — Módulo SERS (Praça Comunitária Inteligente e Sustentável)",
            "disciplina": "Soluções em Energias Renováveis e Sustentáveis (SERS)",
            "curso": "Ciência da Computação — Turma 1CCPA",
            "edicao": "Global Solution 2026.2 (CitizenTech)",
            "integrantes": [
                {"nome": "Thalles Passos da Cunha", "rm": "574879"},
                {"nome": "Waldir Arthur Holanda de Sousa", "rm": "576869"},
            ],
            "nota_metodologica": (
                "Todos os valores apresentados constituem projeções condicionadas às premissas "
                "técnicas e tarifárias documentadas, baseadas em dados simulados e referências públicas "
                "(ANEEL, EPE, MCTI/SIRENE, CRESESB/INPE e ABNT NBR 5101)."
            ),
        },
        "premissas": {
            "qtd_postes": qtd_postes,
            "horas_noite": horas_noite,
            "horas_pico": horas_pico,
            "horas_madrugada": horas_madrugada,
            "dias_mes": dias_mes,
            "dias_ano_comercial": dias_ano_comercial,
            "dias_ano_civil": dias_ano_civil,
            "tarifa_brl_kwh": tarifa_brl_kwh,
            "dimerizacao_madrugada_pct": int(dimerizacao_pct * 100),
            "acionamentos_pir_noite_poste": acionamentos_pir_noite,
            "duracao_boost_pir_min": duracao_pir_min,
        },
        "cenarios": {
            "atual_vapor_sodio": {
                "nome": "Cenário Atual — Vapor de Sódio 250 W (Rede)",
                "potencia_unitaria_w": p_atual_w,
                "potencia_total_w": p_atual_w * qtd_postes,
                "consumo_rede_dia_kwh": round(e_dia_atual, 2),
                "consumo_rede_mes_kwh": round(e_mes_atual, 2),
                "consumo_rede_ano_360_kwh": round(e_ano_360_atual, 2),
                "consumo_rede_ano_365_kwh": round(e_ano_365_atual, 2),
                "consumo_local_solar_mes_kwh": 0.0,
                "custo_fatura_mes_brl": round(custo_mes_atual, 2),
                "custo_fatura_ano_360_brl": round(custo_ano_360_atual, 2),
                "economia_rede_pct": 0.0,
                "renovavel_local_pct": 0.0,
                "capex_estimado_brl": 0.0,
            },
            "alternativa_a_led_rede": {
                "nome": "Alternativa A — LED 100 W Convencional (Rede)",
                "potencia_unitaria_w": p_alt_a_w,
                "potencia_total_w": p_alt_a_w * qtd_postes,
                "consumo_rede_dia_kwh": round(e_dia_a, 2),
                "consumo_rede_mes_kwh": round(e_mes_a, 2),
                "consumo_rede_ano_360_kwh": round(e_ano_360_a, 2),
                "consumo_rede_ano_365_kwh": round(e_ano_365_a, 2),
                "consumo_local_solar_mes_kwh": 0.0,
                "custo_fatura_mes_brl": round(custo_mes_a, 2),
                "custo_fatura_ano_360_brl": round(custo_ano_360_a, 2),
                "economia_rede_mes_kwh": round(econ_mes_kwh_a, 2),
                "economia_rede_pct": round(econ_pct_a, 1),
                "economia_fatura_mes_brl": round(econ_mes_brl_a, 2),
                "renovavel_local_pct": 0.0,
                "capex_estimado_brl": capex_a_brl,
                "opex_manutencao_mes_brl": opex_manut_mes_a,
                "payback_simples_meses": round(payback_simples_meses_a, 1),
            },
            "alternativa_b_solar_pir": {
                "nome": "Alternativa B (Escolhida) — Solar Off-Grid LED 80 W + LiFePO4 + PIR",
                "potencia_unitaria_w": p_alt_b_w,
                "potencia_dimerizada_w": p_alt_b_dim_w,
                "potencia_total_nominal_w": p_alt_b_w * qtd_postes,
                "consumo_rede_dia_kwh": 0.0,
                "consumo_rede_mes_kwh": 0.0,
                "consumo_rede_ano_360_kwh": 0.0,
                "consumo_rede_ano_365_kwh": 0.0,
                "carga_local_poste_sem_pir_wh_dia": round(wh_dia_poste_sem_pir, 1),
                "carga_local_poste_realista_wh_dia": round(wh_dia_poste_realista, 1),
                "carga_local_poste_100pct_wh_dia": round(wh_dia_poste_100pct, 1),
                "consumo_local_solar_mes_sem_pir_kwh": round(e_mes_local_b_sem_pir, 1),
                "consumo_local_solar_mes_realista_kwh": round(e_mes_local_b_realista, 1),
                "consumo_local_solar_mes_100pct_kwh": round(e_mes_local_b_100pct, 1),
                "custo_fatura_mes_brl": opex_fatura_mes_b,
                "custo_fatura_ano_360_brl": 0.0,
                "opex_manutencao_mes_brl": opex_manut_mes_b,
                "economia_rede_mes_kwh": round(e_mes_atual, 2),
                "economia_rede_pct": 100.0,
                "economia_fatura_mes_brl": round(custo_mes_atual, 2),
                "economia_liquida_mes_brl": round(custo_mes_atual - opex_manut_mes_b, 2),
                "renovavel_local_pct": 100.0,
                "horas_operacao_eficiente_dia": horas_madrugada,
                "capex_compacto_brl": capex_b_compacto_brl,
                "capex_estendido_3dias_brl": capex_b_estendido_brl,
                "payback_compacto_fatura_meses": round(payback_compacto_fatura_meses, 1),
                "payback_compacto_liquido_meses": round(payback_compacto_liquido_meses, 1),
                "payback_estendido_fatura_meses": round(payback_estendido_fatura_meses, 1),
                "vida_util_bateria_anos": vida_util_bateria_anos,
                "dimensionamento_por_poste": {
                    "demanda_bateria_wh_dia": round(wh_bateria_dia_poste, 1),
                    "capacidade_minima_3d_kwh": round(capacidade_bat_min_kwh, 2),
                    "bateria_especificada": f"LiFePO4 {bateria_especificada_v} V / {int(bateria_especificada_ah)} Ah ({bateria_especificada_kwh:.2f} kWh)",
                    "autonomia_real_dias_dod80": round(autonomia_real_dias, 2),
                    "hsp_medio_h_dia": hsp_medio_sp,
                    "hsp_inverno_h_dia": hsp_inverno_sp,
                    "performance_ratio": performance_ratio,
                    "potencia_fv_min_inverno_wp": round(potencia_fv_min_wp, 1),
                    "modulo_fv_especificado_wp": int(modulo_fv_especificado_wp),
                    "geracao_media_diaria_wh": round(geracao_dia_media_wh, 1),
                    "geracao_inverno_diaria_wh": round(geracao_dia_inverno_wh, 1),
                },
            },
        },
        "emissoes_evitadas_sin": emissoes_evitadas,
        "telemetria_postes": postes,
        "simulacao_72h_poste_unitario": simulacao_72h,
    }


def main() -> None:
    dados = calcular_modelo()
    out_path = Path(__file__).resolve().parent.parent / "data" / "sers_dados_simulados.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(dados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    b = dados["cenarios"]["alternativa_b_solar_pir"]
    a = dados["cenarios"]["alternativa_a_led_rede"]
    atual = dados["cenarios"]["atual_vapor_sodio"]
    em = dados["emissoes_evitadas_sin"]

    print("=== RESUMO VERIFICADO — SERS (GLOBAL SOLUTION 2026.2) ===")
    print(f"Atual (10x 250W x 12h): {atual['consumo_rede_mes_kwh']:.0f} kWh/mês | R$ {atual['custo_fatura_mes_brl']:.2f}/mês | {atual['consumo_rede_ano_360_kwh']:.0f} kWh/ano (360d) / {atual['consumo_rede_ano_365_kwh']:.0f} kWh/ano (365d)")
    print(f"Alt A (10x 100W LED):   {a['consumo_rede_mes_kwh']:.0f} kWh/mês (-{a['economia_rede_pct']:.0f}%) | R$ {a['custo_fatura_mes_brl']:.2f}/mês | CAPEX R$ {a['capex_estimado_brl']:.0f} | Payback {a['payback_simples_meses']} meses")
    print(f"Alt B (10x 80W Solar):  0 kWh/mês da rede (-100%) | Carga solar local: {b['consumo_local_solar_mes_sem_pir_kwh']}–{b['consumo_local_solar_mes_realista_kwh']} kWh/mês (até {b['consumo_local_solar_mes_100pct_kwh']} sem dimer.)")
    print(f"  Dimensionamento/poste: {b['dimensionamento_por_poste']['modulo_fv_especificado_wp']} Wp + {b['dimensionamento_por_poste']['bateria_especificada']} -> {b['dimensionamento_por_poste']['autonomia_real_dias_dod80']} dias autonomia (DoD 80%)")
    print(f"  Payback Alt B (fatura): {b['payback_compacto_fatura_meses']} meses (kit R$ 20k) | {b['payback_estendido_fatura_meses']} meses (banco estendido 3d R$ 32k)")
    print("Emissões evitadas (Alt B, 360d / 365d):")
    for k, v in em.items():
        print(f"  - {k}: {v['tco2_mwh']} tCO2/MWh -> {v['alt_b_kg_co2_ano_360']} kg/ano (360d) | {v['alt_b_kg_co2_ano_365']} kg/ano (365d)")
    min_soc = min(p["soc_pct"] for p in dados["simulacao_72h_poste_unitario"])
    print(f"Simulação 72h (1 sol + 2 nublados): SoC mínimo atingido = {min_soc}% (limite DoD = 20%)")
    print(f"JSON salvo em: {out_path}")


if __name__ == "__main__":
    main()
