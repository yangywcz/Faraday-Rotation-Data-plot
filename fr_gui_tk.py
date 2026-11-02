from __future__ import annotations

import sys
import tkinter as tk

import maliang
from PIL import Image, ImageTk

from faraday_rotation_data_plot.gui import Application
from faraday_rotation_data_plot.resources import ICON_PATH, SPLASH_PATH


def _prepare_splash_image() -> tuple[Image.Image, str]:
    image = Image.open(SPLASH_PATH).convert("RGBA")
    if sys.platform != "win32":
        return image, ""
    used_colors = {pixel[:3] for pixel in image.get_flattened_data()}
    transparent_rgb = next(
        color
        for color in ((1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12))
        if color not in used_colors
    )
    width, height = image.size
    radius = 28
    pixels = image.load()

    for y in range(height):
        for x in range(width):
            in_corner = False
            if x < radius and y < radius:
                in_corner = (x - radius) ** 2 + (y - radius) ** 2 > radius**2
            elif x >= width - radius and y < radius:
                in_corner = (x - (width - radius - 1)) ** 2 + (y - radius) ** 2 > radius**2
            elif x < radius and y >= height - radius:
                in_corner = (x - radius) ** 2 + (y - (height - radius - 1)) ** 2 > radius**2
            elif x >= width - radius and y >= height - radius:
                in_corner = (
                    (x - (width - radius - 1)) ** 2
                    + (y - (height - radius - 1)) ** 2
                    > radius**2
                )

            if in_corner:
                pixels[x, y] = (*transparent_rgb, 255)
            else:
                pixels[x, y] = (*pixels[x, y][:3], 255)

    transparent_color = "#%02x%02x%02x" % transparent_rgb
    return image, transparent_color


def show_splash(root: maliang.Tk) -> tk.Toplevel:
    root.withdraw()
    image, transparent_color = _prepare_splash_image()
    splash_image = ImageTk.PhotoImage(image)
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    if sys.platform == "win32":
        splash.configure(background=transparent_color)
        splash.wm_attributes("-transparentcolor", transparent_color)
    try:
        splash.wm_attributes("-alpha", 0.0)
    except tk.TclError:
        pass
    splash_image_label = tk.Label(
        splash,
        image=splash_image,
        borderwidth=0,
        highlightthickness=0,
        background=transparent_color,
    )
    splash_image_label.image = splash_image
    splash_image_label.pack()
    splash.update_idletasks()
    splash.geometry(
        f"{splash.winfo_width()}x{splash.winfo_height()}"
        f"+{(splash.winfo_screenwidth() - splash.winfo_width()) // 2}"
        f"+{(splash.winfo_screenheight() - splash.winfo_height()) // 2}"
    )
    splash.update()
    return splash


def fade_in(window: tk.Toplevel, step: int = 0) -> None:
    alpha = min(step / 14, 1.0)
    try:
        window.wm_attributes("-alpha", alpha)
    except tk.TclError:
        return
    if alpha < 1.0:
        window.after(25, fade_in, window, step + 1)


def fade_out(
    root: maliang.Tk,
    window: tk.Toplevel,
    step: int = 14,
    on_finished=None,
) -> None:
    alpha = max(step / 14, 0.0)
    try:
        window.wm_attributes("-alpha", alpha)
    except tk.TclError:
        alpha = 0.0
    if alpha > 0.0:
        window.after(32, fade_out, root, window, step - 1, on_finished)
    else:
        window.destroy()
        root.deiconify()
        if on_finished is not None:
            on_finished()


def main() -> None:
    root = maliang.Tk((960, 830), title="法拉第测试绘图")
    if sys.platform == "win32":
        root.iconbitmap(str(ICON_PATH))
    root.resizable(0, 0)
    root.center()
    splash = show_splash(root)
    app = Application(master=root)
    root.after(25, fade_in, splash)
    root.after(2200, fade_out, root, splash, 14, app.show_mpl_overlay)
    root.mainloop()


if __name__ == "__main__":
    main()