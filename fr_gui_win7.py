from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from python_calamine import CalamineWorkbook

try:
    from scipy.optimize import curve_fit
except ImportError:
    curve_fit = None

FIELD_COLUMN = "磁场(G)"
CURRENT_COLUMN = "电流(A)"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["lines.linewidth"] = 1.5
plt.rcParams["axes.grid"] = True


def resource_path(filename):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)


def fit_func(x, amplitude, rate, slope, offset):
    return amplitude * np.tanh(rate * x) - slope * x - offset


def read_measurement(path):
    workbook = CalamineWorkbook.from_path(path)
    rows = workbook.get_sheet_by_name(workbook.sheet_names[0]).to_python()
    if not rows:
        raise ValueError("文件中没有可用数据")

    headers = [str(value).strip() if value is not None else "" for value in rows[0]]
    try:
        field_index = headers.index(FIELD_COLUMN)
        current_index = headers.index(CURRENT_COLUMN)
    except ValueError as error:
        raise ValueError("Excel 中缺少磁场(G)或电流(A)列") from error

    values = [
        (row[field_index], row[current_index])
        for row in rows[1:]
        if len(row) > max(field_index, current_index)
    ]
    return pd.DataFrame(values, columns=[FIELD_COLUMN, CURRENT_COLUMN]).dropna()


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("法拉第测试绘图 (Windows 7)")
        self.root.geometry("1000x820")
        self.data = None
        self.plot_data = None
        self.status = tk.StringVar(value="请选择 Excel 数据文件")

        controls = ttk.Frame(root, padding=10)
        controls.pack(fill="x")

        ttk.Button(controls, text="打开 Excel", command=self.open_file).grid(row=0, column=0, padx=4, pady=4)
        ttk.Label(controls, text="起始行").grid(row=0, column=1, padx=(12, 2))
        self.start_var = tk.StringVar(value="0")
        ttk.Entry(controls, textvariable=self.start_var, width=8).grid(row=0, column=2)
        ttk.Label(controls, text="结束行").grid(row=0, column=3, padx=(8, 2))
        self.end_var = tk.StringVar(value="30")
        ttk.Entry(controls, textvariable=self.end_var, width=8).grid(row=0, column=4)

        ttk.Label(controls, text="旋转角度(度)").grid(row=1, column=0, padx=4, pady=4)
        self.angle_var = tk.StringVar(value="2.00")
        ttk.Entry(controls, textvariable=self.angle_var, width=10).grid(row=1, column=1)
        ttk.Label(controls, text="膜厚(nm)").grid(row=1, column=2, padx=4)
        self.thickness_var = tk.StringVar(value="100.00")
        ttk.Entry(controls, textvariable=self.thickness_var, width=10).grid(row=1, column=3)

        self.remove_slope_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="减斜率", variable=self.remove_slope_var, command=self.plot).grid(row=1, column=4)
        self.normalize_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="除以膜厚", variable=self.normalize_var, command=self.plot).grid(row=1, column=5)
        ttk.Label(controls, text="斜率倍率").grid(row=2, column=0, padx=4)
        self.slope_factor_var = tk.DoubleVar(value=1.0)
        self.slope_scale = ttk.Scale(
            controls, from_=0.5, to=1.5, variable=self.slope_factor_var,
            command=lambda _value: self.plot(), length=220,
        )
        self.slope_scale.grid(row=2, column=1, columnspan=3, sticky="w")
        self.slope_value = ttk.Label(controls, text="1.000x")
        self.slope_value.grid(row=2, column=4, sticky="w")

        for variable in (self.start_var, self.end_var, self.angle_var, self.thickness_var):
            variable.trace_add("write", lambda *_args: self.root.after_idle(self.plot))

        self.figure, self.axes = plt.subplots(figsize=(9, 5.5), dpi=100)
        self.axes.set(xlabel="施加磁场 (Gs)", ylabel="法拉第旋角", xlim=(-5000, 5000))
        self._draw_zero_lines()
        self.figure_canvas = FigureCanvasTkAgg(self.figure, master=root)
        self.figure_canvas.get_tk_widget().pack(fill="both", expand=True, padx=8)
        self.toolbar = NavigationToolbar2Tk(self.figure_canvas, root)
        self.toolbar.update()
        ttk.Label(root, textvariable=self.status, anchor="w", padding=(8, 4)).pack(fill="x")

    def _draw_zero_lines(self):
        self.axes.axhline(0, color="#c62828", linewidth=1.2)
        self.axes.axvline(0, color="#c62828", linewidth=1.2)

    def open_file(self):
        path = filedialog.askopenfilename(
            title="选择 Excel 文件",
            filetypes=[("Excel 文件", "*.xls *.xlsx"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            self.data = read_measurement(path)
            if self.data.empty:
                raise ValueError("文件中没有可用数据")
        except Exception as error:
            self.data = None
            messagebox.showerror("读取失败", str(error))
            self.status.set("文件读取失败")
            return
        self.root.title("法拉第测试绘图 (Windows 7) - " + os.path.basename(path))
        self.status.set("读取成功: " + os.path.basename(path))
        self.plot()

    def plot(self):
        if self.data is None or not hasattr(self, "figure_canvas"):
            return
        try:
            angle = float(self.angle_var.get())
            thickness = float(self.thickness_var.get())
            if thickness <= 0:
                raise ValueError("膜厚必须大于 0")
            start = int(self.start_var.get())
            end = int(self.end_var.get())
            current = self.data[CURRENT_COLUMN]
            median = current.median()
            with np.errstate(invalid="ignore", divide="ignore"):
                rotation = angle - np.rad2deg(
                    np.arcsin(np.sqrt(current / median) * np.sin(np.deg2rad(angle)))
                )
            data = pd.DataFrame({FIELD_COLUMN: self.data[FIELD_COLUMN], CURRENT_COLUMN: rotation}).dropna()
            fitted_result = None
            if self.remove_slope_var.get():
                if start == end or min(start, end) < 0 or max(start, end) >= len(data):
                    raise ValueError("拟合区间无效，请检查起始行和结束行")
                selected = data.loc[min(start, end):max(start, end)]
                slope = np.polyfit(selected[FIELD_COLUMN], selected[CURRENT_COLUMN], 1)[0]
                slope *= float(self.slope_factor_var.get())
                data[CURRENT_COLUMN] -= slope * data[FIELD_COLUMN]
                values = data[CURRENT_COLUMN]
                if curve_fit is not None:
                    params, _ = curve_fit(
                        fit_func,
                        data[FIELD_COLUMN],
                        values,
                        p0=(values.max(), 0.002, 0, (values.max() + values.min()) / 2),
                        method="trf",
                    )
                    data[CURRENT_COLUMN] += params[-1]
                    fitted_result = float(
                        fit_func(data[FIELD_COLUMN].values, *params).max() + params[-1]
                    )
                    fitted_result /= thickness if self.normalize_var.get() else 1.0
                    fitted_result *= 1e7 if self.normalize_var.get() else 1.0
            if self.normalize_var.get():
                data[CURRENT_COLUMN] /= thickness * 1e-7
            self.plot_data = data
            self.axes.clear()
            self.axes.plot(data[FIELD_COLUMN], data[CURRENT_COLUMN])
            self.axes.set(xlabel="施加磁场 (Gs)", ylabel="法拉第旋角 (deg/cm)" if self.normalize_var.get() else "法拉第旋角 (deg)")
            self._draw_zero_lines()
            self.figure_canvas.draw_idle()
            factor = float(self.slope_factor_var.get())
            self.slope_value.configure(text="%.3fx" % factor)
            if fitted_result is not None:
                unit = "deg/cm" if self.normalize_var.get() else "deg"
                self.status.set("拟合法拉第测试结果: %.3f %s" % (fitted_result, unit))
            elif self.remove_slope_var.get() and curve_fit is None:
                self.status.set("数据已绘制；Win7 32 位版不包含非线性拟合")
        except (ValueError, TypeError, IndexError, RuntimeError, np.linalg.LinAlgError) as error:
            self.status.set(str(error))

    def export(self):
        if self.plot_data is None:
            messagebox.showerror("导出失败", "请先读取数据")
            return
        path = filedialog.asksaveasfilename(
            title="导出 CSV", defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv")],
        )
        if path:
            self.plot_data.to_csv(path, index=False, encoding="utf-8-sig")
            self.status.set("已导出: " + path)


if __name__ == "__main__":
    root = tk.Tk()
    icon = resource_path("logo.ico")
    if os.path.exists(icon):
        try:
            root.iconbitmap(icon)
        except tk.TclError:
            pass
    app = App(root)
    ttk.Button(root, text="导出 CSV", command=app.export).pack(anchor="e", padx=12, pady=6)
    root.mainloop()
