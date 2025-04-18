import os
import numpy as np
import pandas as pd
from PySide6.QtGui import QIcon, QFont
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow,QMessageBox,QSplashScreen
from configparser import ConfigParser
import pyqtgraph as pg
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import time
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号


class Stats():

    def __init__(self): 
        loader = QUiLoader()
        loader.registerCustomWidget(pg.PlotWidget)
        self.ui = loader.load("fr.ui")
        
        self.config = ConfigParser()
        if os.path.exists('config.ini'):
            self.config.read('config.ini', encoding='UTF-8')
        else:
            self.config['Default'] = {'End_line': 30, 'offset_degree': 2.0, 'thickness': 100.0, 'init_dir':f'{os.getcwd()}'}
            with open('config.ini', 'w', encoding='utf-8') as file:
                self.config.write(file)
                
        self.dir=self.config['Default']['init_dir']
        self.ui.spinBox_end.setValue(int(self.config['Default']['End_line']))
        self.ui.deg.setValue(float(self.config['Default']['offset_degree']))
        self.ui.thickness.setValue(float(self.config['Default']['thickness']))

        self.ui.qtplot.showGrid(x=True, y=True)
        self.ui.qtplot.setLabel("bottom", "磁场(G)")
        self.curve = self.ui.qtplot.getPlotItem().plot(pen=pg.mkPen(width=3))
        self.ui.plot1.setEnabled(False)
        self.ui.plot2.setEnabled(False)
        self.ui.plot3.setEnabled(False)
        self.ui.plot4.setEnabled(False)

        self.ui.filebrowser.clicked.connect(self.browser)
        self.ui.plot1.clicked.connect(self.plot1)
        self.ui.plot2.clicked.connect(self.plot2)
        self.ui.plot3.clicked.connect(self.plot3)
        self.ui.plot4.clicked.connect(self.plot4)
        

    def browser(self):
        self.file = QFileDialog.getOpenFileName(caption=f"选择法拉第测试文件",dir=self.dir,filter="Excel表格文件 (*.xls *.xlsx)")
        if self.file:
            self.dir = os.path.dirname(self.file[0])
            self.config['Default']['init_dir']=self.dir
            with open('config.ini', 'w', encoding='utf-8') as file:
                self.config.write(file)
            self.ui.lineEdit.setText(os.path.basename(self.file[0]))
            QApplication.processEvents()
            try:
                df = pd.read_excel(self.file[0],usecols=['磁场(G)','电流(A)'])
            except:
                msgBox = QMessageBox(QMessageBox.Critical,'错误','文件读取失败!')
                msgBox.exec()
                self.ui.statusbar.showMessage('文件读取失败!')   
                self.ui.plot1.setEnabled(False)
                self.ui.plot2.setEnabled(False)
                self.ui.plot3.setEnabled(False)
                self.ui.plot4.setEnabled(False) 
            else:
                self.ui.plot1.setEnabled(True)
                self.ui.plot2.setEnabled(True)
                self.ui.plot3.setEnabled(True)
                self.ui.plot4.setEnabled(True)
                if df.loc[0,'磁场(G)'] >= 0:
                    self.ui.statusbar.showMessage(f"法拉第测试文件读取成功(正⇨负⇨正,负磁场最大值在第{np.argmin(df['磁场(G)'])}行)")
                    self.ui.label_2.setText(f"求斜率:采用线性拟合的斜率(负磁场最大值在第{np.argmin(df['磁场(G)'])}行)")
                else:
                    self.ui.statusbar.showMessage(f"法拉第测试文件读取成功(负⇨正⇨负,正磁场最大值在第{np.argmax(df['磁场(G)'])}行)")
                    self.ui.label_2.setText(f"求斜率:采用线性拟合的斜率(正磁场最大值在第{np.argmax(df['磁场(G)'])}行)")
        else:    
            self.ui.lineEdit.clear()
            self.ui.statusbar.showMessage('没有读入文件!')
            self.ui.plot1.setEnabled(False)
            self.ui.plot2.setEnabled(False)
            self.ui.plot3.setEnabled(False)
            self.ui.plot4.setEnabled(False)
        
    

    def plot1(self):
        self.ui.qtplot.setLabel("left", "法拉第旋角 (deg)")
        df = pd.read_excel(self.file[0],usecols=['磁场(G)','电流(A)'])
        df['电流(A)']=self.ui.deg.value()-np.rad2deg(np.arcsin(np.sqrt(df['电流(A)']/df['电流(A)'].median())*np.sin(np.deg2rad(self.ui.deg.value()))))#self.ui.deg.value()*(1-np.sqrt(df['电流(A)']/df['电流(A)'].median())) 
        df.dropna(axis=0,inplace=True)
        self.curve.setData(df['磁场(G)'],df['电流(A)'])



    def plot2(self):
        self.ui.qtplot.setLabel("left", "法拉第旋角 (deg)")
        df = pd.read_excel(self.file[0],usecols=['磁场(G)','电流(A)'])
        df['电流(A)']=self.ui.deg.value()-np.rad2deg(np.arcsin(np.sqrt(df['电流(A)']/df['电流(A)'].median())*np.sin(np.deg2rad(self.ui.deg.value()))))
        df.dropna(axis=0,inplace=True)
        co = self.ui.spinBox_start.value()
        ci = self.ui.spinBox_end.value()
        if co == ci:
            msgBox = QMessageBox(QMessageBox.Critical,'错误','起始行数和结束行数必须不同!')
            msgBox.exec()
            self.ui.statusbar.showMessage('起始行数和结束行数必须不同!')
        elif co>len(df.index) or ci>len(df.index):
            msgBox = QMessageBox(QMessageBox.Critical,'错误',f'超出索引(文件最大行数为{len(df.index)-1})!')
            msgBox.exec()
            self.ui.statusbar.showMessage(f'超出索引(文件最大行数为{len(df.index)-1})!')
        else:
            try:
                k, _ = np.polyfit(df.loc[min(co,ci):max(co,ci),'磁场(G)'], df.loc[min(co,ci):max(co,ci),'电流(A)'], 1)
            except:
                msgBox = QMessageBox(QMessageBox.Critical,'错误','所选区间无法线性拟合，请选择合适区间!')
                msgBox.exec()
                self.ui.statusbar.showMessage('所选区间无法线性拟合，请选择合适区间!')
            else:
                df['电流(A)'] = (df['电流(A)']-k*df['磁场(G)'])
                def fit_func(x,M,r,b,c):
                    return M*np.tanh(r*x)-b*x-c
                try:
                    popt, pcov = curve_fit(fit_func, df['磁场(G)'],df['电流(A)'],p0=(df['电流(A)'].max(),0.002,0,(df['电流(A)'].max()+df['电流(A)'].min())/2),method='trf')
                    df['电流(A)'] += popt[-1]
                    self.ui.statusbar.showMessage(f'拟合法拉第测试结果为 {fit_func(df['磁场(G)'], *popt).max()+popt[-1]:g} deg')
                except:
                    self.ui.statusbar.showMessage(f'未能成功拟合测试数据')
                finally:
                    self.curve.setData(df['磁场(G)'],df['电流(A)'])
                    
    def plot3(self):
        self.ui.qtplot.setLabel("left", "法拉第旋角 (deg/cm)")
        df = pd.read_excel(self.file[0],usecols=['磁场(G)','电流(A)'])
        df['电流(A)']=(self.ui.deg.value()-np.rad2deg(np.arcsin(np.sqrt(df['电流(A)']/df['电流(A)'].median())*np.sin(np.deg2rad(self.ui.deg.value())))))/self.ui.thickness.value()*1e7    
        df.dropna(axis=0,inplace=True)
        self.curve.setData(df['磁场(G)'],df['电流(A)'])
    
    def plot4(self):
        self.ui.qtplot.setLabel("left", "法拉第旋角 (deg/cm)")
        df = pd.read_excel(self.file[0],usecols=['磁场(G)','电流(A)'])
        df['电流(A)']=self.ui.deg.value()-np.rad2deg(np.arcsin(np.sqrt(df['电流(A)']/df['电流(A)'].median())*np.sin(np.deg2rad(self.ui.deg.value()))))
        df.dropna(axis=0,inplace=True)
        co = self.ui.spinBox_start.value()
        ci = self.ui.spinBox_end.value()
        if co == ci:
            msgBox = QMessageBox(QMessageBox.Critical,'错误','起始行数和结束行数必须不同!')
            msgBox.exec()
            self.ui.statusbar.showMessage('起始行数和结束行数必须不同!')
        elif co>len(df.index) or ci>len(df.index):
            msgBox = QMessageBox(QMessageBox.Critical,'错误',f'超出索引(文件最大行数为{len(df.index)-1})!')
            msgBox.exec()
            self.ui.statusbar.showMessage(f'超出索引(文件最大行数为{len(df.index)-1})!')
        else:
            try:
                k, _ = np.polyfit(df.loc[min(co,ci):max(co,ci),'磁场(G)'], df.loc[min(co,ci):max(co,ci),'电流(A)'], 1)
            except:
                msgBox = QMessageBox(QMessageBox.Critical,'错误','所选区间无法线性拟合，请选择合适区间!')
                msgBox.exec()
                self.ui.statusbar.showMessage('所选区间无法线性拟合，请选择合适区间!')
            else:
                df['电流(A)'] = (df['电流(A)']-k*df['磁场(G)'])/self.ui.thickness.value()*1e7    
                def fit_func(x,M,r,b,c):
                    return M*np.tanh(r*x)-b*x-c
                try:
                    popt, pcov = curve_fit(fit_func, df['磁场(G)'],df['电流(A)'],p0=(df['电流(A)'].max(),0.002,0,(df['电流(A)'].max()+df['电流(A)'].min())/2),method='trf')
                    df['电流(A)'] += popt[-1]
                    self.ui.statusbar.showMessage(f'拟合法拉第测试结果为 {fit_func(df['磁场(G)'], *popt).max()+popt[-1]:g} deg/cm')
                except:
                    self.ui.statusbar.showMessage(f'未能成功拟合测试数据')
                finally:
                    self.curve.setData(df['磁场(G)'],df['电流(A)'])
                    

app = QApplication([])
translator = QtCore.QTranslator()
translator.load("qt_zh_CN.qm")
app.installTranslator(translator)
app.setFont(QFont('微软雅黑'))
app.setWindowIcon(QIcon('logo.png'))

splash_pix=QtGui.QPixmap('SplashScreen.png').scaled(600, 600, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
splash = QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
splash.show()
time.sleep(1)

stats = Stats()
stats.ui.setWindowIcon(QIcon('logo.png'))
stats.ui.setStyleSheet("*{font-family:微软雅黑;font-size:14pt;}")
screen = app.primaryScreen().geometry()
size = stats.ui.geometry()
stats.ui.resize(size.width(), size.width()*10/16+30)
size = stats.ui.geometry()
stats.ui.move((screen.width() - size.width()) / 2,
              (screen.height() - size.height()) / 2)
stats.ui.show()
splash.finish(stats.ui)
app.exec()
