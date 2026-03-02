import sys
import json
import os
import time
import threading
import queue
import subprocess
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
import speech_recognition as sr
import psutil
import keyboard
import pyttsx3
import requests
import tempfile

app = Flask(__name__)

# Глобальные переменные для хранения состояния
scenarios = {}
log_entries = []
push_to_talk_enabled = False
active_microphone = 0
stt_service = "Google"
tts_service = "Google"
theme = "Светлая"

# Инициализация распознавания речи
recognizer = sr.Recognizer()
microphone = sr.Microphone()

class VoiceProcessor:
    def __init__(self):
        self.running = False
        self.thread = None
        self.push_to_talk = False
    
    def start_listening(self):
        if self.thread is None or not self.thread.is_alive():
            self.running = True
            self.thread = threading.Thread(target=self._listen_loop)
            self.thread.daemon = True
            self.thread.start()
    
    def stop_listening(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
    
    def _listen_loop(self):
        while self.running:
            try:
                if self.push_to_talk:
                    # Ждем нажатия LCtrl
                    if keyboard.is_pressed('left ctrl'):
                        with microphone as source:
                            # Пока нажата клавиша - записываем
                            while keyboard.is_pressed('left ctrl') and self.running:
                                try:
                                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                                    text = recognizer.recognize_google(audio, language="ru-RU")
                                    self._process_recognized_text(text)
                                except sr.WaitTimeoutError:
                                    continue
                                except sr.UnknownValueError:
                                    continue
                                except sr.RequestError:
                                    continue
                                time.sleep(0.1)
                else:
                    with microphone as source:
                        recognizer.adjust_for_ambient_noise(source)
                        try:
                            audio = recognizer.listen(source, timeout=2, phrase_time_limit=5)
                            text = recognizer.recognize_google(audio, language="ru-RU")
                            self._process_recognized_text(text)
                        except sr.WaitTimeoutError:
                            continue
                        except sr.UnknownValueError:
                            continue
                        except sr.RequestError:
                            continue
                    
                    # Пауза перед следующей попыткой
                    time.sleep(1)
            except Exception as e:
                print(f"Ошибка в потоке распознавания: {e}")
                time.sleep(1)
    
    def _process_recognized_text(self, text):
        # Логируем распознанный текст
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entries.append({
            'time': timestamp,
            'message': f"пользователь сказал: {text}"
        })
        
        # Проверяем, есть ли такая команда
        found = False
        for command, actions in scenarios.items():
            if text.lower().strip() == command.lower().strip():
                log_entries.append({
                    'time': timestamp,
                    'message': f"команда найдена, запуск сценария '{command}'"
                })
                self._execute_actions(actions)
                found = True
                break
        
        if not found:
            log_entries.append({
                'time': timestamp,
                'message': "команда не найдена, пропуск"
            })
    
    def _execute_actions(self, actions):
        for action_data in actions:
            action_type = action_data['type']
            params = action_data['params']
            
            if action_type == "если активна программа":
                active_window = self._get_active_window_process()
                if active_window and active_window.lower() == params['process'].lower():
                    continue  # Условие выполнено, продолжаем
                else:
                    break  # Условие не выполнено, прерываем цепочку
            elif action_type == "если запущена программа":
                if self._is_process_running(params['process']):
                    continue  # Условие выполнено, продолжаем
                else:
                    break  # Условие не выполнено, прерываем цепочку
            elif action_type == "открыть файл или программу":
                self._open_file_or_program(params['file_path'])
            elif action_type == "закрыть программу":
                self._close_program(params['process'])
            elif action_type == "сказать":
                self._speak_text(params['text'])
            elif action_type == "подождать":
                time.sleep(params['ms'] / 1000.0)
            elif action_type == "нажать клавишу":
                self._press_key(params['key'], params['state'])
    
    def _get_active_window_process(self):
        """Получение имени активного процесса (заглушка для Linux)"""
        try:
            result = subprocess.run(['xdotool', 'getwindowfocus', '-f', '--name'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # Если xdotool недоступен, возвращаем None
        return None
    
    def _is_process_running(self, process_name):
        """Проверка, запущен ли процесс"""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == process_name.lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False
    
    def _open_file_or_program(self, file_path):
        """Открытие файла или программы"""
        try:
            subprocess.Popen([file_path], start_new_session=True)
        except Exception as e:
            print(f"Ошибка при открытии файла: {e}")
    
    def _close_program(self, process_name):
        """Закрытие программы"""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == process_name.lower():
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    def _speak_text(self, text):
        """Озвучивание текста"""
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"Ошибка при озвучивании: {e}")
    
    def _press_key(self, key, state):
        """Нажатие клавиши"""
        if state == "Нажать":
            keyboard.press(key)
        elif state == "Отжать":
            keyboard.release(key)
        elif state == "Нажать и отжать":
            keyboard.press_and_release(key)

voice_processor = VoiceProcessor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scenarios')
def get_scenarios():
    return jsonify(scenarios)

@app.route('/api/scenarios', methods=['POST'])
def save_scenarios():
    global scenarios
    scenarios = request.json
    # Сохраняем в файл
    with open('scenarios.json', 'w', encoding='utf-8') as f:
        json.dump(scenarios, f, ensure_ascii=False, indent=2)
    return jsonify({'status': 'success'})

@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify({
        'theme': theme,
        'push_to_talk': push_to_talk_enabled,
        'microphone': active_microphone,
        'stt_service': stt_service,
        'tts_service': tts_service
    })

@app.route('/api/settings', methods=['POST'])
def update_settings():
    global theme, push_to_talk_enabled, active_microphone, stt_service, tts_service
    data = request.json
    theme = data.get('theme', theme)
    push_to_talk_enabled = data.get('push_to_talk', push_to_talk_enabled)
    active_microphone = data.get('microphone', active_microphone)
    stt_service = data.get('stt_service', stt_service)
    tts_service = data.get('tts_service', tts_service)
    voice_processor.push_to_talk = push_to_talk_enabled
    return jsonify({'status': 'success'})

@app.route('/api/log')
def get_log():
    return jsonify(log_entries[-100:])  # последние 100 записей

@app.route('/api/log/clear', methods=['POST'])
def clear_log():
    global log_entries
    log_entries = []
    return jsonify({'status': 'success'})

@app.route('/api/processes')
def get_processes():
    processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            processes.append(proc.info['name'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return jsonify(processes)

@app.route('/api/microphones')
def get_microphones():
    microphones = []
    for i in range(sr.Microphone.list_working_microphones()):
        microphones.append(f"Микрофон {i}")
    return jsonify(microphones)

@app.route('/api/test_scenario/<command>', methods=['POST'])
def test_scenario(command):
    if command in scenarios:
        actions = scenarios[command]
        # Выполняем действия в отдельном потоке
        thread = threading.Thread(target=voice_processor._execute_actions, args=(actions,))
        thread.daemon = True
        thread.start()
        return jsonify({'status': 'started'})
    return jsonify({'status': 'not_found'}), 404

@app.route('/api/services/status')
def check_services_status():
    # Проверяем Google STT
    stt_status = "Не проверен"
    try:
        test_audio = sr.AudioData(b'', 16000, 2)  # пустые данные для теста
        recognizer.recognize_google(test_audio)
        stt_status = "Доступен"
    except:
        stt_status = "Недоступен"

    # Проверяем Google TTS
    tts_status = "Не проверен"
    try:
        response = requests.get("https://translate.google.com", timeout=5)
        if response.status_code == 200:
            tts_status = "Доступен"
        else:
            tts_status = "Недоступен"
    except:
        tts_status = "Недоступен"
    
    return jsonify({
        'stt_status': stt_status,
        'tts_status': tts_status
    })

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

def load_scenarios():
    global scenarios
    if os.path.exists('scenarios.json'):
        with open('scenarios.json', 'r', encoding='utf-8') as f:
            scenarios = json.load(f)

if __name__ == '__main__':
    load_scenarios()
    voice_processor.start_listening()
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    finally:
        voice_processor.stop_listening()