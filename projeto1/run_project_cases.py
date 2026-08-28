#!/usr/bin/env python3
"""Run all SU2 cases required by the NACA 0012 project form."""

from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASE_CONFIG = ROOT / "inv_NACA0012.cfg"
MESH = ROOT / "mesh_NACA0012_inv.su2"
RESULTS = ROOT / "resultados_formulario"
SU2_CFD = Path.home() / "opt" / "su2" / "bin" / "SU2_CFD"
MPI_RANKS = 4

CASES = [
    ("M08_AoA_1p25", 0.8, 1.25),
    *[(f"M03_AoA_{alpha:02d}", 0.3, float(alpha)) for alpha in range(0, 18, 2)],
]


def replace_setting(text: str, key: str, value: str) -> str:
    pattern = rf"(?m)^\s*{re.escape(key)}\s*=.*$"
    replacement = f"{key}= {value}"
    updated, count = re.subn(pattern, replacement, text)
    if count != 1:
        raise RuntimeError(f"Expected one {key} setting, found {count}")
    return updated


def prepare_case(name: str, mach: float, aoa: float) -> Path:
    case_dir = RESULTS / "casos" / name
    case_dir.mkdir(parents=True, exist_ok=True)
    config = BASE_CONFIG.read_text()
    config = replace_setting(config, "MACH_NUMBER", f"{mach:g}")
    config = replace_setting(config, "AOA", f"{aoa:g}")
    config = replace_setting(
        config,
        "OUTPUT_FILES",
        "(RESTART, PARAVIEW, SURFACE_PARAVIEW, SURFACE_CSV)",
    )
    config = replace_setting(config, "OUTPUT_WRT_FREQ", "10, 250, 250, 250")
    (case_dir / "case.cfg").write_text(config)
    shutil.copy2(MESH, case_dir / MESH.name)
    return case_dir


def parse_forces(path: Path) -> dict[str, float]:
    text = path.read_text(errors="replace")
    patterns = {
        "CL": r"Total CL:\s*([-+0-9.eE]+)",
        "CD": r"Total CD:\s*([-+0-9.eE]+)",
        "CL_CD": r"Total CL/CD:\s*([-+0-9.eE]+)",
        "CMz": r"Total CMz:\s*([-+0-9.eE]+)",
    }
    values: dict[str, float] = {}
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text)
        if not matches:
            raise RuntimeError(f"Could not find {key} in {path}")
        values[key] = float(matches[-1])
    return values


def run_case(name: str, mach: float, aoa: float) -> dict[str, object]:
    case_dir = prepare_case(name, mach, aoa)
    required = [
        case_dir / "forces_breakdown.dat",
        case_dir / "flow.vtu",
        case_dir / "surface_flow.vtu",
        case_dir / "surface_flow.csv",
    ]
    if not all(path.exists() for path in required):
        print(f"Running {name}: Mach={mach:g}, AoA={aoa:g} deg", flush=True)
        env = os.environ.copy()
        env.pop("OMPI_MCA_btl", None)
        command = [
            "mpirun",
            "-np",
            str(MPI_RANKS),
            str(SU2_CFD),
            "case.cfg",
        ]
        with (case_dir / "run.log").open("w") as log:
            subprocess.run(
                command,
                cwd=case_dir,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
    values = parse_forces(case_dir / "forces_breakdown.dat")
    return {"case": name, "Mach": mach, "AoA_deg": aoa, **values}


def main() -> None:
    if not BASE_CONFIG.exists() or not MESH.exists():
        raise SystemExit("Base configuration or mesh is missing.")
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = [run_case(*case) for case in CASES]
    summary = RESULTS / "coeficientes_su2.csv"
    with summary.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Completed {len(rows)} cases. Summary: {summary}")


if __name__ == "__main__":
    main()
