# Vocal Separator App

一个本地运行的人声与背景音分离 Web 应用。上传音频或视频后，输出人声轨与背景音/伴奏轨。

## 功能

- 本地上传和处理音频/视频文件
- 支持 Demucs AI 高质量分离
- Demucs 不可用时自动退回 FFmpeg 快速算法
- 支持 WAV 和 MP3 输出
- 页面内试听、下载、保存到本机输出目录
- Apple 风格浅色界面

## 快速启动

```powershell
cd D:\codex\vocal_separator_app
.\start.ps1
```

或双击：

```text
launch_app.cmd
```

启动后打开：

```text
http://127.0.0.1:7860/
```

注意：本地服务窗口必须保持打开。关闭窗口后，网页会显示 `ERR_CONNECTION_REFUSED`。

## 安装 AI 分离环境

```powershell
cd D:\codex\vocal_separator_app
.\install_ai.ps1
```

安装完成后，在页面选择 `高质量优先` 或 `只用 Demucs AI`。第一次运行 Demucs 可能会下载模型文件。

## 输出目录

每次处理会生成一个独立任务目录：

```text
jobs/<job-id>
```

页面里的 `保存到本机` 会复制结果到：

```text
outputs/<job-id>
```

## 不上传到 GitHub 的内容

以下内容已通过 `.gitignore` 排除：

- Python 虚拟环境
- Demucs/PyTorch 安装环境
- FFmpeg 二进制文件
- 上传和分离后的音频结果
- 日志和缓存
