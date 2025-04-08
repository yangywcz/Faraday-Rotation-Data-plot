import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

import maliang
from maliang import mpl, theme
from tkinter import filedialog,messagebox
from scipy.optimize import curve_fit

mpl.set_mpl_default_theme(theme.get_color_mode())

# rcParams设置
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
plt.rcParams['lines.linewidth'] = 1.5
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['axes.titlesize'] = 'larger'
plt.rcParams['axes.labelsize'] = 'larger'
plt.rcParams['xtick.minor.visible'] = True
plt.rcParams['ytick.minor.visible'] = True
plt.rcParams['xtick.direction'] = 'in'
plt.rcParams['ytick.direction'] = 'in'
plt.rcParams['axes.grid'] = True

class Application():
    def __init__(self, master):
        self.master = master
        self.canvas = maliang.Canvas(auto_zoom=True,auto_update=True)
        self.canvas.place(width=960, height=830)
        self.canvas_mpl = maliang.Canvas(auto_zoom=True,auto_update=True)
        self.canvas_mpl.place(width=960, height=500,y=300)
        self.file_name = None

        maliang.Text(self.canvas, (10, 20), text="文件路径", anchor="nw")
        self.path_var=maliang.InputBox(self.canvas, (120, 10), (700,40),anchor="nw", placeholder="浏览文件")
        maliang.Button(self.canvas, (950, 10),(100,40), text="浏览", anchor="ne", command=self.selectPath)
        
        self.label_text = maliang.Text(self.canvas, (10, 80), anchor="nw", text="求斜率:采用线性拟合的斜率")
        
        maliang.Text(self.canvas, (10, 140), text="起始行数", anchor="nw")
        self.start_box=maliang.SpinBox(self.canvas, (120, 130),(120, 40),default='0')
        maliang.Text(self.canvas, (280, 140), text="结束行数", anchor="nw")
        self.end_box=maliang.SpinBox(self.canvas, (380, 130),(120, 40),default='30')
        self.slope_switch = maliang.Switch(self.canvas, (550, 140),default=False)
        maliang.Text(self.canvas, (640, 140), text="手动设置斜率：", anchor="nw")        
        self.slope_box = maliang.SpinBox(self.canvas, (780, 130),(120, 40),format_spec='.2f',step=0.01,default='10.00')
        maliang.Text(self.canvas, (950, 140), text="E-7", anchor="ne")

        maliang.Text(self.canvas, (10, 190), text="旋转角度", anchor="nw")
        self.deg_box = maliang.SpinBox(self.canvas, (120, 180),(120, 40),format_spec='.2f',step=0.01,default='2.00')
        maliang.Text(self.canvas, (250, 190), text="度", anchor="nw")

        maliang.Text(self.canvas, (10, 240), text="膜厚", anchor="nw")
        self.thin_box = maliang.SpinBox(self.canvas, (120, 240),(120, 40),format_spec='.2f',step=0.01,default='100.00')
        maliang.Text(self.canvas, (250, 240), text="nm", anchor="nw")
        self.k_switch = maliang.Switch(self.canvas, (300, 240),default=True)
        maliang.Text(self.canvas, (370, 240), text="减斜率", anchor="nw")
        self.thin_switch = maliang.Switch(self.canvas, (450, 240),default=True)
        maliang.Text(self.canvas, (530, 240), text="除以膜厚", anchor="nw")

        maliang.Button(self.canvas, (950, 240),(140,40), text="导出", anchor="ne", command=self.export)
        maliang.Button(self.canvas, (800, 240),(140,40), text="绘图", anchor="ne", command=self.plot)
        
        self.statusbar = maliang.Label(self.canvas, (0, 830),(960, 30),anchor='sw', text="准备就绪",fontsize=18)

        self.figure = plt.Figure()
        self.axes = self.figure.add_subplot()

        self.axes.set(xlabel='施加磁场 (Gs)', ylabel='法拉第旋角 (deg)',xlim=(-5000,5000),ylim=(-5000,5000))
        self.figure.tight_layout()

        self.figure_canvas = mpl.FigureCanvas(self.canvas_mpl, self.figure)
        self.toolbar = mpl.FigureToolbar(self.canvas_mpl, self.figure_canvas)
        self.figure_canvas.pack(side="bottom", fill="x", expand=True)

            
    def selectPath(self):
        # 设置可以选择的文件类型，不属于这个类型的，无法被选中
        filetypes = [("Excel表格文件", "*.xls"), ('全部文件', '*.*')]
        self.file_name= filedialog.askopenfilename(title='选择单个文件',filetypes=filetypes,)
        self.path_var.set(os.path.basename(self.file_name))
        try:
            df = pd.read_excel(self.file_name,usecols=['磁场(G)','电流(A)'])
        except:
            messagebox.showerror(title='错误',message='文件读取失败!')
            self.statusbar.set('文件读取失败!')
        else:
            if df.loc[0,'磁场(G)'] >= 0:
                self.statusbar.set(f"法拉第测试文件读取成功(正⇨负⇨正,负磁场最大值在第{np.argmin(df['磁场(G)'])}行)")
                self.label_text.set(f"求斜率:采用线性拟合的斜率(负磁场最大值在第{np.argmin(df['磁场(G)'])}行)")
                self.label_text.update()
            else:
                self.statusbar.set(f"法拉第测试文件读取成功(负⇨正⇨负,正磁场最大值在第{np.argmax(df['磁场(G)'])}行)")
                self.label_text.set(f"求斜率:采用线性拟合的斜率(正磁场最大值在第{np.argmax(df['磁场(G)'])}行)")
                self.label_text.update()

            
    def plot(self):
        self.deg = float(self.deg_box.get())
        self.thin = float(self.thin_box.get())
        if not self.thin_switch.get():
            self.thin = 1e7
        self.df = pd.read_excel(self.file_name,usecols=['磁场(G)','电流(A)'])
        self.df['电流(A)']=self.deg-np.rad2deg(np.arcsin(np.sqrt(self.df['电流(A)']/self.df['电流(A)'].median())*np.sin(np.deg2rad(self.deg))))
        self.df.dropna(axis=0,inplace=True)
        self.suffix = 'deg/cm' if self.thin_switch.get() else 'deg'
        if self.k_switch.get():
            if self.slope_switch.get():
                self.slope = float(self.slope_box.get())*1e-7
                self.df['电流(A)'] = (self.df['电流(A)']-self.slope*self.df['磁场(G)'])
            else:
                co = int(self.start_box.get())
                ci = int(self.end_box.get())
                if co == ci:
                    messagebox.showerror(title='错误',message='起始行数和结束行数必须不同!')
                elif co>len(self.df.index) or ci>len(self.df.index):
                    messagebox.showerror(title='错误',message=f'超出索引(文件最大行数为{len(self.df.index)-1})!')
                else:
                    try:
                        k, _ = np.polyfit(self.df.loc[min(co,ci):max(co,ci),'磁场(G)'], self.df.loc[min(co,ci):max(co,ci),'电流(A)'], 1)
                        self.slope_box.set(f'{k*1e7:.2f}')
                        self.df['电流(A)'] = (self.df['电流(A)']-k*self.df['磁场(G)'])
                    except:
                        messagebox.showerror(title='错误',message='所选区间无法线性拟合，请选择合适区间!')
        
            def fit_func(x,M,r,b,c):
                    return M*np.tanh(r*x)-b*x-c
                
            try:
                popt, pcov = curve_fit(fit_func, self.df['磁场(G)'],self.df['电流(A)'],p0=(self.df['电流(A)'].max(),0.002,0,(self.df['电流(A)'].max()+self.df['电流(A)'].min())/2),method='trf')
                self.df['电流(A)'] += popt[-1]
                self.statusbar.set(f'拟合法拉第测试结果为 {(fit_func(self.df['磁场(G)'], *popt).max()+popt[-1])/self.thin*1e7:g} {self.suffix}')
            except:
                self.statusbar.set(f'未能成功拟合测试数据')
        else:
            self.statusbar.set('')
        
        self.axes.clear()
        self.df['电流(A)']/=self.thin*1e-7
        self.axes.plot(self.df['磁场(G)'],self.df['电流(A)'])
        self.axes.set(xlabel='施加磁场 (Gs)', ylabel=f'法拉第旋角 ({self.suffix})')
        self.toolbar = mpl.FigureToolbar(self.canvas_mpl, self.figure_canvas)
    
        
    def export(self):
        filetypes = [("逗号分隔值文件(CSV)", "*.csv"), ('全部文件', '*.*')]
        file_path = filedialog.asksaveasfilename(title='选择单个文件',defaultextension=".csv",
                                             filetypes=filetypes)
        if file_path:
            x_label = self.axes.xaxis.get_label_text()
            y_label = self.axes.yaxis.get_label_text()
            self.df.to_csv(file_path, columns=['磁场(G)','电流(A)'],header=[x_label,y_label],index=False,encoding='utf8')
            self.statusbar.set(f"保存文件到：{file_path}")
    

if __name__ == '__main__':
    root = maliang.Tk((960, 830), title="法拉第测试绘图")
    root.resizable(0,0)
    root.center()
    app = Application(master=root)
 
    root.mainloop()
