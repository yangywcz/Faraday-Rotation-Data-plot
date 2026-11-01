from __future__ import annotations

from dataclasses import dataclass
from os import PathLike
from typing import TypeAlias

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

FIELD_COLUMN = "磁场(G)"
CURRENT_COLUMN = "电流(A)"
REQUIRED_COLUMNS = (FIELD_COLUMN, CURRENT_COLUMN)
Path: TypeAlias = str | PathLike[str]


@dataclass(frozen=True)
class ProcessingResult:
    data: pd.DataFrame
    slope: float | None
    fitted_rotation: float | None
    unit: str


def read_measurement(file_path: Path) -> pd.DataFrame:
    """Read and validate the columns used by the application."""
    data = pd.read_excel(file_path, usecols=list(REQUIRED_COLUMNS))
    if data.empty:
        raise ValueError("文件中没有可用数据")
    return data


def describe_measurement(data: pd.DataFrame) -> tuple[str, int]:
    """Return the magnetic-field direction and its extreme-value row."""
    if data.iloc[0][FIELD_COLUMN] >= 0:
        return "正⇨负⇨正,负磁场最大值", int(data[FIELD_COLUMN].idxmin())
    return "负⇨正⇨负,正磁场最大值", int(data[FIELD_COLUMN].idxmax())


def calculate_rotation(data: pd.DataFrame, angle: float) -> pd.DataFrame:
    """Convert measured current to Faraday rotation in degrees."""
    result = data.copy()
    median_current = result[CURRENT_COLUMN].median()
    with np.errstate(invalid="ignore", divide="ignore"):
        result[CURRENT_COLUMN] = angle - np.rad2deg(
            np.arcsin(
                np.sqrt(result[CURRENT_COLUMN] / median_current)
                * np.sin(np.deg2rad(angle))
            )
        )
    return result.dropna(axis=0)


def estimate_baseline_slope(
    data: pd.DataFrame, start_row: int, end_row: int
) -> float:
    """Estimate the linear background slope over an inclusive row range."""
    if start_row == end_row:
        raise ValueError("起始行数和结束行数必须不同")
    if min(start_row, end_row) < 0 or max(start_row, end_row) >= len(data.index):
        raise ValueError(f"超出索引(文件最大行数为{len(data.index) - 1})")

    selected = data.loc[
        min(start_row, end_row) : max(start_row, end_row),
        [FIELD_COLUMN, CURRENT_COLUMN],
    ]
    try:
        slope, _ = np.polyfit(
            selected[FIELD_COLUMN], selected[CURRENT_COLUMN], 1
        )
    except (TypeError, ValueError, np.linalg.LinAlgError) as error:
        raise ValueError("所选区间无法线性拟合，请选择合适区间") from error
    return float(slope)


def apply_baseline(data: pd.DataFrame, slope: float) -> pd.DataFrame:
    result = data.copy()
    result[CURRENT_COLUMN] -= slope * result[FIELD_COLUMN]
    return result


def fit_func(x: np.ndarray, amplitude: float, rate: float, slope: float, offset: float):
    return amplitude * np.tanh(rate * x) - slope * x - offset


def fit_rotation(data: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """Fit the rotation curve and return the shifted data and its peak value."""
    current = data[CURRENT_COLUMN]
    initial = (
        current.max(),
        0.002,
        0,
        (current.max() + current.min()) / 2,
    )
    try:
        parameters, _ = curve_fit(
            fit_func,
            data[FIELD_COLUMN],
            current,
            p0=initial,
            method="trf",
        )
    except (RuntimeError, TypeError, ValueError) as error:
        raise ValueError("未能成功拟合测试数据") from error

    result = data.copy()
    offset = float(parameters[-1])
    result[CURRENT_COLUMN] += offset
    fitted_peak = float((fit_func(data[FIELD_COLUMN].to_numpy(), *parameters).max() + offset))
    return result, fitted_peak


def process_measurement(
    data: pd.DataFrame,
    angle: float,
    thickness: float,
    normalize_thickness: bool,
    remove_baseline: bool,
    manual_slope_factor: float | None = None,
    baseline_start: int = 0,
    baseline_end: int = 30,
) -> ProcessingResult:
    """Apply the selected transformations and return plot-ready data."""
    if thickness <= 0:
        raise ValueError("膜厚必须大于 0")

    result = calculate_rotation(data, angle)
    slope = None
    if remove_baseline:
        slope = estimate_baseline_slope(result, baseline_start, baseline_end)
        if manual_slope_factor is not None:
            if not 0.5 <= manual_slope_factor <= 1.5:
                raise ValueError("手动斜率倍率必须在 0.5 到 1.5 之间")
            slope *= manual_slope_factor
        result = apply_baseline(result, slope)

    fitted_rotation = None
    if remove_baseline:
        result, fitted_rotation = fit_rotation(result)

    scale = thickness if normalize_thickness else 1e7
    result = result.copy()
    result[CURRENT_COLUMN] /= scale * 1e-7
    return ProcessingResult(
        data=result,
        slope=slope,
        fitted_rotation=(fitted_rotation / scale * 1e7 if fitted_rotation is not None else None),
        unit="deg/cm" if normalize_thickness else "deg",
    )