# Transcriber (Whisper Large-v3)

这是一个本地运行的音视频转写工具，目标是让不会写代码的用户也能直接使用。

核心能力：

- 输入音频或视频，输出对话文本 transcript。
- 主模型使用 openai/whisper large-v3。
- 默认优先使用 GPU（如 RTX 4070 Ti SUPER）。
- 支持中英混合对话转写。
- 提供桌面 GUI 和 CLI 两种使用方式。

## 截止目前我们做了什么

下面按阶段记录每次修改做了什么。

### 第 1 次修改：基础 CLI 管线落地

主要改动：

- 建立项目目录结构：config、src、input、output、logs、temp、models。
- 实现音视频输入识别与校验。
- 实现 FFmpeg 预处理：统一转为 16kHz 单声道 wav。
- 实现 Whisper large-v3 转写（默认 CUDA，支持 CPU 回退）。
- 实现 txt 输出格式（含元数据和分段文本）。
- 增加 Windows 环境脚本和自检脚本。

对应文件：

- main.py
- src/input_router.py
- src/media_preprocess.py
- src/transcribe_whisper.py
- src/format_txt.py
- config/setup_windows.bat
- config/check_env.py

### 第 2 次修改：Windows 兼容与运行稳定性修复

主要改动：

- 修复 FFmpeg 路径问题（Whisper 内部调用 ffmpeg 时保证 PATH 可见）。
- 修复 Windows 子进程输出解码问题（避免 gbk/utf-8 相关报错）。
- 优化 setup 脚本，兼容没有 py 启动器但已有 .venv 的情况。

对应文件：

- main.py
- src/media_preprocess.py
- config/setup_windows.bat

### 第 3 次修改：架构重构与可配置输出

主要改动：

- 抽离服务层，CLI 和 GUI 可复用同一管线。
- 新增统一配置对象，集中管理模型、设备、输出开关等参数。
- 新增批量目录处理能力（支持递归扫描）。
- 输出格式支持两个开关：
   - 是否输出时间戳
   - 是否输出人物标签

对应文件：

- src/models.py
- src/service.py
- src/progress.py
- src/format_txt.py
- src/input_router.py
- main.py

### 第 4 次修改：桌面 GUI 与一键启动

主要改动：

- 新增 Tkinter 桌面应用，支持单文件和批量目录模式。
- GUI 可勾选：
   - Include timestamps
   - Include speaker labels
- 默认勾选状态：两个都关闭。
- 新增双击启动脚本，降低使用门槛。

对应文件：

- gui/app.py
- start_gui.bat
- USER_GUIDE_CN.txt
- README.md

## 当前功能

- 单文件转写（音频/视频）。
- 批量目录转写（可选递归）。
- GPU 优先转写（CUDA 可用时）。
- 输出文件冲突策略：timestamp/sequence/overwrite。
- 可开关输出时间戳。
- 可开关基础人物标签。
- 桌面 GUI + CLI 双入口。

## 重要说明：人物区分目前还没有做好

当前的“区分人物说话”是基础规则法：根据停顿阈值做 Speaker_1、Speaker_2 的轮换标签。

这不是真正高精度的说话人分离（diarization），存在这些限制：

- 无法稳定识别同一说话人身份。
- 多人快速对话时可能标注不准。
- 仅适合作为粗粒度参考。

如果要做到更高准确度，需要后续接入专门的说话人分离模型。

## 使用方法

### 方法 1：桌面 GUI（推荐，给不会代码的用户）

1. 运行：start_gui.bat
2. 选择模式：Single File 或 Batch Folder。
3. 选择输入和输出路径。
4. 根据需要勾选：
    - Include timestamps
    - Include speaker labels
5. 点击 Start Transcription。

### 方法 2：CLI

单文件：

python main.py --input input\sample.mp4 --output-dir output

批量目录：

python main.py --input-dir input --recursive --output-dir output

常用参数：

- --include-timestamps / --no-timestamps
- --include-speakers / --no-speakers
- --device cuda|cpu
- --precision fp32|fp16
- --pause-threshold 1.2
- --max-speakers 2
- --output-conflict-strategy timestamp|sequence|overwrite
- --ffmpeg-bin C:\path\to\ffmpeg.exe

## 环境安装

1. 安装 Python 3.11（或使用现有虚拟环境）。
2. 安装 FFmpeg（可使用 winget）。
3. 运行：

config\setup_windows.bat

该脚本会创建 .venv、安装依赖并执行环境检查。

## 目录说明

- config：环境与脚本
- src：核心转写逻辑
- gui：桌面界面
- input：输入文件目录（默认不提交媒体文件）
- output：输出文本目录
- logs：日志目录
- temp：临时文件目录
- models：模型缓存目录

## Git 提交注意事项

本仓库已配置忽略规则，默认不会提交：

- input 中的音视频文件
- output 中的转写结果
- 虚拟环境和 .env 等本地环境文件
- 模型缓存和临时文件

