#!/usr/bin/env python3
"""Generate coefficient and Cp comparison plots for the project form."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "resultados_formulario"
FIGURES = RESULTS / "figuras"
DATA = RESULTS / "dados_extraidos"
EXPERIMENTS = ROOT / "experimental_values"
FIGURES.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "legend.fontsize": 10,
        "figure.dpi": 140,
        "savefig.dpi": 240,
        "axes.grid": True,
        "grid.alpha": 0.25,
    }
)


def load_two_column(path: Path) -> tuple[np.ndarray, np.ndarray]:
    data = np.loadtxt(path, skiprows=2 if "CpCurves" in str(path) else 1)
    return data[:, 0], data[:, 1]


def load_coefficients() -> list[dict[str, str]]:
    with (RESULTS / "coeficientes_su2.csv").open() as stream:
        return list(csv.DictReader(stream))


def plot_lift_curve():
    rows = [row for row in load_coefficients() if float(row["Mach"]) == 0.3]
    aoa = np.array([float(row["AoA_deg"]) for row in rows])
    cl = np.array([float(row["CL"]) for row in rows])
    exp_aoa, exp_cl = load_two_column(
        EXPERIMENTS / "VsAlphaCurves" / "CLvsAlpha.txt"
    )

    fig, ax = plt.subplots(figsize=(8.5, 5.8))
    ax.plot(
        exp_aoa,
        exp_cl,
        "o-",
        color="#d97706",
        linewidth=1.8,
        markersize=5,
        label="Experimental",
    )
    ax.plot(
        aoa[:-1],
        cl[:-1],
        "s-",
        color="#2563eb",
        linewidth=2,
        markersize=5,
        label="SU2 — Euler, M = 0,3",
    )
    ax.plot(
        aoa[-1],
        cl[-1],
        marker="x",
        color="#dc2626",
        markersize=9,
        markeredgewidth=2,
        linestyle="none",
        label="SU2, 16° — não convergiu",
    )
    ax.set(
        title="Curva de sustentação do NACA 0012",
        xlabel="Ângulo de ataque, α (graus)",
        ylabel="Coeficiente de sustentação, $C_L$",
        xlim=(-0.5, 16.8),
    )
    ax.legend(frameon=False)
    fig.text(
        0.01,
        0.01,
        "Fontes: SU2 8.5.0 (malha fornecida) e dados experimentais do projeto.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIGURES / "04_CL_vs_AoA_com_experimento.png", bbox_inches="tight")
    plt.close(fig)

    interpolated = np.interp(aoa, exp_aoa, exp_cl)
    with (RESULTS / "comparacao_CL.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["AoA_deg", "CL_SU2", "CL_experimental_interpolado", "erro_percentual"]
        )
        for angle, computed, reference in zip(aoa, cl, interpolated):
            error = 100 * (computed - reference) / abs(reference) if abs(reference) > 0.01 else np.nan
            writer.writerow([angle, computed, reference, error])


def load_cp(case_name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    data = np.genfromtxt(
        DATA / f"{case_name}_cp.csv", delimiter=",", names=True
    )
    return data["x_over_c"], data["y_over_c"], data["Cp"]


def split_surface(
    x: np.ndarray, y: np.ndarray, cp: np.ndarray
) -> tuple[tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]:
    upper = y >= 0
    lower = y < 0
    upper_order = np.argsort(x[upper])
    lower_order = np.argsort(x[lower])
    return (
        (x[upper][upper_order], cp[upper][upper_order]),
        (x[lower][lower_order], cp[lower][lower_order]),
    )


def plot_cp_case(case_name: str, mach: float, aoa: float, output_name: str):
    x, y, cp = load_cp(case_name)
    (xu, cpu), (xl, cpl) = split_surface(x, y, cp)
    fig, ax = plt.subplots(figsize=(8.5, 5.8))
    ax.plot(xu, cpu, color="#2563eb", linewidth=2, label="SU2 — extradorso")
    ax.plot(xl, cpl, color="#0891b2", linewidth=2, label="SU2 — intradorso")
    ax.set(
        title=f"Distribuição de $C_p$ — M = {mach:g}; α = {aoa:g}°",
        xlabel="Posição ao longo da corda, x/c",
        ylabel="Coeficiente de pressão, $C_p$",
        xlim=(-0.02, 1.02),
    )
    ax.invert_yaxis()
    ax.legend(frameon=False)
    fig.text(
        0.01,
        0.01,
        "Fonte: SU2 8.5.0, solução de Euler na malha fornecida.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIGURES / output_name, bbox_inches="tight")
    plt.close(fig)


def plot_cp_comparison(case_name: str, angle: int):
    x, y, cp = load_cp(case_name)
    (xu, cpu), (xl, cpl) = split_surface(x, y, cp)
    exp_u_x, exp_u_cp = load_two_column(
        EXPERIMENTS / "CpCurves" / f"alpha_{angle}_upper.txt"
    )
    exp_l_x, exp_l_cp = load_two_column(
        EXPERIMENTS / "CpCurves" / f"alpha_{angle}_lower.txt"
    )

    fig, ax = plt.subplots(figsize=(8.5, 5.8))
    ax.plot(xu, cpu, color="#2563eb", linewidth=2, label="SU2 — extradorso")
    ax.plot(xl, cpl, color="#0891b2", linewidth=2, label="SU2 — intradorso")
    ax.scatter(
        exp_u_x,
        exp_u_cp,
        facecolors="none",
        edgecolors="#d97706",
        s=32,
        label="Experimental — extradorso",
        zorder=4,
    )
    ax.scatter(
        exp_l_x,
        exp_l_cp,
        marker="x",
        color="#7c3aed",
        s=32,
        label="Experimental — intradorso",
        zorder=4,
    )
    qualifier = " — caso não convergido" if angle == 16 else ""
    ax.set(
        title=f"Distribuição de $C_p$ — M = 0,3; α = {angle}°{qualifier}",
        xlabel="Posição ao longo da corda, x/c",
        ylabel="Coeficiente de pressão, $C_p$",
        xlim=(-0.02, 1.02),
    )
    ax.invert_yaxis()
    ax.legend(frameon=False, ncol=2)
    fig.text(
        0.01,
        0.01,
        "Fontes: SU2 8.5.0 e dados experimentais do projeto.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(
        FIGURES / f"06_Cp_M03_AoA_{angle:02d}_com_experimento.png",
        bbox_inches="tight",
    )
    plt.close(fig)


def main():
    plot_lift_curve()
    plot_cp_case(
        "M08_AoA_1p25",
        0.8,
        1.25,
        "03_Cp_M08_AoA_1p25.png",
    )
    for angle in (0, 8, 16):
        plot_cp_comparison(f"M03_AoA_{angle:02d}", angle)
    print(f"Comparison plots saved to {FIGURES}")


if __name__ == "__main__":
    main()
