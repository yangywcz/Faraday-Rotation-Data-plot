# Changelog

本文件记录 Faraday Rotation Data Plot 的重要变更。

## [Unreleased]

### 新增

- 增加基于 Maliang/Tk 的数据绘图界面。
- 增加 Honor Sans CN 项目字体资源和统一字体配置。
- 增加 splash 启动画面、淡入淡出效果和项目图标。
- 增加鼠标滚轮调整行号、旋转角度、膜厚和斜率倍率。
- 增加斜率倍率滑块，支持 `0.500x` 到 `1.500x`，步进为 `0.005`。
- 增加状态栏拟合结果高亮、悬停提示和全精度复制。
- 增加 MPL 的中文工具栏、零点参考线和坐标格式化。
- 增加 GitHub Actions Windows exe 构建与 Release 发布流程。
- 增加 Windows 10/11、macOS Intel/Apple Silicon 和 Ubuntu 的原生构建与 Release 资产。
- 增加基于 Python 3.8 和原生 Tkinter 的 Windows 7 x86/x64 独立程序；x86 版不包含 SciPy 非线性拟合。

### 改进

- 将数据读取、旋角计算、基线扣除和曲线拟合拆分到独立处理模块。
- 文件读取后自动绘图，参数变化后自动更新曲线。
- 无数据时禁用导出和斜率滑块，并显示 MPL 操作提示层。
- 重新读取数据时重置斜率倍率为 `1.000x`。
- 优化深色和浅色模式下的覆盖层、状态栏和控件布局。
- 将旧 Qt 程序及相关资源移动到 `QT/` 目录归档。
- 为不同平台使用独立构建流程；Windows 7 版不依赖 Maliang。
- Windows 7 版采用 ttkbootstrap 深色主题和原生 Spinbox，并优化控件对齐与绘图区布局。
- Excel 读取统一使用 `python-calamine`，移除 `xlrd` 依赖。

### 修复

- 修复 Matplotlib 画布更新后曲线不刷新的问题。
- 修复隐藏斜率控件更新时产生的 Tkinter bbox 异常。
- 修复 splash 透明边缘和覆盖层跟随主窗口移动的问题。
- 修复输入框滚轮只触发回调但不改变数值的问题。
- 修复覆盖层遮挡文件选择对话框的问题。
- 消除 Pillow `Image.getdata()` 弃用警告。
- Windows 7 版改用 `python-calamine` 读取 Excel，避免 Pandas `xlrd` 引擎弃用警告。
- 跨平台启动时仅在 Windows 调用 Windows 专用字体和窗口 API。

### 构建

- 使用 `pyproject.toml` 和 `uv.lock` 管理项目依赖。
- GitHub Actions 支持手动输入语义化版本号，并自动创建 GitHub Release 上传 exe。
- Windows 7 使用 Python 3.8、旧版兼容科学计算依赖和 PyInstaller 独立打包。
