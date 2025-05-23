"""
音频工具模块
===========
提供音频处理相关的工具函数
"""

import numpy as np
import sounddevice as sd
import wave
import io
import time
from typing import List, Tuple, Optional, Dict
from scipy import signal
import threading


class AudioDeviceManager:
    """音频设备管理器"""

    @staticmethod
    def list_audio_devices() -> List[Dict]:
        """列出所有可用的音频设备"""
        devices = []
        try:
            device_list = sd.query_devices()
            for i, device in enumerate(device_list):
                devices.append({
                    'id': i,
                    'name': device['name'],
                    'max_input_channels': device['max_input_channels'],
                    'max_output_channels': device['max_output_channels'],
                    'default_samplerate': device['default_samplerate'],
                    'hostapi': device['hostapi']
                })
        except Exception as e:
            print(f"获取音频设备列表失败: {e}")

        return devices

    @staticmethod
    def get_default_input_device() -> Optional[Dict]:
        """获取默认输入设备信息"""
        try:
            device_id = sd.default.device[0]  # 输入设备
            if device_id is not None:
                device_info = sd.query_devices(device_id)
                return {
                    'id': device_id,
                    'name': device_info['name'],
                    'channels': device_info['max_input_channels'],
                    'samplerate': device_info['default_samplerate']
                }
        except Exception as e:
            print(f"获取默认输入设备失败: {e}")

        return None

    @staticmethod
    def test_audio_device(device_id: int, duration: float = 2.0, samplerate: int = 16000) -> bool:
        """测试音频设备是否正常工作"""
        try:
            # 录制测试
            print(f"测试设备 {device_id}，录制 {duration} 秒...")
            audio_data = sd.rec(
                int(duration * samplerate),
                samplerate=samplerate,
                channels=1,
                device=device_id,
                dtype='float32'
            )
            sd.wait()

            # 检查是否有音频信号
            rms = np.sqrt(np.mean(audio_data ** 2))
            if rms > 0.001:  # 有声音信号
                print(f"设备测试成功，音量RMS: {rms:.4f}")
                return True
            else:
                print("设备测试失败：未检测到音频信号")
                return False

        except Exception as e:
            print(f"设备测试失败: {e}")
            return False


class AudioProcessor:
    """音频处理器"""

    @staticmethod
    def normalize_audio(audio_data: np.ndarray, target_rms: float = 0.1) -> np.ndarray:
        """归一化音频数据"""
        current_rms = np.sqrt(np.mean(audio_data ** 2))
        if current_rms > 0:
            scale_factor = target_rms / current_rms
            return audio_data * scale_factor
        return audio_data

    @staticmethod
    def remove_silence(audio_data: np.ndarray, threshold: float = 0.01,
                       sample_rate: int = 16000) -> np.ndarray:
        """移除音频开头和结尾的静音部分"""
        # 计算音频能量
        frame_length = int(sample_rate * 0.025)  # 25ms frame
        hop_length = int(sample_rate * 0.01)  # 10ms hop

        energy = []
        for i in range(0, len(audio_data) - frame_length, hop_length):
            frame = audio_data[i:i + frame_length]
            energy.append(np.sum(frame ** 2))

        energy = np.array(energy)

        # 找到非静音部分
        non_silent = energy > threshold
        if not np.any(non_silent):
            return audio_data

        # 找到开始和结束位置
        start_frame = np.argmax(non_silent)
        end_frame = len(non_silent) - np.argmax(non_silent[::-1]) - 1

        start_sample = start_frame * hop_length
        end_sample = min((end_frame + 1) * hop_length + frame_length, len(audio_data))

        return audio_data[start_sample:end_sample]

    @staticmethod
    def apply_bandpass_filter(audio_data: np.ndarray, lowcut: float = 80,
                              highcut: float = 8000, sample_rate: int = 16000) -> np.ndarray:
        """应用带通滤波器"""
        nyquist = sample_rate / 2
        low = lowcut / nyquist
        high = highcut / nyquist

        b, a = signal.butter(4, [low, high], btype='band')
        filtered_audio = signal.filtfilt(b, a, audio_data)

        return filtered_audio

    @staticmethod
    def reduce_noise(audio_data: np.ndarray, noise_factor: float = 0.1) -> np.ndarray:
        """简单的噪声抑制"""
        # 计算音频的均值和标准差
        mean_amplitude = np.mean(np.abs(audio_data))

        # 创建噪声阈值
        threshold = mean_amplitude * noise_factor

        # 应用软阈值
        processed_audio = np.where(
            np.abs(audio_data) > threshold,
            audio_data,
            audio_data * (np.abs(audio_data) / threshold) ** 2
        )

        return processed_audio

    @staticmethod
    def chunk_audio(audio_data: np.ndarray, chunk_size: int,
                    overlap: int = 0) -> List[np.ndarray]:
        """将音频分块"""
        chunks = []
        step = chunk_size - overlap

        for i in range(0, len(audio_data) - chunk_size + 1, step):
            chunk = audio_data[i:i + chunk_size]
            chunks.append(chunk)

        # 处理最后不完整的块
        if len(audio_data) % step != 0:
            last_chunk = audio_data[-chunk_size:]
            if len(last_chunk) == chunk_size:
                chunks.append(last_chunk)

        return chunks


class AudioRecorder:
    """音频录制器"""

    def __init__(self, sample_rate: int = 16000, channels: int = 1,
                 chunk_duration: float = 0.1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration = chunk_duration
        self.chunk_size = int(sample_rate * chunk_duration)

        self.is_recording = False
        self.audio_data = []
        self.stream = None
        self.record_thread = None

    def start_recording(self, device_id: Optional[int] = None) -> bool:
        """开始录制"""
        if self.is_recording:
            return True

        try:
            self.audio_data = []
            self.is_recording = True

            # 启动录制线程
            self.record_thread = threading.Thread(
                target=self._record_thread,
                args=(device_id,)
            )
            self.record_thread.daemon = True
            self.record_thread.start()

            return True

        except Exception as e:
            print(f"启动录制失败: {e}")
            self.is_recording = False
            return False

    def stop_recording(self) -> np.ndarray:
        """停止录制并返回音频数据"""
        if not self.is_recording:
            return np.array([])

        self.is_recording = False

        # 等待录制线程结束
        if self.record_thread and self.record_thread.is_alive():
            self.record_thread.join(timeout=2.0)

        # 停止音频流
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
            self.stream = None

        # 合并音频数据
        if self.audio_data:
            return np.concatenate(self.audio_data)
        else:
            return np.array([])

    def _record_thread(self, device_id: Optional[int]):
        """录制线程"""
        try:
            def audio_callback(indata, frames, time, status):
                if status:
                    print(f"录制状态: {status}")
                if self.is_recording:
                    self.audio_data.append(indata.copy().flatten())

            self.stream = sd.InputStream(
                callback=audio_callback,
                device=device_id,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype='float32',
                blocksize=self.chunk_size
            )

            self.stream.start()

            while self.is_recording:
                time.sleep(0.1)

        except Exception as e:
            print(f"录制线程错误: {e}")
            self.is_recording = False


class AudioFileManager:
    """音频文件管理器"""

    @staticmethod
    def save_wav(audio_data: np.ndarray, filename: str, sample_rate: int = 16000):
        """保存音频为WAV文件"""
        try:
            # 确保数据在正确的范围内
            if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
                # 浮点数据，转换为16位整数
                audio_data = np.clip(audio_data, -1.0, 1.0)
                audio_data = (audio_data * 32767).astype(np.int16)

            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16位
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())

            print(f"音频已保存: {filename}")

        except Exception as e:
            print(f"保存音频文件失败: {e}")

    @staticmethod
    def load_wav(filename: str) -> Tuple[np.ndarray, int]:
        """加载WAV文件"""
        try:
            with wave.open(filename, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                audio_data = wav_file.readframes(n_frames)

                # 转换为numpy数组
                audio_array = np.frombuffer(audio_data, dtype=np.int16)

                # 转换为浮点数
                audio_array = audio_array.astype(np.float32) / 32767.0

                return audio_array, sample_rate

        except Exception as e:
            print(f"加载音频文件失败: {e}")
            return np.array([]), 0

    @staticmethod
    def audio_to_bytes(audio_data: np.ndarray, sample_rate: int = 16000) -> bytes:
        """将音频数据转换为字节流"""
        try:
            # 转换为16位整数
            if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
                audio_data = np.clip(audio_data, -1.0, 1.0)
                audio_data = (audio_data * 32767).astype(np.int16)

            # 创建WAV格式的字节流
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())

            return buffer.getvalue()

        except Exception as e:
            print(f"音频转换为字节流失败: {e}")
            return b''


class AudioAnalyzer:
    """音频分析器"""

    @staticmethod
    def calculate_rms(audio_data: np.ndarray) -> float:
        """计算RMS（均方根）值"""
        return np.sqrt(np.mean(audio_data ** 2))

    @staticmethod
    def calculate_zcr(audio_data: np.ndarray) -> float:
        """计算过零率"""
        signs = np.sign(audio_data)
        return np.sum(np.abs(np.diff(signs))) / (2 * len(audio_data))

    @staticmethod
    def detect_voice_activity(audio_data: np.ndarray,
                              rms_threshold: float = 0.02,
                              zcr_threshold: float = 0.3) -> bool:
        """简单的语音活动检测"""
        rms = AudioAnalyzer.calculate_rms(audio_data)
        zcr = AudioAnalyzer.calculate_zcr(audio_data)

        # 语音通常有较高的RMS和适中的过零率
        return rms > rms_threshold and zcr < zcr_threshold

    @staticmethod
    def get_audio_features(audio_data: np.ndarray) -> Dict[str, float]:
        """获取音频特征"""
        return {
            'rms': AudioAnalyzer.calculate_rms(audio_data),
            'zcr': AudioAnalyzer.calculate_zcr(audio_data),
            'max_amplitude': np.max(np.abs(audio_data)),
            'mean_amplitude': np.mean(np.abs(audio_data)),
            'std_amplitude': np.std(audio_data),
            'duration': len(audio_data) / 16000.0  # 假设16kHz采样率
        }