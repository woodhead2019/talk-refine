# 🎤 TalkRefine

**自然说话，输出精炼文字。** 本地离线语音输入 + LLM 润色工具。

按快捷键 → 说话 → 本地 ASR 模型转写 → 本地 LLM 润色为书面语 → 自动粘贴到光标位置。全程离线，隐私安全。

## 特性

- 🗣️ **语音 → 文字 → 精炼文字**，一步到位
- 🔒 **完全离线**，数据不出本机
- ⚡ **极速**，10 秒语音不到 1 秒识别（SenseVoice）
- 🌍 **多语言**，中文、英文、日文、韩文等
- 🧠 **可插拔引擎**，通过配置文件切换 ASR 模型和 LLM
- 📋 **智能粘贴**，自动粘贴到光标，剪贴板内容不丢失
- 🎨 **悬浮 UI**，录音音量条 + 系统托盘图标

## 效果演示

```
🎙️  说话: "嗯就是我觉得吧这个东西有三个问题，第一个就是速度太慢了，
          然后那个界面不好看，然后就是不支持中文对吧"

✨ 输出: - 速度太慢
        - 界面不好看
        - 不支持中文
```

## 快速开始（Windows）

### 一键安装

```powershell
git clone https://github.com/swenyang/talk-refine.git
cd talk-refine
.\scripts\install.ps1
```

自动安装 Python 依赖、ffmpeg、Ollama + Qwen，并设置开机自启。

### 手动安装

```powershell
# 1. 安装系统依赖
winget install Gyan.FFmpeg
winget install Ollama.Ollama
ollama pull qwen2.5:3b

# 2. 安装 Python 包
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install funasr modelscope pyaudio pyperclip pyautogui keyboard requests pystray Pillow pyyaml

# 3. 运行
python -m talkrefine
```

## 使用方法

1. 启动（开始菜单搜 `TalkRefine`，或 `python -m talkrefine`）
2. 按 **F7** 开始录音
3. 自然说话
4. 按 **F7** 停止 → 自动识别、润色、粘贴
5. 按 **ESC** 取消录音（丢弃不处理）

系统托盘图标（右下角）→ 右键菜单：
- 开关 LLM 润色
- 退出程序

## 配置

复制 `config.example.yaml` 为 `config.yaml`，按需修改：

```yaml
hotkey: "f7"              # 录音快捷键（f9, ctrl+shift+r 等均可）
cancel_key: "esc"         # 取消录音
language: "auto"          # "auto", "zh", "en", "ja", ...

asr:
  engine: "sensevoice"    # "sensevoice"（中文最佳）| "whisper"（多语言）
  model: "iic/SenseVoiceSmall"
  device: "cpu"           # "cpu" | "cuda"

llm:
  enabled: true
  provider: "ollama"      # "ollama" | "openai"（兼容 API）| "none"
  endpoint: "http://localhost:11434"
  model: "qwen2.5:3b"
  prompt: "default"       # "default" | "meeting" | "code" | 自定义 .txt 路径

output:
  auto_paste: true        # 自动粘贴到光标
  preserve_clipboard: true  # 粘贴后恢复剪贴板
```

### ASR 引擎

| 引擎 | 适合场景 | 模型大小 | 速度 |
|------|----------|----------|------|
| **SenseVoice**（默认） | 中文 | ~200 MB | ⚡ 极快 |
| **Whisper** | 多语言 | 500MB-3GB | 中等 |

### LLM 提供者

| 提供者 | 配置方式 | 适用场景 |
|--------|----------|----------|
| **Ollama**（默认） | `ollama pull qwen2.5:3b` | 完全离线 |
| **OpenAI 兼容** | 设置 endpoint + api_key | 云端 LLM（OpenAI、DeepSeek、vLLM 等） |
| **None** | — | 仅转写，不润色 |

### Prompt 模板

内置模板位于 `prompts/` 目录：
- **default** — 通用：去口水词、自动分点
- **meeting** — 会议纪要：提取决议和待办
- **code** — 技术口述：保留代码术语

创建自定义 `.txt` 文件，将 `llm.prompt` 设为文件路径即可。

## 系统要求

| | 最低 | 推荐 |
|---|------|------|
| CPU | 4 核 | 8 核+ |
| 内存 | 8 GB | 16 GB+ |
| GPU | **不需要** | — |
| 磁盘 | ~3 GB | ~5 GB |
| 系统 | Windows 10+ | Windows 11 |
| Python | 3.10+ | 3.12 |

## 架构

```
┌────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐
│   麦克风   │───▶│  ASR 引擎   │───▶│ LLM 润色    │───▶│ 自动粘贴 │
│  (PyAudio) │    │ SenseVoice  │    │ Ollama/Qwen │    │ (剪贴板  │
│            │    │ 或 Whisper  │    │ 或 OpenAI   │    │  恢复)   │
└────────────┘    └─────────────┘    └─────────────┘    └──────────┘
```

```
talkrefine/
├── app.py              # 主应用
├── config.py           # 配置加载
├── recorder.py         # 录音模块
├── asr/                # 语音识别引擎（可插拔）
│   ├── base.py
│   ├── sensevoice.py   #   阿里 FunASR SenseVoice
│   └── whisper.py      #   OpenAI Whisper
├── llm/                # LLM 润色（可插拔）
│   ├── base.py
│   ├── ollama.py       #   本地 Ollama
│   ├── openai_compat.py#   OpenAI 兼容 API
│   ├── none.py         #   直通（不润色）
│   └── prompts.py      #   Prompt 模板加载
├── platform/           # 平台适配
│   └── windows.py
└── ui/
    ├── overlay.py      #   悬浮音量条
    └── tray.py         #   系统托盘
```

## 开机自启 & 快捷方式

```powershell
python -m talkrefine --install      # 添加开机自启 + 开始菜单
python -m talkrefine --uninstall    # 移除
```

## 卸载

```powershell
# 1. 移除自启和快捷方式
python -m talkrefine --uninstall

# 2. 卸载 Python 包
pip uninstall funasr modelscope torch torchaudio pyaudio -y

# 3. 删除模型缓存
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\modelscope"

# 4. 卸载 Ollama（可选）
winget uninstall Ollama.Ollama
Remove-Item -Recurse -Force "$env:USERPROFILE\.ollama"
```

## License

MIT
