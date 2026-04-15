"""Centralized i18n strings for TalkRefine."""

_STRINGS = {
    "zh": {
        # ── Overlay ──
        "recording": "🎤 录音中... {hotkey}=完成  {cancel}=取消",
        "recognizing": "⏳ 识别中...",
        "refining": "✍️ 润色中...",
        "cancelled": "🚫 已取消",
        "no_audio": "⚠️ 未检测到音频",
        "too_short": "⚠️ 录音太短",
        "no_speech": "⚠️ 未识别到内容",
        "error": "❌ 出错",
        "ready": "🟢 按 {hotkey} 开始录音",
        "loading": "⏳ 加载模型中...",
        "loading_asr": "⏳ 语音模型加载中...",
        "loading_llm": "⏳ LLM 加载中...",
        "model_not_ready": "⏳ 模型加载中...",
        "pasted": "📋 已粘贴",
        "copied": "📋 已复制",
        "processing": "⏳ 正在处理上一条录音...",

        # ── Tray ──
        "recent": "── 最近记录 ──",
        "history": "📜 历史记录",
        "settings": "⚙️ 设置",
        "quit": "退出",

        # ── Settings ──
        "settings_title": "TalkRefine 设置",
        "tab_general": "通用",
        "tab_asr": "语音识别",
        "tab_llm": "LLM 润色",
        "tab_output": "输出",
        "ui_language": "界面语言",
        "autostart": "开机自动启动",
        "record_hotkey": "录音快捷键",
        "cancel_key": "取消快捷键",
        "recognition_lang": "识别语言",
        "asr_model": "识别模型",
        "device": "运行设备",
        "enable_llm": "启用 LLM 润色",
        "provider": "提供者",
        "endpoint": "服务端点",
        "detect": "检测",
        "model": "模型",
        "refresh": "刷新",
        "api_key": "API Key",
        "prompt": "提示词",
        "prompt_presets": "预设模板",
        "general_preset": "通用",
        "meeting_preset": "会议",
        "code_preset": "代码",
        "temperature": "Temperature",
        "auto_paste": "自动粘贴到光标",
        "preserve_clipboard": "粘贴后恢复剪贴板",
        "save": "💾 保存",
        "cancel": "取消",
        "auto_detect": "自动",
        "chinese": "中文",
        "hotkey_conflict": "⚠️ 此快捷键可能与输入法冲突",
        "save_success": "保存成功",
        "save_msg": "配置已生效。ASR 模型更改将自动重启。",
        "endpoint_ok": "✅ 连接成功",
        "endpoint_fail": "❌ 连接失败",
        "restore_default": "🔄 恢复默认",
        "recommended_cn": "推荐中文",
        "install_more": "📦 安装更多引擎",

        # ── History ──
        "history_title": "TalkRefine 历史记录",
        "time_col": "时间",
        "duration_col": "时长",
        "raw_col": "原始转写",
        "refined_col": "润色结果",
        "copy_refined": "📋 复制润色结果",
        "copy_raw": "📋 复制原始转写",
        "clear_history": "🗑️ 清空",
        "clear_confirm": "确定要清空所有历史记录吗？",
        "confirm": "确认",
        "detail": "详情",
        "search": "搜索...",
        "select_first": "请先选择一条记录",
        "lang_change_note": "语言变更将在重新打开设置窗口后生效。",
    },
    "en": {
        # ── Overlay ──
        "recording": "🎤 Recording... {hotkey}=done  {cancel}=cancel",
        "recognizing": "⏳ Recognizing...",
        "refining": "✍️ Refining...",
        "cancelled": "🚫 Cancelled",
        "no_audio": "⚠️ No audio detected",
        "too_short": "⚠️ Too short",
        "no_speech": "⚠️ No speech detected",
        "error": "❌ Error",
        "ready": "🟢 Press {hotkey} to record",
        "loading": "⏳ Loading model...",
        "loading_asr": "⏳ ASR model loading...",
        "loading_llm": "⏳ LLM loading...",
        "model_not_ready": "⏳ Model still loading...",
        "pasted": "📋 Pasted",
        "copied": "📋 Copied",
        "processing": "⏳ Still processing...",

        # ── Tray ──
        "recent": "── Recent ──",
        "history": "📜 History",
        "settings": "⚙️ Settings",
        "quit": "Quit",

        # ── Settings ──
        "settings_title": "TalkRefine Settings",
        "tab_general": "General",
        "tab_asr": "Speech Recognition",
        "tab_llm": "LLM Refinement",
        "tab_output": "Output",
        "ui_language": "UI Language",
        "autostart": "Start on system boot",
        "record_hotkey": "Record Hotkey",
        "cancel_key": "Cancel Key",
        "recognition_lang": "Recognition Language",
        "asr_model": "Recognition Model",
        "device": "Device",
        "enable_llm": "Enable LLM Refinement",
        "provider": "Provider",
        "endpoint": "Endpoint",
        "detect": "Detect",
        "model": "Model",
        "refresh": "Refresh",
        "api_key": "API Key",
        "prompt": "Prompt",
        "prompt_presets": "Presets",
        "general_preset": "General",
        "meeting_preset": "Meeting",
        "code_preset": "Code",
        "temperature": "Temperature",
        "auto_paste": "Auto-paste at cursor",
        "preserve_clipboard": "Restore clipboard after paste",
        "save": "💾 Save",
        "cancel": "Cancel",
        "auto_detect": "Auto",
        "chinese": "Chinese",
        "hotkey_conflict": "⚠️ May conflict with input method",
        "save_success": "Saved",
        "save_msg": "Config applied. ASR model changes will auto-restart.",
        "endpoint_ok": "✅ Connected",
        "endpoint_fail": "❌ Failed",
        "restore_default": "🔄 Restore Default",
        "recommended_cn": "Best for Chinese",
        "install_more": "📦 Install More Engines",

        # ── History ──
        "history_title": "TalkRefine History",
        "time_col": "Time",
        "duration_col": "Duration",
        "raw_col": "Raw Text",
        "refined_col": "Refined Text",
        "copy_refined": "📋 Copy Refined",
        "copy_raw": "📋 Copy Raw",
        "clear_history": "🗑️ Clear All",
        "clear_confirm": "Clear all history?",
        "confirm": "Confirm",
        "detail": "Detail",
        "search": "Search...",
        "select_first": "Please select an entry first",
        "lang_change_note": "Language change takes effect after reopening settings.",
    },
}


def get_strings(lang: str = "zh") -> dict:
    """Get the string dictionary for a language."""
    if lang not in _STRINGS:
        lang = "zh"
    return _STRINGS[lang]


def validate_strings():
    """Check that all languages have the same keys. Returns list of issues."""
    issues = []
    langs = list(_STRINGS.keys())
    if len(langs) < 2:
        return issues

    base_keys = set(_STRINGS[langs[0]].keys())
    for lang in langs[1:]:
        lang_keys = set(_STRINGS[lang].keys())
        missing = base_keys - lang_keys
        extra = lang_keys - base_keys
        for k in sorted(missing):
            issues.append(f"[{lang}] missing key: {k}")
        for k in sorted(extra):
            issues.append(f"[{lang}] extra key: {k}")
    return issues
