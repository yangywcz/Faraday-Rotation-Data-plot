# Faraday-Rotation-Data-plot
处理东方晨景公司测得法拉第旋角原始数据
![界面](https://raw.kkgithub.com/yangywcz/Faraday-Rotation-Data-plot/main/GUI_detail.png)
## 下载 & update history
[Release页下载](https://github.com/yangywcz/Faraday-Rotation-Data_plot/releases)
- 目前因为PySide6和PyInstaller最新版本尚未兼容，分发版本仍为使用PySide2编写的v0.8版本

## 描述
根据法拉第测试方法，从光电流求出法拉第旋角的公式如下

<img src="https://latex.codecogs.com/svg.latex?\theta%20=\Delta%20-\mathrm{arc}\sin%20\left(%20\sqrt{\frac{I}{I_0}\sin%20\Delta}%20\right)" title="\theta =\Delta -\mathrm{arc}\sin \left( \sqrt{\frac{I}{I_0}\sin \Delta} \right)" />

- Δ是在检偏器上提前预设的旋转角，通常为2°或4°，根据公式可得法拉第旋角，单位通常为deg
- 比法拉第是指单位长度法拉第旋角，单位通常为deg/cm
- 由于基底的磁性会在测得法拉第旋角上加上一条斜率一定的曲线，将其减去即为磁性薄膜的法拉第旋角，方法就是通过起始行数和结束行数选取一部分数据，对该部分数据进行最小二乘法线性拟合，得到其斜率，并对原始数据减去该斜率（无磁基底不需要该步骤）
- 对于如何选择起始和结束行数，主要依靠经验，通常都取能使法拉第旋角大的结果
- 在绘图窗口右击即可获得丰富功能，包括数据的范围和再处理，最重要的是可以进行导出操作，Matplotlib绘图和图片可以给出简单绘图，csv的数据导出可以再进行后续绘图

## 源码编译
- 对于不同的操作系统，已打包好的程序可能无法正常运行，该程序仅在Windows 10 64位操作系统上正常测试，Windows 7没有进行测试，Xp系统确定无法运行，Linux及MacOS因为平台不同，未编译对应程序，可使用源码在该平台自行编译
### 编译所需包
| 包名称 | 备注 |
|:-------------- |:--------------------------------- |
| numpy | 一定需要mkl支持 |
| pandas |  |
| Matplotlib | |
| Excel相关包 | 推荐xlrd，openpyxl |
| Qt相关包 | 推荐PySide6，PyQt5/PyQt6/PySide2可能需要修改部分代码 |
| PyInstaller | 仅限Windows系统分发 |
