#!/usr/bin/env python3
"""Executa os cinco casos do Projeto 2 com SU2/MPI e pós-processa no ParaView."""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASE_CONFIG = ROOT / "inv_wedge_HLLC.cfg"
MESH = ROOT / "mesh_wedge_inv.su2"
PARAVIEW_SCRIPT = ROOT / "paraview_postprocess.py"
RESULTS = ROOT / "resultados"

GAMMA = 1.4
MACH_1 = 2.0
THETA_DEG = 10.0
P_1 = 100_000.0
WEDGE_X = 0.5
LINE_Y = 0.5


@dataclass(frozen=True)
class Case:
    directory: str
    label: str
    flux: str
    muscl: bool
    requested_order: str
    effective_order: str


CASES = (
    Case("HLLC_2a_ordem", "HLLC — 2ª ordem", "HLLC", True, "2ND_ORDER", "2ª"),
    Case("HLLC_1a_ordem", "HLLC — 1ª ordem", "HLLC", False, "1ST_ORDER", "1ª"),
    # Esquemas centrais não aceitam reconstrução MUSCL no SU2 8.5.
    Case("JST_2a_ordem", "JST — 2ª ordem", "JST", False, "2ND_ORDER", "2ª"),
    Case(
        "LAX_FRIEDRICH_2a_ordem",
        "Lax–Friedrich — solicitado como 2ª ordem",
        "LAX-FRIEDRICH",
        False,
        "2ND_ORDER",
        "1ª (dissipação do esquema)",
    ),
    Case("ROE_2a_ordem", "Roe — 2ª ordem", "ROE", True, "2ND_ORDER", "2ª"),
)


def replace_option(config: str, name: str, value: str) -> str:
    pattern = rf"(?m)^[ \t]*{re.escape(name)}[ \t]*=.*$"
    replacement = f"{name}= {value}"
    updated, count = re.subn(pattern, replacement, config)
    if count:
        return updated
    return config.rstrip() + f"\n{name}= {value}\n"


def build_config(case: Case, case_dir: Path) -> Path:
    config = BASE_CONFIG.read_text(encoding="utf-8")
    values = {
        "CONV_NUM_METHOD_FLOW": case.flux,
        "MUSCL_FLOW": "YES" if case.muscl else "NO",
        "MESH_FILENAME": MESH.name,
        "CONV_FILENAME": "history",
        "RESTART_FILENAME": "restart_flow",
        "VOLUME_FILENAME": "flow",
        "SURFACE_FILENAME": "surface_flow",
        "OUTPUT_FILES": "(RESTART, PARAVIEW, SURFACE_PARAVIEW)",
        "VOLUME_OUTPUT": "(COORDINATES, SOLUTION, PRIMITIVE)",
        "HISTORY_OUTPUT": "(ITER, RMS_RES, AERO_COEFF)",
    }
    for name, value in values.items():
        config = replace_option(config, name, value)

    header = (
        "% Gerado por solve_project.py para o Projeto 2\n"
        f"% Caso: {case.label}\n"
        f"% SPATIAL_ORDER_FLOW pedido: {case.requested_order}\n"
        f"% Ordem efetiva no SU2 8.5: {case.effective_order}\n"
        "% Em esquemas upwind, MUSCL_FLOW substitui SPATIAL_ORDER_FLOW.\n"
        "% Em esquemas centrais, MUSCL_FLOW deve ser NO.\n\n"
    )
    path = case_dir / "case.cfg"
    path.write_text(header + config, encoding="utf-8")
    return path


def prepare_cases(clean: bool) -> None:
    if clean and RESULTS.exists():
        shutil.rmtree(RESULTS)
    RESULTS.mkdir(exist_ok=True)
    for case in CASES:
        case_dir = RESULTS / case.directory
        case_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MESH, case_dir / MESH.name)
        build_config(case, case_dir)


def find_executable(name: str, fallback: Path | None = None) -> str:
    executable = shutil.which(name)
    if executable:
        return executable
    if fallback and fallback.exists():
        return str(fallback)
    raise RuntimeError(f"{name} não foi encontrado no PATH")


def solver_environment() -> dict[str, str]:
    environment = os.environ.copy()
    # Esta variável foi adicionada durante a instalação, mas tcp,self causa timeout
    # no MPI local deste Mac. Sem ela, OpenMPI escolhe o transporte compartilhado.
    environment.pop("OMPI_MCA_btl", None)
    return environment


def validate_case(case: Case) -> None:
    case_dir = RESULTS / case.directory
    executable = find_executable("SU2_CFD", Path.home() / "opt/su2/bin/SU2_CFD")
    log_path = case_dir / "dryrun.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.run(
            [executable, "-d", "case.cfg"],
            cwd=case_dir,
            env=solver_environment(),
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if process.returncode:
        raise RuntimeError(f"Configuração inválida: {case.label}; veja {log_path}")
    print(f"[ok  ] configuração: {case.label}")


def run_case(case: Case, ranks: int, force: bool) -> None:
    case_dir = RESULTS / case.directory
    completed = case_dir / ".completed"
    flow_file = case_dir / "flow.vtu"
    if completed.exists() and flow_file.exists() and not force:
        print(f"[skip] simulação pronta: {case.label}")
        return

    su2 = find_executable("SU2_CFD", Path.home() / "opt/su2/bin/SU2_CFD")
    if ranks == 1:
        command = [su2, "case.cfg"]
    else:
        mpirun = find_executable("mpirun", Path("/opt/homebrew/bin/mpirun"))
        command = [mpirun, "-np", str(ranks), su2, "case.cfg"]

    log_path = case_dir / "solver.log"
    print(f"[run ] {case.label} ({ranks} rank(s) MPI)")
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(command) + "\n\n")
        process = subprocess.run(
            command,
            cwd=case_dir,
            env=solver_environment(),
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if process.returncode:
        raise RuntimeError(
            f"{case.label} falhou com código {process.returncode}; veja {log_path}"
        )
    if not flow_file.exists():
        raise RuntimeError(f"{case.label} terminou sem gerar {flow_file.name}")
    completed.write_text("SU2_CFD concluído com sucesso\n", encoding="utf-8")


def find_pvpython() -> str:
    return find_executable(
        "pvpython",
        Path("/Applications/ParaView-6.1.1.app/Contents/bin/pvpython"),
    )


def combine_case_images(case_dir: Path) -> None:
    images = [
        case_dir / "01_pressao_dominios.png",
        case_dir / "02_mach_dominios.png",
        case_dir / "03_pressao_plot_over_line.png",
    ]
    if not all(path.exists() for path in images):
        return
    magick = shutil.which("magick")
    if magick:
        subprocess.run(
            [magick, *map(str, images), "-append", str(case_dir / "ENTREGA_CASO.png")],
            check=True,
        )


def postprocess_case(case: Case, force: bool) -> None:
    case_dir = RESULTS / case.directory
    output = case_dir / "03_pressao_plot_over_line.png"
    if output.exists() and not force:
        print(f"[skip] ParaView pronto: {case.label}")
        combine_case_images(case_dir)
        return

    flow = case_dir / "flow.vtu"
    if not flow.exists():
        raise FileNotFoundError(f"Resultado ausente: {flow}")
    print(f"[view] ParaView: {case.label}")
    log_path = case_dir / "paraview.log"
    command = [
        find_pvpython(),
        str(PARAVIEW_SCRIPT),
        "--input",
        str(flow),
        "--output-dir",
        str(case_dir),
        "--title",
        case.label,
    ]
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.run(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if process.returncode:
        raise RuntimeError(f"ParaView falhou para {case.label}; veja {log_path}")
    combine_case_images(case_dir)


def oblique_shock() -> dict[str, float]:
    theta = math.radians(THETA_DEG)
    low = math.asin(1.0 / MACH_1) + 1e-8
    high = math.radians(60.0)

    def residual(beta: float) -> float:
        numerator = 2.0 / math.tan(beta) * (
            MACH_1**2 * math.sin(beta) ** 2 - 1.0
        )
        denominator = MACH_1**2 * (GAMMA + math.cos(2.0 * beta)) + 2.0
        return math.atan(numerator / denominator) - theta

    for _ in range(100):
        middle = (low + high) / 2.0
        if residual(low) * residual(middle) <= 0:
            high = middle
        else:
            low = middle
    beta = (low + high) / 2.0
    mn1 = MACH_1 * math.sin(beta)
    pressure_ratio = 1.0 + 2.0 * GAMMA / (GAMMA + 1.0) * (mn1**2 - 1.0)
    return {
        "beta_deg": math.degrees(beta),
        "pressure_2_pa": P_1 * pressure_ratio,
        "shock_x": WEDGE_X + LINE_Y / math.tan(beta),
    }


def normalized(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def load_pressure_line(case: Case) -> tuple[list[float], list[float]]:
    path = RESULTS / case.directory / "pressao_linha_y_0p5.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise RuntimeError(f"CSV vazio: {path}")
    columns = {normalized(name): name for name in rows[0]}

    x_name = next(
        (original for key, original in columns.items() if key in {"points0", "arclength"}),
        None,
    )
    pressure_name = next(
        (original for key, original in columns.items() if key == "pressure"),
        None,
    )
    if not x_name or not pressure_name:
        raise RuntimeError(f"Colunas inesperadas em {path}: {list(rows[0])}")
    pairs = sorted((float(row[x_name]), float(row[pressure_name])) for row in rows)
    return [pair[0] for pair in pairs], [pair[1] for pair in pairs]


def crossing(x: list[float], pressure: list[float], level: float) -> float:
    for index in range(1, len(x)):
        p0, p1 = pressure[index - 1], pressure[index]
        if (p0 - level) * (p1 - level) <= 0 and p1 != p0:
            return x[index - 1] + (level - p0) * (x[index] - x[index - 1]) / (
                p1 - p0
            )
    return math.nan


def write_summary() -> None:
    theory = oblique_shock()
    p2 = theory["pressure_2_pa"]
    metrics = []
    for case in CASES:
        x, pressure = load_pressure_line(case)
        p10 = P_1 + 0.1 * (p2 - P_1)
        p50 = P_1 + 0.5 * (p2 - P_1)
        p90 = P_1 + 0.9 * (p2 - P_1)
        x10, x50, x90 = (
            crossing(x, pressure, level) for level in (p10, p50, p90)
        )
        metrics.append(
            {
                "caso": case.label,
                "x_choque_50_m": x50,
                "erro_x_m": x50 - theory["shock_x"],
                "largura_10_90_m": x90 - x10,
                "pressao_min_pa": min(pressure),
                "pressao_max_pa": max(pressure),
            }
        )

    with (RESULTS / "resumo_metricas.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(metrics[0]))
        writer.writeheader()
        writer.writerows(metrics)

    ranked = sorted(metrics, key=lambda row: row["largura_10_90_m"])
    ranking = " < ".join(
        f"{row['caso']} ({row['largura_10_90_m']:.4f} m)" for row in ranked
    )
    response = f"""# Resposta sugerida — comentário final

A solução analítica de choque oblíquo para Mach {MACH_1:.0f} e cunha de
{THETA_DEG:.0f}° fornece β ≈ {theory['beta_deg']:.3f}°, pressão pós-choque
≈ {p2/1000:.2f} kPa e interseção do choque com y = 0,5 m em
x ≈ {theory['shock_x']:.4f} m.

Na malha fornecida, a ordem crescente da largura numérica 10–90% do choque foi:

**{ranking}**

A reconstrução de segunda ordem reduz a dissipação nas regiões suaves e tende a
representar o choque em menos células que o HLLC de primeira ordem. HLLC e Roe
usam a estrutura característica do problema e produzem transições mais nítidas,
mas, sem limitador, podem apresentar overshoot/undershoot (erro dispersivo).
JST é um esquema central estabilizado por dissipação artificial; sua resolução
depende do sensor de pressão. Lax–Friedrich é mais dissipativo e espalha a
descontinuidade por mais células. No SU2 8.5, esquemas centrais não usam MUSCL;
portanto, a opção antiga SPATIAL_ORDER_FLOW foi traduzida para a formulação
compatível com essa versão.
"""
    (RESULTS / "RESPOSTA_COMENTARIO.md").write_text(response, encoding="utf-8")


def write_upload_guide() -> None:
    lines = [
        "# Guia de upload",
        "",
        "Caso padrão HLLC 2ª ordem:",
        "- Questão 3: `HLLC_2a_ordem/01_pressao_dominios.png`",
        "- Questão 4: `HLLC_2a_ordem/02_mach_dominios.png`",
        "- Questão 5: `HLLC_2a_ordem/03_pressao_plot_over_line.png`",
        "",
        "Questões seguintes (um arquivo contendo as três figuras):",
    ]
    for case in CASES[1:]:
        lines.append(f"- {case.label}: `{case.directory}/ENTREGA_CASO.png`")
    lines.extend(
        [
            "",
            "Comentário final: use `RESPOSTA_COMENTARIO.md`.",
            "",
        ]
    )
    (RESULTS / "GUIA_UPLOAD.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean", action="store_true", help="apaga resultados anteriores")
    parser.add_argument("--force", action="store_true", help="refaz simulações e figuras")
    parser.add_argument("--prepare-only", action="store_true", help="só prepara e valida")
    parser.add_argument("--postprocess-only", action="store_true", help="só roda ParaView")
    parser.add_argument(
        "--ranks",
        type=int,
        default=max(1, min(4, os.cpu_count() or 1)),
        help="ranks MPI para cada simulação (padrão: até 4)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for required in (BASE_CONFIG, MESH, PARAVIEW_SCRIPT):
        if not required.exists():
            raise FileNotFoundError(required)
    if args.ranks < 1:
        raise ValueError("--ranks deve ser pelo menos 1")

    if not args.postprocess_only:
        prepare_cases(args.clean)
        for case in CASES:
            validate_case(case)
        if args.prepare_only:
            return 0
        for case in CASES:
            run_case(case, args.ranks, args.force)

    for case in CASES:
        postprocess_case(case, args.force)
    write_summary()
    write_upload_guide()
    print(f"\nConcluído. Resultados em: {RESULTS}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERRO: {error}", file=sys.stderr)
        raise
