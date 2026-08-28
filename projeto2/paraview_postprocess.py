#!/usr/bin/env pvpython
"""Gera as três figuras do formulário usando filtros e vistas do ParaView."""

from __future__ import annotations

import argparse
from pathlib import Path

from paraview.simple import (  # type: ignore[import-not-found]
    AssignViewToLayout,
    ColorBy,
    CreateLayout,
    CreateView,
    GetColorTransferFunction,
    GetScalarBar,
    PlotOverLine,
    ResetSession,
    SaveData,
    SaveScreenshot,
    Show,
    Text,
    XMLUnstructuredGridReader,
    _DisableFirstRenderCameraReset,
)


_DisableFirstRenderCameraReset()


def set_2d_camera(view, xlim: tuple[float, float], ylim: tuple[float, float]) -> None:
    center_x = sum(xlim) / 2.0
    center_y = sum(ylim) / 2.0
    view.InteractionMode = "2D"
    view.CameraParallelProjection = 1
    view.CameraPosition = [center_x, center_y, 10.0]
    view.CameraFocalPoint = [center_x, center_y, 0.0]
    view.CameraViewUp = [0.0, 1.0, 0.0]
    # Cada painel tem aspecto próximo de 1:1.
    view.CameraParallelScale = 0.50 * max(xlim[1] - xlim[0], ylim[1] - ylim[0])


def add_field_to_view(reader, view, field: str, title: str, rescale: bool = True):
    display = Show(reader, view)
    display.Representation = "Surface"
    ColorBy(display, ("POINTS", field))
    lookup = GetColorTransferFunction(field)
    if rescale:
        display.RescaleTransferFunctionToDataRange(True, False)
    display.SetScalarBarVisibility(view, True)
    scalar_bar = GetScalarBar(lookup, view)
    scalar_bar.Title = title
    scalar_bar.ComponentTitle = ""
    scalar_bar.WindowLocation = "Any Location"
    scalar_bar.Position = [0.84, 0.55]
    scalar_bar.ScalarBarLength = 0.34
    scalar_bar.ScalarBarThickness = 18
    scalar_bar.TitleFontSize = 18
    scalar_bar.LabelFontSize = 15
    view.Background = [1.0, 1.0, 1.0]
    view.UseColorPaletteForBackground = 0
    view.OrientationAxesVisibility = 1
    return display


def add_annotation(view, text: str) -> None:
    annotation = Text(Text=text)
    display = Show(annotation, view)
    display.WindowLocation = "Upper Left Corner"
    display.FontSize = 18
    display.Color = [0.0, 0.0, 0.0]
    display.BackgroundColor = [1.0, 1.0, 1.0, 0.82]
    display.ShowBorder = 1
    display.BorderColor = [0.0, 0.0, 0.0]
    display.BorderThickness = 1
    display.Padding = 5
    display.Bold = 1


def render_two_views(
    input_path: Path,
    output_path: Path,
    field: str,
    scalar_title: str,
    case_title: str,
) -> None:
    ResetSession()
    reader = XMLUnstructuredGridReader(FileName=[str(input_path)])
    reader.UpdatePipeline()

    layout = CreateLayout(name=f"{field} — domínio e cunha")
    layout.SplitHorizontal(0, 0.5)
    full_view = CreateView("RenderView")
    near_view = CreateView("RenderView")
    AssignViewToLayout(view=full_view, layout=layout, hint=0)
    AssignViewToLayout(view=near_view, layout=layout, hint=2)

    add_field_to_view(reader, full_view, field, scalar_title, rescale=True)
    add_field_to_view(reader, near_view, field, scalar_title, rescale=False)
    add_annotation(full_view, f"{case_title}\nDomínio completo")
    add_annotation(near_view, f"{case_title}\nDetalhe no canto da cunha")
    set_2d_camera(full_view, (0.0, 1.5), (0.0, 1.0))
    # Vértice da cunha em x = 0,5 m. Esta janela é ~5× menor que o domínio.
    set_2d_camera(near_view, (0.45, 0.72), (0.00, 0.20))

    layout.SetSize(1800, 900)
    SaveScreenshot(
        str(output_path),
        layout,
        ImageResolution=[1800, 900],
        FontScaling="Scale fonts proportionally",
    )


def render_plot_over_line(
    input_path: Path,
    image_path: Path,
    csv_path: Path,
    title: str,
) -> None:
    ResetSession()
    reader = XMLUnstructuredGridReader(FileName=[str(input_path)])
    reader.UpdatePipeline()

    line = PlotOverLine(Input=reader)
    line.Point1 = [0.0, 0.5, 0.0]
    line.Point2 = [1.5, 0.5, 0.0]
    line.Resolution = 600
    line.UpdatePipeline()
    SaveData(str(csv_path), proxy=line)

    chart = CreateView("XYChartView")
    layout = CreateLayout(name="Plot Over Line")
    AssignViewToLayout(view=chart, layout=layout, hint=0)
    display = Show(line, chart)
    display.UseIndexForXAxis = 0
    display.XArrayName = "arc_length"
    display.SeriesVisibility = ["Pressure"]
    display.SeriesLabel = ["Pressure", "Pressão SU2"]
    display.SeriesColor = ["Pressure", "0.12", "0.35", "0.85"]
    display.SeriesLineThickness = ["Pressure", "3"]

    chart.ChartTitle = f"{title}\nPressão ao longo de (0; 0,5; 0) → (1,5; 0,5; 0)"
    chart.LeftAxisTitle = "Pressão estática [Pa]"
    chart.BottomAxisTitle = "x [m]"
    chart.ShowLegend = 1
    chart.LegendLocation = "TopLeft"
    layout.SetSize(1800, 900)
    SaveScreenshot(
        str(image_path),
        layout,
        ImageResolution=[1800, 900],
        FontScaling="Scale fonts proportionally",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--title", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    render_two_views(
        args.input,
        args.output_dir / "01_pressao_dominios.png",
        "Pressure",
        "Pressão [Pa]",
        args.title,
    )
    render_two_views(
        args.input,
        args.output_dir / "02_mach_dominios.png",
        "Mach",
        "Número de Mach",
        args.title,
    )
    render_plot_over_line(
        args.input,
        args.output_dir / "03_pressao_plot_over_line.png",
        args.output_dir / "pressao_linha_y_0p5.csv",
        args.title,
    )


if __name__ == "__main__":
    main()
