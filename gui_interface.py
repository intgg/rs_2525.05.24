"""
实时语音翻译系统 - 图形用户界面
===============================
基于tkinter的可视化界面，支持设备选择、语音参数调节等功能
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import asyncio
import threading
import sys
import os
from typing import Dict, List, Optional
import sounddevice as sd

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.pipeline import RealTimeTranslationPipeline
from config.settings import config
from utils.audio_utils import AudioDeviceManager
from utils.logger import get_logger


class TranslationGUI:
    """实时语音翻译图形界面"""
    
    def __init__(self):
        """初始化GUI"""
        self.logger = get_logger("gui")
        
        # 翻译管道
        self.pipeline = RealTimeTranslationPipeline()
        self.is_initialized = False
        self.is_translating = False
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("🎙️ 实时语音翻译系统")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # 设置样式
        self.setup_styles()
        
        # 创建界面元素
        self.create_widgets()
        
        # 设置回调
        self.setup_callbacks()
        
        # 初始化数据
        self.load_devices()
        self.load_languages()
        
        # 异步任务
        self.async_loop = None
        self.async_thread = None
        
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置样式
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 10, 'bold'))
        style.configure('Success.TButton', foreground='green')
        style.configure('Danger.TButton', foreground='red')
        
    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 创建各个区域
        self.create_header(main_frame)
        self.create_language_settings(main_frame)
        self.create_device_settings(main_frame)
        self.create_tts_settings(main_frame)
        self.create_control_panel(main_frame)
        self.create_display_area(main_frame)
        self.create_status_bar(main_frame)
        
    def create_header(self, parent):
        """创建标题区域"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="🎙️ 实时语音翻译系统", style='Title.TLabel')
        title_label.pack()
        
        subtitle_label = ttk.Label(header_frame, text="基于 FunASR + Transformers + Edge-TTS")
        subtitle_label.pack()
        
    def create_language_settings(self, parent):
        """创建语言设置区域"""
        lang_frame = ttk.LabelFrame(parent, text="🌍 语言设置", padding="5")
        lang_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        lang_frame.columnconfigure(1, weight=1)
        lang_frame.columnconfigure(3, weight=1)
        
        # 源语言
        ttk.Label(lang_frame, text="源语言:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.source_lang_var = tk.StringVar(value="zh")
        self.source_lang_combo = ttk.Combobox(lang_frame, textvariable=self.source_lang_var, 
                                            state="readonly", width=15)
        self.source_lang_combo.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        
        # 目标语言
        ttk.Label(lang_frame, text="目标语言:").grid(row=0, column=2, padx=(10, 5), sticky=tk.W)
        self.target_lang_var = tk.StringVar(value="en")
        self.target_lang_combo = ttk.Combobox(lang_frame, textvariable=self.target_lang_var,
                                            state="readonly", width=15)
        self.target_lang_combo.grid(row=0, column=3, padx=5, sticky=(tk.W, tk.E))
        
        # 绑定语言变化事件
        self.target_lang_combo.bind('<<ComboboxSelected>>', self.on_target_language_changed)
        
    def create_device_settings(self, parent):
        """创建设备设置区域"""
        device_frame = ttk.LabelFrame(parent, text="🎛️ 设备设置", padding="5")
        device_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        device_frame.columnconfigure(1, weight=1)
        device_frame.columnconfigure(3, weight=1)
        
        # 输入设备
        ttk.Label(device_frame, text="输入设备:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.input_device_var = tk.StringVar()
        self.input_device_combo = ttk.Combobox(device_frame, textvariable=self.input_device_var,
                                             state="readonly", width=25)
        self.input_device_combo.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        
        # 输出设备
        ttk.Label(device_frame, text="输出设备:").grid(row=0, column=2, padx=(10, 5), sticky=tk.W)
        self.output_device_var = tk.StringVar()
        self.output_device_combo = ttk.Combobox(device_frame, textvariable=self.output_device_var,
                                              state="readonly", width=25)
        self.output_device_combo.grid(row=0, column=3, padx=5, sticky=(tk.W, tk.E))
        
        # 刷新设备按钮
        refresh_btn = ttk.Button(device_frame, text="🔄 刷新设备", command=self.load_devices)
        refresh_btn.grid(row=1, column=0, pady=(5, 0), sticky=tk.W)
        
        # 测试设备按钮
        test_btn = ttk.Button(device_frame, text="🧪 测试设备", command=self.test_devices)
        test_btn.grid(row=1, column=1, pady=(5, 0), sticky=tk.W, padx=(5, 0))
        
    def create_tts_settings(self, parent):
        """创建TTS设置区域"""
        tts_frame = ttk.LabelFrame(parent, text="🔊 语音合成设置", padding="5")
        tts_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        tts_frame.columnconfigure(1, weight=1)
        
        # 音色选择
        ttk.Label(tts_frame, text="音色:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.voice_var = tk.StringVar()
        self.voice_combo = ttk.Combobox(tts_frame, textvariable=self.voice_var,
                                      state="readonly", width=30)
        self.voice_combo.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        
        # 试听按钮
        test_voice_btn = ttk.Button(tts_frame, text="🎵 试听", command=self.test_voice)
        test_voice_btn.grid(row=0, column=2, padx=(5, 0))
        
        # 语音参数调节
        params_frame = ttk.Frame(tts_frame)
        params_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        params_frame.columnconfigure(1, weight=1)
        params_frame.columnconfigure(3, weight=1)
        params_frame.columnconfigure(5, weight=1)
        
        # 语速
        ttk.Label(params_frame, text="语速:").grid(row=0, column=0, sticky=tk.W)
        self.rate_var = tk.StringVar(value="0")
        self.rate_scale = ttk.Scale(params_frame, from_=-50, to=50, variable=self.rate_var,
                                   orient=tk.HORIZONTAL, length=150)
        self.rate_scale.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        self.rate_label = ttk.Label(params_frame, text="0%")
        self.rate_label.grid(row=0, column=2, padx=(5, 15), sticky=tk.W)
        
        # 语调
        ttk.Label(params_frame, text="语调:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.pitch_var = tk.StringVar(value="0")
        self.pitch_scale = ttk.Scale(params_frame, from_=-50, to=50, variable=self.pitch_var,
                                    orient=tk.HORIZONTAL, length=150)
        self.pitch_scale.grid(row=1, column=1, padx=5, sticky=(tk.W, tk.E), pady=(5, 0))
        self.pitch_label = ttk.Label(params_frame, text="0Hz")
        self.pitch_label.grid(row=1, column=2, padx=(5, 15), sticky=tk.W, pady=(5, 0))
        
        # 音量
        ttk.Label(params_frame, text="音量:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.volume_var = tk.StringVar(value="0")
        self.volume_scale = ttk.Scale(params_frame, from_=-50, to=50, variable=self.volume_var,
                                     orient=tk.HORIZONTAL, length=150)
        self.volume_scale.grid(row=2, column=1, padx=5, sticky=(tk.W, tk.E), pady=(5, 0))
        self.volume_label = ttk.Label(params_frame, text="0%")
        self.volume_label.grid(row=2, column=2, padx=(5, 15), sticky=tk.W, pady=(5, 0))
        
        # 绑定滑块变化事件
        self.rate_scale.configure(command=self.update_rate_label)
        self.pitch_scale.configure(command=self.update_pitch_label)
        self.volume_scale.configure(command=self.update_volume_label)
        
    def create_control_panel(self, parent):
        """创建控制面板"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        # 初始化按钮
        self.init_btn = ttk.Button(control_frame, text="🚀 初始化系统", 
                                  command=self.initialize_system)
        self.init_btn.pack(side=tk.LEFT, padx=5)
        
        # 开始/停止按钮
        self.start_stop_btn = ttk.Button(control_frame, text="▶️ 开始翻译", 
                                        command=self.toggle_translation, state=tk.DISABLED)
        self.start_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 清空按钮
        clear_btn = ttk.Button(control_frame, text="🗑️ 清空显示", command=self.clear_display)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 设置按钮
        settings_btn = ttk.Button(control_frame, text="⚙️ 高级设置", command=self.show_settings)
        settings_btn.pack(side=tk.LEFT, padx=5)
        
    def create_display_area(self, parent):
        """创建显示区域"""
        display_frame = ttk.LabelFrame(parent, text="📺 实时显示", padding="5")
        display_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        display_frame.columnconfigure(0, weight=1)
        display_frame.columnconfigure(1, weight=1)
        display_frame.rowconfigure(1, weight=1)
        
        parent.rowconfigure(5, weight=1)
        
        # 源文本显示
        ttk.Label(display_frame, text="🎤 识别结果:", style='Header.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.source_text = scrolledtext.ScrolledText(display_frame, height=8, width=40,
                                                   wrap=tk.WORD, font=('Arial', 10))
        self.source_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # 翻译结果显示
        ttk.Label(display_frame, text="🌍 翻译结果:", style='Header.TLabel').grid(
            row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        self.target_text = scrolledtext.ScrolledText(display_frame, height=8, width=40,
                                                   wrap=tk.WORD, font=('Arial', 10))
        self.target_text.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        status_frame.columnconfigure(1, weight=1)
        
        # 状态指示器
        self.status_indicator = ttk.Label(status_frame, text="🔴", font=('Arial', 12))
        self.status_indicator.grid(row=0, column=0, padx=(0, 5))
        
        # 状态文本
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=1, sticky=tk.W)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, length=200)
        self.progress_bar.grid(row=0, column=2, padx=(10, 0))
        
    def setup_callbacks(self):
        """设置回调函数"""
        self.pipeline.add_status_callback(self.on_status_change)
        self.pipeline.add_text_callback(self.on_text_recognized)
        self.pipeline.add_translation_callback(self.on_translation_result)
        self.pipeline.add_error_callback(self.on_error)
        
    def load_devices(self):
        """加载音频设备"""
        try:
            devices = AudioDeviceManager.list_audio_devices()
            
            # 输入设备
            input_devices = [f"{d['id']}: {d['name']}" for d in devices 
                           if d['max_input_channels'] > 0]
            self.input_device_combo['values'] = input_devices
            
            # 输出设备  
            output_devices = [f"{d['id']}: {d['name']}" for d in devices
                            if d['max_output_channels'] > 0]
            self.output_device_combo['values'] = output_devices
            
            # 设置默认设备
            default_input = AudioDeviceManager.get_default_input_device()
            if default_input and input_devices:
                for device in input_devices:
                    if str(default_input['id']) in device:
                        self.input_device_var.set(device)
                        break
                        
            if output_devices:
                self.output_device_var.set(output_devices[0])
                
            self.update_status("设备列表已更新")
            
        except Exception as e:
            self.show_error(f"加载设备失败: {e}")
            
    def load_languages(self):
        """加载支持的语言"""
        languages = {
            "zh": "中文 (Chinese)",
            "en": "英语 (English)",
            "ja": "日语 (Japanese)", 
            "ko": "韩语 (Korean)",
            "fr": "法语 (French)",
            "de": "德语 (German)",
            "es": "西班牙语 (Spanish)",
            "ru": "俄语 (Russian)"
        }
        
        lang_values = [f"{code} - {name}" for code, name in languages.items()]
        
        self.source_lang_combo['values'] = lang_values
        self.target_lang_combo['values'] = lang_values
        
        # 设置默认值
        self.source_lang_var.set("zh - 中文 (Chinese)")
        self.target_lang_var.set("en - 英语 (English)")
        
        # 加载对应音色
        self.load_voices_for_language("en")
        
    def load_voices_for_language(self, language_code: str):
        """为指定语言加载音色"""
        def load_voices_async():
            try:
                if hasattr(self.pipeline, 'tts_module') and self.pipeline.tts_module:
                    # 如果TTS模块已初始化，直接获取音色
                    voices = self.pipeline.tts_module.get_voices_for_language(f"{language_code}-*")
                else:
                    # 否则创建临时TTS模块获取音色
                    from modules.text_to_speech import TextToSpeechModule
                    temp_tts = TextToSpeechModule()
                    
                    # 在新线程中运行异步操作
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(temp_tts.load_available_voices())
                    
                    # 获取指定语言的音色
                    all_voices = temp_tts.available_voices
                    voices = []
                    for locale, voice_list in all_voices.items():
                        if locale.startswith(language_code):
                            voices.extend(voice_list)
                    
                    loop.close()
                
                # 更新UI（需要在主线程中执行）
                self.root.after(0, self.update_voice_combo, voices)
                
            except Exception as e:
                self.root.after(0, self.show_error, f"加载音色失败: {e}")
        
        # 在后台线程中加载音色
        threading.Thread(target=load_voices_async, daemon=True).start()
        
    def update_voice_combo(self, voices):
        """更新音色下拉框"""
        if voices:
            voice_options = [f"{voice['name']} ({voice['gender']})" for voice in voices]
            self.voice_combo['values'] = voice_options
            if voice_options:
                self.voice_var.set(voice_options[0])
        else:
            self.voice_combo['values'] = []
            self.voice_var.set("")
            
    def on_target_language_changed(self, event=None):
        """目标语言改变时的处理"""
        target_lang = self.target_lang_var.get().split(' - ')[0]
        self.load_voices_for_language(target_lang)
        
    def update_rate_label(self, value):
        """更新语速标签"""
        self.rate_label.config(text=f"{int(float(value))}%")
        
    def update_pitch_label(self, value):
        """更新语调标签"""  
        self.pitch_label.config(text=f"{int(float(value))}Hz")
        
    def update_volume_label(self, value):
        """更新音量标签"""
        self.volume_label.config(text=f"{int(float(value))}%")
        
    def test_devices(self):
        """测试音频设备"""
        input_device = self.input_device_var.get()
        if not input_device:
            self.show_error("请先选择输入设备")
            return
            
        try:
            device_id = int(input_device.split(':')[0])
            self.update_status("正在测试设备...")
            
            def test_async():
                success = AudioDeviceManager.test_audio_device(device_id, duration=2.0)
                result_msg = "设备测试成功" if success else "设备测试失败"
                self.root.after(0, self.update_status, result_msg)
                
            threading.Thread(target=test_async, daemon=True).start()
            
        except Exception as e:
            self.show_error(f"设备测试失败: {e}")
            
    def test_voice(self):
        """试听音色"""
        voice = self.voice_var.get()
        if not voice:
            self.show_error("请先选择音色")
            return
            
        voice_name = voice.split(' (')[0]
        test_text = "Hello, this is a voice test." if 'en-' in voice_name else "你好，这是音色测试。"
        
        def test_voice_async():
            try:
                from modules.text_to_speech import TextToSpeechModule
                temp_tts = TextToSpeechModule()
                
                # 设置音色参数
                temp_tts.set_voice(voice_name)
                
                # 播放测试
                success = temp_tts.speak_immediate(test_text)
                result_msg = "试听完成" if success else "试听失败"
                self.root.after(0, self.update_status, result_msg)
                
            except Exception as e:
                self.root.after(0, self.show_error, f"试听失败: {e}")
                
        threading.Thread(target=test_voice_async, daemon=True).start()
        self.update_status("正在试听音色...")
        
    def initialize_system(self):
        """初始化系统"""
        if self.is_initialized:
            self.show_info("系统已经初始化")
            return
            
        # 获取语言设置
        source_lang = self.source_lang_var.get().split(' - ')[0]
        target_lang = self.target_lang_var.get().split(' - ')[0]
        
        self.update_status("正在初始化系统...")
        self.progress_var.set(0)
        self.init_btn.config(state=tk.DISABLED)
        
        def init_async():
            try:
                # 创建新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # 初始化管道
                success = loop.run_until_complete(
                    self.pipeline.initialize(source_lang, target_lang)
                )
                
                if success:
                    # 应用TTS设置
                    self.apply_tts_settings()
                    
                    self.root.after(0, self.on_initialization_success)
                else:
                    self.root.after(0, self.on_initialization_failed)
                    
                loop.close()
                
            except Exception as e:
                self.root.after(0, self.on_initialization_failed, str(e))
                
        threading.Thread(target=init_async, daemon=True).start()
        
    def apply_tts_settings(self):
        """应用TTS设置"""
        if not self.pipeline.tts_module:
            return
            
        try:
            # 设置音色
            voice = self.voice_var.get()
            if voice:
                voice_name = voice.split(' (')[0]
                self.pipeline.tts_module.set_voice(voice_name)
            
            # 设置语音参数
            rate = int(float(self.rate_var.get()))
            pitch = int(float(self.pitch_var.get()))
            volume = int(float(self.volume_var.get()))
            
            # 更新TTS配置
            self.pipeline.tts_module.tts_config.rate = f"{rate:+d}%"
            self.pipeline.tts_module.tts_config.pitch = f"{pitch:+d}Hz"
            self.pipeline.tts_module.tts_config.volume = f"{volume:+d}%"
            
        except Exception as e:
            self.show_error(f"应用TTS设置失败: {e}")
            
    def on_initialization_success(self):
        """初始化成功处理"""
        self.is_initialized = True
        self.status_indicator.config(text="🟡")
        self.update_status("系统初始化完成")
        self.progress_var.set(100)
        
        self.init_btn.config(state=tk.NORMAL, text="✅ 已初始化")
        self.start_stop_btn.config(state=tk.NORMAL)
        
    def on_initialization_failed(self, error_msg=None):
        """初始化失败处理"""
        self.status_indicator.config(text="🔴")
        self.update_status("初始化失败")
        self.progress_var.set(0)
        
        self.init_btn.config(state=tk.NORMAL)
        
        if error_msg:
            self.show_error(f"初始化失败: {error_msg}")
        else:
            self.show_error("系统初始化失败，请检查配置")
            
    def toggle_translation(self):
        """切换翻译状态"""
        if not self.is_initialized:
            self.show_error("请先初始化系统")
            return
            
        if self.is_translating:
            self.stop_translation()
        else:
            self.start_translation()
            
    def start_translation(self):
        """开始翻译"""
        # 应用设备设置
        self.apply_device_settings()
        
        # 应用TTS设置
        self.apply_tts_settings()
        
        success = self.pipeline.start_translation()
        
        if success:
            self.is_translating = True
            self.status_indicator.config(text="🟢")
            self.update_status("正在翻译...")
            self.start_stop_btn.config(text="⏹️ 停止翻译", style='Danger.TButton')
        else:
            self.show_error("启动翻译失败")
            
    def stop_translation(self):
        """停止翻译"""
        self.pipeline.stop_translation()
        
        self.is_translating = False
        self.status_indicator.config(text="🟡")
        self.update_status("翻译已停止")
        self.start_stop_btn.config(text="▶️ 开始翻译", style='TButton')
        
    def apply_device_settings(self):
        """应用设备设置"""
        try:
            # 获取选择的输入设备
            input_device = self.input_device_var.get()
            if input_device:
                device_id = int(input_device.split(':')[0])
                # 设置默认音频设备
                sd.default.device[0] = device_id
                
        except Exception as e:
            self.show_error(f"设备设置失败: {e}")
            
    def clear_display(self):
        """清空显示区域"""
        self.source_text.delete(1.0, tk.END)
        self.target_text.delete(1.0, tk.END)
        
    def show_settings(self):
        """显示高级设置"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("⚙️ 高级设置")
        settings_window.geometry("400x300")
        settings_window.resizable(False, False)
        
        # 模态窗口
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 音频设置标签页
        audio_frame = ttk.Frame(notebook)
        notebook.add(audio_frame, text="音频设置")
        
        # VAD设置
        vad_var = tk.BooleanVar(value=config.audio.use_vad)
        ttk.Checkbutton(audio_frame, text="启用语音端点检测 (VAD)", 
                       variable=vad_var).pack(anchor=tk.W, pady=5)
        
        # 标点设置
        punc_var = tk.BooleanVar(value=config.audio.use_punctuation)
        ttk.Checkbutton(audio_frame, text="启用标点恢复", 
                       variable=punc_var).pack(anchor=tk.W, pady=5)
        
        # 最大片段时长
        ttk.Label(audio_frame, text="最大片段时长 (秒):").pack(anchor=tk.W, pady=(10, 0))
        max_duration_var = tk.DoubleVar(value=config.audio.max_segment_duration_seconds)
        ttk.Scale(audio_frame, from_=3, to=15, variable=max_duration_var,
                 orient=tk.HORIZONTAL, length=300).pack(pady=5)
        
        # 翻译设置标签页
        trans_frame = ttk.Frame(notebook)
        notebook.add(trans_frame, text="翻译设置")
        
        # SimulTrans块大小
        ttk.Label(trans_frame, text="SimulTrans块大小:").pack(anchor=tk.W, pady=(10, 0))
        chunk_size_var = tk.IntVar(value=config.translation.chunk_size)
        ttk.Scale(trans_frame, from_=64, to=256, variable=chunk_size_var,
                 orient=tk.HORIZONTAL, length=300).pack(pady=5)
        
        # 保存按钮
        def save_settings():
            config.audio.use_vad = vad_var.get()
            config.audio.use_punctuation = punc_var.get()
            config.audio.max_segment_duration_seconds = max_duration_var.get()
            config.translation.chunk_size = chunk_size_var.get()
            
            self.show_info("设置已保存")
            settings_window.destroy()
            
        ttk.Button(settings_window, text="保存设置", command=save_settings).pack(pady=10)
        
    def on_status_change(self, status: str, data: dict):
        """状态变化处理"""
        self.root.after(0, self.update_status, status)
        
    def on_text_recognized(self, text: str, is_final: bool):
        """文本识别处理"""
        def update_text():
            if is_final:
                self.source_text.insert(tk.END, text + "\n")
            else:
                # 实时更新最后一行
                self.source_text.delete("end-1c linestart", "end-1c")
                self.source_text.insert(tk.END, text + "\n")
            
            self.source_text.see(tk.END)
            
        self.root.after(0, update_text)
        
    def on_translation_result(self, translation: str, is_final: bool):
        """翻译结果处理"""
        def update_translation():
            if is_final:
                self.target_text.insert(tk.END, translation + "\n")
            else:
                # 实时更新最后一行
                self.target_text.delete("end-1c linestart", "end-1c")
                self.target_text.insert(tk.END, translation + "\n")
            
            self.target_text.see(tk.END)
            
        self.root.after(0, update_translation)
        
    def on_error(self, error_msg: str):
        """错误处理"""
        self.root.after(0, self.show_error, error_msg)
        
    def update_status(self, status: str):
        """更新状态"""
        self.status_var.set(status)
        
    def show_error(self, message: str):
        """显示错误消息"""
        messagebox.showerror("错误", message)
        
    def show_info(self, message: str):
        """显示信息消息"""
        messagebox.showinfo("信息", message)
        
    def on_closing(self):
        """关闭窗口处理"""
        if self.is_translating:
            self.stop_translation()
            
        self.root.destroy()
        
    def run(self):
        """运行GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


def main():
    """主函数"""
    try:
        app = TranslationGUI()
        app.run()
    except Exception as e:
        print(f"启动GUI失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()