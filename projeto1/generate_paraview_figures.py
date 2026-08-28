#!/usr/bin/env pvpython
"""Create the mesh and pressure-contour figures required by the form."""

from __future__ import annotations

import csv
from pathlib import Path

from paraview import servermanager
from paraview.simple import (
    ColorBy,
    CreateView,
    Delete,
    GetColorTransferFunction,
    GetScalarBar,
    Hide,
    Render,
    SaveScreenshot,
    Show,
    Text,
    XMLUnstructuredGridReader,
)


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "resultados_formulario"
CASES = RESULTS / "casos"
FIGURES = RESULTS / "figuras"
DATA = RESULTS / "dados_extraidos"
FIGURES.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)


def make_view():
    view = CreateView("RenderView")
    view.ViewSize = [1600, 1000]
    view.InteractionMode = "2D"
    view.OrientationAxesVisibility = 0
    view.Background = [1.0, 1.0, 1.0]
    view.CameraPosition = [0.5, 0.0, 5.0]
    view.CameraFocalPoint = [0.5, 0.0, 0.0]
    view.CameraViewUp = [0.0, 1.0, 0.0]
    view.CameraParallelProjection = 1
    view.CameraParallelScale = 0.42
    return view


def add_title(view, title: str):
    text = Text(Text=title)
    display = Show(text, view)
    display.WindowLocation = "Upper Center"
    display.FontSize = 18
    display.Color = [0.08, 0.08, 0.08]
    return text


def render_mesh():
    reader = XMLUnstructuredGridReader(
        FileName=[str(CASES / "M08_AoA_1p25" / "flow.vtu")]
    )
    reader.UpdatePipeline()
    view = make_view()
    display = Show(reader, view)
    display.Representation = "Surface With Edges"
    display.AmbientColor = [0.92, 0.92, 0.92]
    display.DiffuseColor = [0.92, 0.92, 0.92]
    display.EdgeColor = [0.08, 0.08, 0.08]
    display.LineWidth = 0.7
    title = add_title(view, "Malha próxima ao NACA 0012")
    Render(view)
    view.CameraPosition = [0.5, 0.0, 5.0]
    view.CameraFocalPoint = [0.5, 0.0, 0.0]
    view.CameraViewUp = [0.0, 1.0, 0.0]
    view.CameraParallelScale = 0.35
    Render(view)
    SaveScreenshot(
        str(FIGURES / "01_malha_proxima_aerofolio.png"),
        view,
        ImageResolution=[1600, 1000],
    )
    Delete(title)
    Delete(reader)
    Delete(view)


def pressure_range(case_names: list[str]) -> tuple[float, float]:
    limits = []
    for name in case_names:
        reader = XMLUnstructuredGridReader(
            FileName=[str(CASES / name / "flow.vtu")]
        )
        reader.UpdatePipeline()
        limits.append(reader.PointData["Pressure"].GetRange())
        Delete(reader)
    return min(item[0] for item in limits), max(item[1] for item in limits)


def render_pressure(
    case_name: str,
    title_text: str,
    output_name: str,
    limits: tuple[float, float],
):
    reader = XMLUnstructuredGridReader(
        FileName=[str(CASES / case_name / "flow.vtu")]
    )
    reader.UpdatePipeline()
    view = make_view()
    display = Show(reader, view)
    ColorBy(display, ("POINTS", "Pressure"))
    lut = GetColorTransferFunction("Pressure")
    lut.RescaleTransferFunction(*limits)
    lut.ApplyPreset("Cool to Warm", True)
    display.SetScalarBarVisibility(view, True)
    scalar_bar = GetScalarBar(lut, view)
    scalar_bar.Title = "Pressão"
    scalar_bar.ComponentTitle = "Pa"
    scalar_bar.TitleFontSize = 16
    scalar_bar.LabelFontSize = 13
    title = add_title(view, title_text)
    Render(view)
    SaveScreenshot(
        str(FIGURES / output_name),
        view,
        ImageResolution=[1600, 1000],
    )
    Hide(reader, view)
    Delete(title)
    Delete(reader)
    Delete(view)


def extract_cp(case_name: str):
    reader = XMLUnstructuredGridReader(
        FileName=[str(CASES / case_name / "surface_flow.vtu")]
    )
    reader.UpdatePipeline()
    dataset = servermanager.Fetch(reader)
    points = dataset.GetPoints()
    cp = dataset.GetPointData().GetArray("Pressure_Coefficient")
    if points is None or cp is None:
        raise RuntimeError(f"Missing coordinates or Cp in {case_name}")
    with (DATA / f"{case_name}_cp.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["x_over_c", "y_over_c", "Cp"])
        for index in range(points.GetNumberOfPoints()):
            x, y, _ = points.GetPoint(index)
            writer.writerow([x, y, cp.GetTuple1(index)])
    Delete(reader)


def main():
    render_mesh()

    m08_limits = pressure_range(["M08_AoA_1p25"])
    render_pressure(
        "M08_AoA_1p25",
        "Pressão — M = 0,8; α = 1,25°",
        "02_pressao_M08_AoA_1p25.png",
        m08_limits,
    )

    low_speed_cases = ["M03_AoA_00", "M03_AoA_08", "M03_AoA_16"]
    low_speed_limits = pressure_range(low_speed_cases)
    for angle, case_name in [(0, low_speed_cases[0]), (8, low_speed_cases[1]), (16, low_speed_cases[2])]:
        qualifier = " — não convergiu" if angle == 16 else ""
        render_pressure(
            case_name,
            f"Pressão — M = 0,3; α = {angle}°{qualifier}",
            f"05_pressao_M03_AoA_{angle:02d}.png",
            low_speed_limits,
        )

    for case_name in ["M08_AoA_1p25", *low_speed_cases]:
        extract_cp(case_name)

    print(f"ParaView figures saved to {FIGURES}")


if __name__ == "__main__":
    main()
