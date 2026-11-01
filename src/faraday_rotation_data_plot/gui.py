from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox

import matplotlib.pyplot as plt
import maliang
from maliang import Font, mpl, theme

from faraday_rotation_data_plot.processing import (
    CURRENT_COLUMN,
    FIELD_COLUMN,
    describe_measurement,
    process_measurement,
    read_measurement,
)
from faraday_rotation_data_plot.resources import HONOR_SANS_CN, load_fonts

load_fonts()
Font.family = HONOR_SANS_CN
Font.size = -22
mpl.set_mpl_default_theme(theme.get_color_mode())
COLOR_MODE = theme.get_color_mode()
ZERO_LINE_COLOR = "#c62828" if COLOR_MODE == "light" else "#ffb74d"

plt.rcParams["font.sans-serif"] = [HONOR_SANS_CN]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["lines.linewidth"] = 1.5
plt.rcParams["mathtext.fontset"] = "stix"
plt.rcParams["axes.titlesize"] = "larger"
plt.rcParams["axes.labelsize"] = "larger"
plt.rcParams["xtick.minor.visible"] = True
plt.rcParams["ytick.minor.visible"] = True
plt.rcParams["xtick.direction"] = "in"
plt.rcParams["ytick.direction"] = "in"
plt.rcParams["axes.grid"] = True


class ChineseFigureToolbar(mpl.FigureToolbar):
    toolitems = (
        ("主页", "恢复初始视图", "home", "home"),
        ("后退", "返回上一个视图", "back", "back"),
        ("前进", "前进到下一个视图", "forward", "forward"),
        (None, None, None, None),
        ("平移", "左键平移，右键缩放", "move", "pan"),
        ("缩放", "框选区域进行缩放", "zoom_to_rect", "zoom"),
        ("子图", "配置子图布局", "subplots", "configure_subplots"),
        (None, None, None, None),
        ("保存", "保存图像", "filesave", "save_figure"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_font(self)

    def _apply_font(self, widget: tk.Misc) -> None:
        try:
            widget.configure(font=(HONOR_SANS_CN, 10))
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._apply_font(child)

    def set_message(self, message: str) -> None:
        translations = {
            "Back to previous view": "返回上一个视图",
            "Forward to next view": "前进到下一个视图",
            "Home": "恢复初始视图",
            "Pan": "平移",
            "Zoom": "缩放",
            "Configure subplots": "配置子图布局",
            "Save the figure": "保存图像",
        }
        super().set_message(translations.get(message, message))


class Application:
    def __init__(self, master):
        self.master = master
        self.canvas = maliang.Canvas(auto_zoom=True, auto_update=True)
        self.canvas.place(width=960, height=830)
        self.canvas_mpl = maliang.Canvas(auto_zoom=True, auto_update=True)
        self.canvas_mpl.place(width=960, height=500, y=300)
        self.file_name = None
        self.data = None
        self._plot_job = None
        self._status_full_value = ""
        self._status_tooltip = None

        maliang.Text(self.canvas, (10, 16), text="文件路径", anchor="nw")
        self.path_var = maliang.InputBox(
            self.canvas, (120, 10), (700, 40), anchor="nw", placeholder="浏览文件"
        )
        self.browse_button = maliang.Button(
            self.canvas, (950, 10), (100, 40), text="浏览", anchor="ne", command=self.selectPath
        )
        self.label_text = maliang.Text(
            self.canvas, (10, 80), anchor="nw", text="求斜率:采用线性拟合的斜率"
        )
        maliang.Text(self.canvas, (10, 136), text="起始行数", anchor="nw")
        self.start_box = maliang.SpinBox(
            self.canvas, (120, 130), (120, 40), default="0", command=self._on_parameter_changed
        )
        maliang.Text(self.canvas, (280, 136), text="结束行数", anchor="nw")
        self.end_box = maliang.SpinBox(
            self.canvas, (380, 130), (120, 40), default="30", command=self._on_parameter_changed
        )
        self.manual_slope_label = maliang.Text(
            self.canvas, (520, 136), text="手动设置斜率", anchor="nw"
        )
        self.slope_slider = maliang.Slider(
            self.canvas,
            (680, 135),
            (200, 30),
            default=0.5,
            command=self._on_slope_slider_changed,
        )
        self.slope_factor_label = maliang.Text(
            self.canvas, (950, 150), text="1.000x", fontsize=18, anchor="e"
        )
        maliang.Text(self.canvas, (10, 186), text="旋转角度", anchor="nw")
        self.deg_box = maliang.SpinBox(
            self.canvas,
            (120, 180),
            (120, 40),
            format_spec=".2f",
            step=0.01,
            default="2.00",
            command=self._on_parameter_changed,
        )
        maliang.Text(self.canvas, (250, 186), text="度", anchor="nw")
        maliang.Text(self.canvas, (10, 246), text="膜厚", anchor="nw")
        self.thin_box = maliang.SpinBox(
            self.canvas,
            (120, 240),
            (120, 40),
            format_spec=".2f",
            step=0.01,
            default="100.00",
            command=self._on_parameter_changed,
        )
        maliang.Text(self.canvas, (250, 246), text="nm", anchor="nw")
        self.k_switch = maliang.Switch(
            self.canvas, (300, 246), default=True, command=self._on_baseline_switch
        )
        maliang.Text(self.canvas, (370, 246), text="减斜率", anchor="nw")
        self.thin_switch = maliang.Switch(
            self.canvas, (450, 246), default=True, command=self._on_parameter_changed
        )
        maliang.Text(self.canvas, (530, 246), text="除以膜厚", anchor="nw")
        self.export_button = maliang.Button(
            self.canvas, (950, 240), (140, 40), text="导出", anchor="ne", command=self.export
        )
        status_background = "#303030" if COLOR_MODE == "dark" else "#f0f0f0"
        status_foreground = "#f0f0f0" if COLOR_MODE == "dark" else "#202020"
        status_highlight = "#ffb74d" if COLOR_MODE == "dark" else "#b71c1c"
        self.statusbar = tk.Frame(self.master, background=status_background)
        self.statusbar.place(x=0, y=800, width=960, height=30)
        self.status_content = tk.Frame(self.statusbar, background=status_background)
        self.status_content.place(relx=0.5, rely=0.5, anchor="center")
        self.status_message = tk.Label(
            self.status_content,
            text="准备就绪",
            font=(HONOR_SANS_CN, 16),
            foreground=status_foreground,
            background=status_background,
            anchor="w",
        )
        self.status_message.pack(side="left")
        self.status_value = tk.Label(
            self.status_content,
            text="",
            font=(HONOR_SANS_CN, 16, "bold"),
            foreground=status_highlight,
            background=status_background,
            anchor="w",
        )
        self.status_value.pack(side="left", padx=(6, 0))
        self.status_value.bind("<Button-1>", self._copy_status_value)
        self.status_value.bind("<Enter>", self._show_status_tooltip)
        self.status_value.bind("<Leave>", self._hide_status_tooltip)

        self.figure = plt.Figure()
        self.axes = self.figure.add_subplot()
        self.axes.set(
            xlabel="施加磁场 (Gs)", ylabel="法拉第旋角 (deg)", xlim=(-5000, 5000), ylim=(-5000, 5000)
        )
        self._draw_zero_lines()
        self.axes.format_coord = self._format_coord
        self.figure.tight_layout()
        self.figure_canvas = mpl.FigureCanvas(self.canvas_mpl, self.figure)
        self.toolbar = ChineseFigureToolbar(self.canvas_mpl, self.figure_canvas)
        self.figure_canvas.pack(side="bottom", fill="x", expand=True)
        overlay_base, overlay_foreground = (
            ("#d8d8d8", "#202020") if COLOR_MODE == "light" else ("#454545", "#ffffff")
        )
        self.mpl_overlay = tk.Canvas(
            self.master,
            background=overlay_base,
            highlightthickness=0,
            cursor="arrow",
        )
        self.mpl_overlay.create_rectangle(
            0,
            0,
            960,
            500,
            fill=overlay_base,
            outline=overlay_base,
        )
        tk.Label(
            self.mpl_overlay,
            text="读取数据后再使用",
            font=(HONOR_SANS_CN, 22),
            foreground=overlay_foreground,
            background=overlay_base,
        ).place(relx=0.5, rely=0.5, anchor="center")
        self._set_data_controls_enabled(False)
        self._bind_parameter_updates()
        self.slope_slider.bind("<MouseWheel>", self._on_slope_wheel, auto_detect=False)

    def _on_slope_slider_changed(self, value: float) -> None:
        quantized = round(value / 0.005) * 0.005
        self.slope_slider.set(quantized)
        self._update_slope_factor_label()
        self._on_parameter_changed()

    def _set_status(self, message: str, value: str = "", full_value: str = "") -> None:
        self.status_message.configure(text=message)
        self.status_value.configure(text=value)
        self._status_full_value = full_value

    def _copy_status_value(self, _event=None) -> None:
        if not self._status_full_value:
            return
        self.master.clipboard_clear()
        self.master.clipboard_append(self._status_full_value)
        self.master.update_idletasks()

    def _show_status_tooltip(self, _event=None) -> None:
        if not self._status_full_value or self._status_tooltip is not None:
            return
        self._status_tooltip = tk.Toplevel(self.master)
        self._status_tooltip.overrideredirect(True)
        self._status_tooltip.attributes("-topmost", True)
        tk.Label(
            self._status_tooltip,
            text="左键复制完整精度数值",
            font=(HONOR_SANS_CN, 12),
            background="#fff8dc",
            foreground="#202020",
            padx=6,
            pady=3,
        ).pack()
        self._status_tooltip.update_idletasks()
        x = self.status_value.winfo_rootx()
        y = self.status_value.winfo_rooty() - self._status_tooltip.winfo_height() - 4
        self._status_tooltip.geometry(f"+{x}+{y}")

    def _hide_status_tooltip(self, _event=None) -> None:
        if self._status_tooltip is not None:
            self._status_tooltip.destroy()
            self._status_tooltip = None

    def _on_slope_wheel(self, event) -> None:
        if not self.slope_slider.detect(event.x, event.y):
            return
        direction = 1 if event.delta > 0 else -1
        value = min(1.0, max(0.0, self.slope_slider.get() + direction * 0.005))
        self.slope_slider.set(value)
        self._update_slope_factor_label()
        self._on_parameter_changed()

    def _update_slope_factor_label(self) -> None:
        if not self.slope_factor_label.disappeared:
            factor = 0.5 + self.slope_slider.get()
            self.slope_factor_label.set(f"{factor:.3f}x")

    def _on_baseline_switch(self, value: bool) -> None:
        self._on_parameter_changed()

    def _on_parameter_changed(self, *_args) -> None:
        if self.data is not None:
            if self._plot_job is not None:
                self.master.after_cancel(self._plot_job)
            self._plot_job = self.master.after(120, self._plot_after_parameter_change)

    def _plot_after_parameter_change(self) -> None:
        self._plot_job = None
        self.plot()

    def _bind_parameter_updates(self) -> None:
        for control in (self.start_box, self.end_box, self.deg_box, self.thin_box):
            control.children[0].bind(
                "<KeyRelease>", self._on_parameter_changed, auto_detect=False
            )
            control.feature._mouse_wheel = (
                lambda event, control=control: self._on_spinbox_wheel(control, event)
            )

    def _on_spinbox_wheel(self, control, event) -> bool:
        if not control.detect(event.x, event.y):
            return False
        control.change(event.delta > 0)
        self._on_parameter_changed()
        return True

    def _set_data_controls_enabled(self, enabled: bool) -> None:
        self.export_button.disable(not enabled)
        self.slope_slider.disable(not enabled)
        if enabled:
            self.mpl_overlay.place_forget()
        else:
            self.mpl_overlay.place(x=0, y=300, width=960, height=500)

    def show_mpl_overlay(self) -> None:
        self.mpl_overlay.place(x=0, y=300, width=960, height=500)

    def _draw_zero_lines(self) -> None:
        self.axes.axhline(0, color=ZERO_LINE_COLOR, linewidth=1.2, alpha=0.9, zorder=2)
        self.axes.axvline(0, color=ZERO_LINE_COLOR, linewidth=1.2, alpha=0.9, zorder=2)

    def selectPath(self):
        filetypes = [("Excel表格文件", "*.xls"), ("全部文件", "*.*")]
        self.file_name = filedialog.askopenfilename(title="选择单个文件", filetypes=filetypes)
        if not self.file_name:
            return
        try:
            self.data = read_measurement(self.file_name)
        except (OSError, ValueError, ImportError):
            self.data = None
            self._set_data_controls_enabled(False)
            messagebox.showerror(title="错误", message="文件读取失败!")
            self._set_status("文件读取失败!")
            return
        direction, extreme_row = describe_measurement(self.data)
        self._set_data_controls_enabled(True)
        self.slope_slider.set(0.5)
        if not self.slope_factor_label.disappeared:
            self.slope_factor_label.set("1.000x")
        self.path_var.set(os.path.basename(self.file_name))
        self._set_status(f"法拉第测试文件读取成功({direction}在第{extreme_row}行)")
        self.label_text.set(f"求斜率:采用线性拟合的斜率({direction}在第{extreme_row}行)")
        self.label_text.update()
        self.plot()

    def plot(self):
        if self.data is None:
            messagebox.showerror(title="错误", message="请先选择数据文件!")
            return
        try:
            manual_slope_factor = 0.5 + self.slope_slider.get()
            result = process_measurement(
                self.data,
                angle=float(self.deg_box.get()),
                thickness=float(self.thin_box.get()),
                normalize_thickness=self.thin_switch.get(),
                remove_baseline=self.k_switch.get(),
                manual_slope_factor=manual_slope_factor,
                baseline_start=int(self.start_box.get()),
                baseline_end=int(self.end_box.get()),
            )
        except (TypeError, ValueError, OSError) as error:
            self._set_status(str(error))
            return
        self.df = result.data
        self.suffix = result.unit
        if result.slope is not None:
            self._update_slope_factor_label()
        if result.fitted_rotation is not None:
            self._set_status(
                "拟合法拉第测试结果为 ",
                f"{result.fitted_rotation:.3f} {self.suffix}",
                f"{result.fitted_rotation:.17g}",
            )
        else:
            self._set_status("")
        self.axes.clear()
        self.axes.plot(self.df[FIELD_COLUMN], self.df[CURRENT_COLUMN])
        self.axes.set(xlabel="施加磁场 (Gs)", ylabel=f"法拉第旋角 ({self.suffix})")
        self._draw_zero_lines()
        self.axes.format_coord = self._format_coord
        self.figure_canvas.draw_idle()
        self.figure_canvas.flush_events()

    @staticmethod
    def _format_coord(x: float, y: float) -> str:
        return f"x={x:.2f}, y={y:.2f}"

    def export(self):
        if not hasattr(self, "df"):
            messagebox.showerror(title="错误", message="请先绘图再导出!")
            return
        file_path = filedialog.asksaveasfilename(
            title="选择单个文件",
            defaultextension=".csv",
            filetypes=[("逗号分隔值文件(CSV)", "*.csv"), ("全部文件", "*.*")],
        )
        if file_path:
            self.df.to_csv(
                file_path,
                columns=[FIELD_COLUMN, CURRENT_COLUMN],
                header=[self.axes.xaxis.get_label_text(), self.axes.yaxis.get_label_text()],
                index=False,
                encoding="utf8",
            )
            self._set_status(f"保存文件到：{file_path}")