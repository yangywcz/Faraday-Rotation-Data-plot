from __future__ import annotations

import os
import sys
import tkinter as tk
import warnings
from ctypes import windll
from tkinter import filedialog, messagebox, ttk

import matplotlib

warnings.filterwarnings(
    "ignore",
    category=SyntaxWarning,
    module=r"ttkbootstrap\.localization\.msgs",
)
import ttkbootstrap as tb

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

plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["lines.linewidth"] = 1.5
plt.rcParams["axes.grid"] = True
plt.rcParams["figure.facecolor"] = "#222222"
plt.rcParams["axes.facecolor"] = "#222222"
plt.rcParams["axes.edgecolor"] = "#aaaaaa"
plt.rcParams["axes.labelcolor"] = "#f0f0f0"
plt.rcParams["xtick.color"] = "#f0f0f0"
plt.rcParams["ytick.color"] = "#f0f0f0"
plt.rcParams["text.color"] = "#f0f0f0"
plt.rcParams["grid.color"] = "#555555"


def resource_path(filename):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)


def load_honor_font():
    font_dir = os.path.join("assets", "fonts")
    font_paths = (
        resource_path(os.path.join(font_dir, "HONORSansCN-Regular.ttf")),
        resource_path(os.path.join(font_dir, "HONORSansCN-Bold.ttf")),
    )
    loaded = False
    for font_path in font_paths:
        if os.path.exists(font_path):
            windll.gdi32.AddFontResourceExW(font_path, 0x10, 0)
            loaded = True
    return "HONOR Sans CN" if loaded else "Microsoft YaHei"


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
    data = pd.DataFrame(values, columns=[FIELD_COLUMN, CURRENT_COLUMN])
    for column in (FIELD_COLUMN, CURRENT_COLUMN):
        original = data[column]
        cleaned = original.map(
            lambda value: value.strip().replace(",", "") or None
            if isinstance(value, str)
            else value
        )
        normalized = pd.to_numeric(cleaned, errors="coerce")
        invalid = cleaned.notna() & normalized.isna()
        if invalid.any():
            excel_rows = ", ".join(str(index + 2) for index in data.index[invalid][:5])
            raise ValueError(
                "%s 列包含无法转换为数字的内容 (Excel 第 %s 行)"
                % (column, excel_rows)
            )
        data[column] = normalized
    return data.dropna(subset=[FIELD_COLUMN, CURRENT_COLUMN])


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("法拉第测试绘图")
        self.root.geometry("1000x820")
        self.data = None
        self.plot_data = None
        self._closing = False
        self._plot_job = None
        self._status_full_value = ""
        self._status_tooltip = None
        self.status = tk.StringVar(value="请选择 Excel 数据文件")
        self.status_value = tk.StringVar(value="")

        family = load_honor_font()
        self.font_family = family
        self.root.option_add("*Font", (family, 18))
        style = tb.Style(theme="darkly")
        interface_background = style.lookup("dark.TFrame", "background") or "#303030"
        self.interface_background = interface_background
        style.configure("Dark.TFrame", background=interface_background)
        style.configure(
            "Dark.TLabel", font=(family, 18), background=interface_background,
            foreground="#f0f0f0",
        )
        style.configure("Dark.TButton", font=(family, 18))
        style.configure("Dark.TSpinbox", font=(family, 18))
        style.configure("TButton", font=(family, 18))
        style.configure("TCheckbutton", font=(family, 18))
        style.configure("TEntry", font=(family, 18))
        style.configure("TSpinbox", font=(family, 18))
        style.configure("TScale", font=(family, 18))
        self.root.configure(background=interface_background)
        plt.rcParams["font.family"] = family
        plt.rcParams["font.sans-serif"] = [family, "Microsoft YaHei", "SimHei"]
        plt.rcParams["font.size"] = 18
        plt.rcParams["axes.labelsize"] = 18
        plt.rcParams["figure.facecolor"] = "#222222"
        plt.rcParams["axes.facecolor"] = "#222222"

        controls = ttk.Frame(root, padding=(10, 8), style="Dark.TFrame")
        controls.pack(fill="x")
        for column, weight in ((0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 1)):
            controls.grid_columnconfigure(column, weight=weight)
        controls.grid_columnconfigure(0, minsize=150)
        controls.grid_columnconfigure(1, minsize=145)
        controls.grid_columnconfigure(2, minsize=115)
        controls.grid_columnconfigure(3, minsize=150)
        controls.grid_columnconfigure(4, minsize=125)
        controls.grid_columnconfigure(5, minsize=135)

        ttk.Button(controls, text="打开 Excel", command=self.open_file, style="Dark.TButton").grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ttk.Label(controls, text="起始行", style="Dark.TLabel").grid(row=0, column=1, padx=(8, 2), sticky="e")
        self.start_var = tk.StringVar(value="0")
        self.start_spin = self._make_numeric_input(
            controls, self.start_var, 0, 100000, 1, 0, 6
        )
        self.start_spin.grid(row=0, column=2, sticky="ew")
        ttk.Label(controls, text="结束行", style="Dark.TLabel").grid(row=0, column=3, padx=(6, 2), sticky="e")
        self.end_var = tk.StringVar(value="30")
        self.end_spin = self._make_numeric_input(
            controls, self.end_var, 0, 100000, 1, 0, 6
        )
        self.end_spin.grid(row=0, column=4, sticky="ew")

        ttk.Label(controls, text="旋转角度(度)", style="Dark.TLabel").grid(row=1, column=0, padx=4, pady=4, sticky="e")
        self.angle_var = tk.StringVar(value="2.00")
        self.angle_spin = self._make_numeric_input(
            controls, self.angle_var, -90, 90, 0.01, 2, 8
        )
        self.angle_spin.grid(row=1, column=1, sticky="ew")
        ttk.Label(controls, text="膜厚(nm)", style="Dark.TLabel").grid(row=1, column=2, padx=4, sticky="e")
        self.thickness_var = tk.StringVar(value="100.00")
        self.thickness_spin = self._make_numeric_input(
            controls, self.thickness_var, 0.01, 1000000000, 0.01, 2, 8
        )
        self.thickness_spin.grid(row=1, column=3, sticky="ew")

        self.remove_slope_var = tk.BooleanVar(value=True)
        self._make_boolean_option(controls, "减斜率", self.remove_slope_var).grid(
            row=1, column=4, padx=4, sticky="w"
        )
        self.normalize_var = tk.BooleanVar(value=True)
        self._make_boolean_option(controls, "除以膜厚", self.normalize_var).grid(
            row=1, column=5, padx=4, sticky="w"
        )
        ttk.Label(controls, text="斜率倍率", style="Dark.TLabel").grid(row=2, column=0, padx=4, sticky="e")
        self.slope_factor_var = tk.DoubleVar(value=1.0)
        self.slope_scale = ttk.Scale(
            controls, from_=0.5, to=1.5, variable=self.slope_factor_var,
            command=lambda _value: self.plot(), length=220,
        )
        self.slope_scale.grid(row=2, column=1, columnspan=3, sticky="ew")
        self.slope_value = ttk.Label(controls, text="1.000x", style="Dark.TLabel")
        self.slope_value.grid(row=2, column=4, sticky="w")
        ttk.Button(controls, text="导出 CSV", command=self.export, style="Dark.TButton").grid(
            row=2, column=5, padx=6, sticky="ew"
        )

        for variable in (self.start_var, self.end_var, self.angle_var, self.thickness_var):
            variable.trace_add("write", lambda *_args: self._schedule_plot())
        self._bind_spinbox_wheel(self.start_spin, self.start_var, 1, 0, 100000, 0)
        self._bind_spinbox_wheel(self.end_spin, self.end_var, 1, 0, 100000, 0)
        self._bind_spinbox_wheel(self.angle_spin, self.angle_var, 0.01, -90, 90, 2)
        self._bind_spinbox_wheel(
            self.thickness_spin, self.thickness_var, 0.01, 0.01, 1000000000, 2
        )

        self.figure, self.axes = plt.subplots(figsize=(9, 5.5), dpi=100)
        self.figure.patch.set_facecolor("#222222")
        self.axes.set(
            xlabel="施加磁场 (Gs)",
            ylabel="法拉第旋角",
            xlim=(-5000, 5000),
            ylim=(-5000, 5000),
        )
        self.axes.set_facecolor("#222222")
        self.figure.subplots_adjust(right=0.97, top=0.97)
        self.figure.subplots_adjust(bottom=0.20)
        self._draw_zero_lines()
        self.status_bar = ttk.Frame(root, padding=(8, 4))
        self.status_bar.pack(side="bottom", fill="x")
        status_content = ttk.Frame(self.status_bar)
        status_content.pack(anchor="center")
        ttk.Label(status_content, textvariable=self.status).pack(side="left")
        self.status_value_label = ttk.Label(
            status_content,
            textvariable=self.status_value,
            foreground="#ffb74d",
            font=(family, 18, "bold"),
        )
        self.status_value_label.pack(side="left", padx=(8, 0))
        self.status_value_label.bind("<Button-1>", self._copy_status_value)
        self.status_value_label.bind("<Enter>", self._show_status_tooltip)
        self.status_value_label.bind("<Leave>", self._hide_status_tooltip)

        self.plot_area = ttk.Frame(root)
        self.plot_area.pack(fill="both", expand=True, padx=8)
        self.figure_canvas = FigureCanvasTkAgg(self.figure, master=self.plot_area)
        self.figure_canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        self.toolbar = NavigationToolbar2Tk(
            self.figure_canvas, self.plot_area, pack_toolbar=False
        )
        self.toolbar.configure(background="#222222")
        self.toolbar.update()
        self.toolbar.pack(side="bottom", fill="x")

    def _make_numeric_input(self, parent, variable, minimum, maximum, step, decimals, width):
        return ttk.Spinbox(
            parent,
            textvariable=variable,
            from_=minimum,
            to=maximum,
            increment=step,
            format="%%.%df" % decimals if decimals else "%d",
            width=width,
            font=(self.font_family, 18),
            style="Dark.TSpinbox",
        )

    def _make_boolean_option(self, parent, label, variable):
        background = self.interface_background
        option = tk.Frame(parent, background=background)
        indicator = tk.Canvas(
            option,
            width=30,
            height=30,
            background=background,
            highlightthickness=0,
        )
        indicator.pack(side="left", padx=(0, 5))
        indicator.create_rectangle(3, 3, 27, 27, fill="#ffffff", outline="#555555", width=2)
        text = ttk.Label(option, text=label, style="Dark.TLabel")
        text.pack(side="left")

        def refresh():
            indicator.delete("check")
            if variable.get():
                indicator.create_line(
                    8, 15, 13, 21, 23, 9,
                    fill="#1687c9",
                    width=3,
                    capstyle="round",
                    joinstyle="round",
                    tags="check",
                )

        def toggle(_event=None):
            variable.set(not variable.get())
            refresh()
            self.plot()

        for widget in (option, indicator, text):
            widget.bind("<Button-1>", toggle)
        refresh()
        return option

    def _schedule_plot(self):
        if self._closing:
            return
        if self._plot_job is not None:
            try:
                self.root.after_cancel(self._plot_job)
            except tk.TclError:
                pass
        self._plot_job = self.root.after(100, self._run_scheduled_plot)

    def _run_scheduled_plot(self):
        self._plot_job = None
        if not self._closing:
            self.plot()

    def _bind_spinbox_wheel(self, widget, variable, step, minimum, maximum, decimals):
        def on_wheel(event):
            try:
                current = float(variable.get())
            except (TypeError, ValueError):
                return "break"
            direction = 1 if event.delta > 0 else -1
            value = min(maximum, max(minimum, current + direction * step))
            variable.set(("%%.%df" % decimals) % value if decimals else str(int(value)))
            return "break"

        widget.bind("<MouseWheel>", on_wheel)

    def _set_status(self, message, full_value="", display_value=""):
        self.status.set(message)
        self.status_value.set(display_value)
        self._status_full_value = full_value

    def _copy_status_value(self, _event=None):
        if self._status_full_value:
            self.root.clipboard_clear()
            self.root.clipboard_append(self._status_full_value)

    def _show_status_tooltip(self, _event=None):
        if not self._status_full_value or self._status_tooltip is not None:
            return
        tooltip = tk.Toplevel(self.root)
        tooltip.overrideredirect(True)
        tk.Label(
            tooltip,
            text="左键复制完整精度数值",
            font=(self.font_family, 18),
            background="#fff8dc",
            foreground="#202020",
            padx=6,
            pady=3,
        ).pack()
        tooltip.update_idletasks()
        x = self.status_value_label.winfo_rootx()
        y = self.status_value_label.winfo_rooty() - tooltip.winfo_height() - 4
        tooltip.geometry("+%d+%d" % (x, y))
        self._status_tooltip = tooltip

    def _hide_status_tooltip(self, _event=None):
        if self._status_tooltip is not None:
            self._status_tooltip.destroy()
            self._status_tooltip = None

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
        self.root.title("法拉第测试绘图 - " + os.path.basename(path))
        self._set_status("读取成功: " + os.path.basename(path))
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
                if start == end:
                    raise ValueError("起始行数和结束行数必须不同")
                if min(start, end) < 0 or max(start, end) >= len(self.data):
                    raise ValueError("拟合区间无效，请检查起始行和结束行")
                if start not in data.index or end not in data.index:
                    raise ValueError("起始行或结束行没有有效数据")
                if curve_fit is None:
                    start_point = data.loc[start]
                    end_point = data.loc[end]
                    field_delta = end_point[FIELD_COLUMN] - start_point[FIELD_COLUMN]
                    if field_delta == 0:
                        raise ValueError("起始点和结束点的磁场值不能相同")
                    slope = (
                        end_point[CURRENT_COLUMN] - start_point[CURRENT_COLUMN]
                    ) / field_delta
                else:
                    selected = data.loc[min(start, end):max(start, end)]
                    slope = np.polyfit(
                        selected[FIELD_COLUMN], selected[CURRENT_COLUMN], 1
                    )[0]
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
                self._set_status(
                    "拟合法拉第测试结果: ",
                    full_value="%.17g" % fitted_result,
                    display_value="%.3f %s" % (fitted_result, unit),
                )
            elif self.remove_slope_var.get() and curve_fit is None:
                self._set_status("已按起止点斜率绘图；此版本不计算最终旋角")
        except (ValueError, TypeError, IndexError, RuntimeError, np.linalg.LinAlgError) as error:
            self._set_status(str(error))

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
            self._set_status("已导出: " + path)

    def close(self):
        if self._closing:
            return
        self._closing = True
        if self._plot_job is not None:
            try:
                self.root.after_cancel(self._plot_job)
            except tk.TclError:
                pass
            self._plot_job = None
        try:
            self.toolbar.destroy()
        except tk.TclError:
            pass
        try:
            self.figure_canvas.get_tk_widget().destroy()
        except tk.TclError:
            pass
        plt.close(self.figure)
        self.root.quit()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("法拉第测试绘图")
    icon = resource_path("logo.ico")
    if os.path.exists(icon):
        try:
            root.iconbitmap(icon)
        except tk.TclError:
            pass
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
