import sys
import json
import os
import time
import threading
import queue
from datetime import datetime

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import speech_recognition as sr
import psutil
import keyboard
import pyttsx3


class KeyboardLayoutWidget(QWidget):
    """A widget showing a keyboard layout for key selection"""
    def __init__(self, parent=None, callback=None):
        super().__init__(parent)
        self.callback = callback
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # Create keyboard grid
        keys_layout = QGridLayout()
        
        # First row
        row1 = ['Esc', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12']
        for i, key in enumerate(row1):
            btn = QPushButton(key)
            btn.clicked.connect(lambda _, k=key: self.key_selected(k))
            keys_layout.addWidget(btn, 0, i)
        
        # Second row
        row2 = ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'Backspace']
        for i, key in enumerate(row2):
            btn = QPushButton(key)
            btn.clicked.connect(lambda _, k=key: self.key_selected(k))
            keys_layout.addWidget(btn, 1, i)
        
        # Third row
        row3 = ['Tab', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', '\\']
        for i, key in enumerate(row3):
            btn = QPushButton(key)
            btn.clicked.connect(lambda _, k=key: self.key_selected(k))
            keys_layout.addWidget(btn, 2, i)
        
        # Fourth row
        row4 = ['Caps', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', "'", 'Enter']
        for i, key in enumerate(row4):
            btn = QPushButton(key)
            btn.clicked.connect(lambda _, k=key: self.key_selected(k))
            keys_layout.addWidget(btn, 3, i)
        
        # Fifth row
        row5 = ['Shift', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/', 'Shift']
        for i, key in enumerate(row5):
            btn = QPushButton(key)
            btn.clicked.connect(lambda _, k=key: self.key_selected(k))
            keys_layout.addWidget(btn, 4, i)
        
        # Sixth row
        row6 = ['Ctrl', 'Win', 'Alt', 'Space', 'Alt', 'Win', 'Menu', 'Ctrl']
        col = 0
        for key in row6:
            btn = QPushButton(key)
            btn.clicked.connect(lambda _, k=key: self.key_selected(k))
            if key == 'Space':
                keys_layout.addWidget(btn, 5, col, 1, 3)  # Space takes 3 columns
                col += 2  # Because we added one extra column
            else:
                keys_layout.addWidget(btn, 5, col)
            col += 1
        
        layout.addLayout(keys_layout)
        self.setLayout(layout)
    
    def key_selected(self, key):
        if self.callback:
            self.callback(key)


class ActionItemWidget(QWidget):
    """Widget representing a single action item in the action list"""
    def __init__(self, action_type, parent_list_widget=None):
        super().__init__()
        self.action_type = action_type
        self.parent_list_widget = parent_list_widget
        self.initUI()
    
    def initUI(self):
        layout = QHBoxLayout()
        
        # Add label for action type
        self.type_label = QLabel(self.action_type)
        self.type_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.type_label)
        
        # Add specific widgets based on action type
        if self.action_type == "если активна программа":
            self.process_combo = QComboBox()
            self.update_process_list()
            layout.addWidget(QLabel("Процесс:"))
            layout.addWidget(self.process_combo)
            
        elif self.action_type == "если запущена программа":
            self.process_combo = QComboBox()
            self.update_process_list()
            layout.addWidget(QLabel("Процесс:"))
            layout.addWidget(self.process_combo)
            
        elif self.action_type == "открыть файл или программу":
            self.file_button = QPushButton("Обзор...")
            self.file_path_label = QLabel("Файл не выбран")
            self.file_button.clicked.connect(self.select_file)
            layout.addWidget(self.file_path_label)
            layout.addWidget(self.file_button)
            
        elif self.action_type == "закрыть программу":
            self.process_combo = QComboBox()
            self.update_process_list()
            layout.addWidget(QLabel("Процесс:"))
            layout.addWidget(self.process_combo)
            
        elif self.action_type == "сказать":
            self.text_input = QLineEdit()
            self.text_input.setPlaceholderText("Введите текст для произношения...")
            layout.addWidget(QLabel("Текст:"))
            layout.addWidget(self.text_input)
            
        elif self.action_type == "подождать":
            self.ms_input = QLineEdit()
            self.ms_input.setPlaceholderText("Миллисекунды...")
            self.ms_input.setValidator(QIntValidator(0, 100000))
            layout.addWidget(QLabel("Ожидание (мс):"))
            layout.addWidget(self.ms_input)
            
        elif self.action_type == "нажать клавишу":
            self.press_release_combo = QComboBox()
            self.press_release_combo.addItems(["Нажать", "Отжать"])
            self.key_input = QLineEdit()
            self.key_input.setPlaceholderText("Клавиша...")
            self.key_button = QPushButton("...")
            self.key_button.clicked.connect(self.select_key)
            layout.addWidget(QLabel("Действие:"))
            layout.addWidget(self.press_release_combo)
            layout.addWidget(QLabel("Клавиша:"))
            layout.addWidget(self.key_input)
            layout.addWidget(self.key_button)
        
        # Add stretch to push everything to the left
        layout.addStretch()
        
        self.setLayout(layout)
    
    def update_process_list(self):
        """Update the process combo box with currently running processes"""
        if hasattr(self, 'process_combo'):
            self.process_combo.clear()
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    self.process_combo.addItem(proc.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    
    def select_file(self):
        """Open file dialog to select a file"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл или программу")
        if file_path:
            self.file_path_label.setText(file_path)
    
    def select_key(self):
        """Open keyboard layout dialog to select a key"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Выберите клавишу")
        dialog_layout = QVBoxLayout()
        
        keyboard_widget = KeyboardLayoutWidget(callback=lambda key: self.set_key(key, dialog))
        dialog_layout.addWidget(keyboard_widget)
        
        dialog.setLayout(dialog_layout)
        dialog.exec_()
    
    def set_key(self, key, dialog):
        """Set the selected key and close dialog"""
        self.key_input.setText(key)
        dialog.close()
    
    def get_action_data(self):
        """Return the action data based on the current UI state"""
        if self.action_type == "если активна программа":
            return {"type": self.action_type, "process": self.process_combo.currentText()}
        elif self.action_type == "если запущена программа":
            return {"type": self.action_type, "process": self.process_combo.currentText()}
        elif self.action_type == "открыть файл или программу":
            return {"type": self.action_type, "file_path": self.file_path_label.text()}
        elif self.action_type == "закрыть программу":
            return {"type": self.action_type, "process": self.process_combo.currentText()}
        elif self.action_type == "сказать":
            return {"type": self.action_type, "text": self.text_input.text()}
        elif self.action_type == "подождать":
            return {"type": self.action_type, "ms": int(self.ms_input.text()) if self.ms_input.text().isdigit() else 0}
        elif self.action_type == "нажать клавишу":
            return {
                "type": self.action_type,
                "action": self.press_release_combo.currentText(),
                "key": self.key_input.text()
            }
        return {}


class EditorTab(QWidget):
    """Editor tab for managing voice commands and actions"""
    def __init__(self, log_callback=None):
        super().__init__()
        self.log_callback = log_callback
        self.commands = {}
        self.is_modified = False
        self.current_command = None
        self.initUI()
    
    def initUI(self):
        layout = QHBoxLayout()
        
        # Left side - Command list
        left_layout = QVBoxLayout()
        
        # Command input area
        input_layout = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Введите голосовую команду...")
        self.add_command_btn = QPushButton("✓")
        self.add_command_btn.clicked.connect(self.add_command)
        input_layout.addWidget(QLabel("Команда:"))
        input_layout.addWidget(self.command_input)
        input_layout.addWidget(self.add_command_btn)
        
        # Commands list
        self.commands_list = QListWidget()
        self.commands_list.itemClicked.connect(self.load_actions_for_command)
        self.commands_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.commands_list.model().rowsMoved.connect(self.on_commands_reordered)
        
        left_layout.addLayout(input_layout)
        left_layout.addWidget(QLabel("Голосовые команды:"))
        left_layout.addWidget(self.commands_list)
        
        # Right side - Actions editor
        right_layout = QVBoxLayout()
        
        # Actions list
        self.actions_list = QListWidget()
        self.actions_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.actions_list.model().rowsMoved.connect(self.on_actions_reordered)
        
        # Action type selector
        action_selector_layout = QHBoxLayout()
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems([
            "если активна программа",
            "если запущена программа", 
            "открыть файл или программу",
            "закрыть программу",
            "сказать",
            "подождать",
            "нажать клавишу"
        ])
        self.add_action_btn = QPushButton("Добавить действие")
        self.add_action_btn.clicked.connect(self.add_action)
        action_selector_layout.addWidget(QLabel("Действие:"))
        action_selector_layout.addWidget(self.action_type_combo)
        action_selector_layout.addWidget(self.add_action_btn)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾")
        self.save_btn.clicked.connect(self.save_commands)
        self.test_btn = QPushButton("▶")
        self.test_btn.clicked.connect(self.test_scenario)
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.test_btn)
        
        right_layout.addWidget(QLabel("Действия:"))
        right_layout.addLayout(action_selector_layout)
        right_layout.addWidget(self.actions_list)
        right_layout.addLayout(buttons_layout)
        
        # Combine both sides
        layout.addLayout(left_layout)
        layout.addLayout(right_layout)
        
        self.setLayout(layout)
        
        # Initially disable test button
        self.test_btn.setEnabled(False)
    
    def add_command(self):
        """Add a new command to the list"""
        command_text = self.command_input.text().strip()
        if command_text and command_text not in self.commands:
            self.commands[command_text] = []
            item = QListWidgetItem(command_text)
            self.commands_list.addItem(item)
            self.command_input.clear()
            self.is_modified = True
            self.save_btn.setEnabled(True)
    
    def load_actions_for_command(self, item):
        """Load actions for the selected command"""
        command_text = item.text()
        self.current_command = command_text
        self.actions_list.clear()
        
        if command_text in self.commands:
            for action_data in self.commands[command_text]:
                action_widget = ActionItemWidget(action_data['type'])
                
                # Set the values from saved data
                if action_data['type'] == "если активна программа":
                    idx = action_widget.process_combo.findText(action_data.get('process', ''))
                    if idx >= 0:
                        action_widget.process_combo.setCurrentIndex(idx)
                elif action_data['type'] == "если запущена программа":
                    idx = action_widget.process_combo.findText(action_data.get('process', ''))
                    if idx >= 0:
                        action_widget.process_combo.setCurrentIndex(idx)
                elif action_data['type'] == "открыть файл или программу":
                    action_widget.file_path_label.setText(action_data.get('file_path', 'Файл не выбран'))
                elif action_data['type'] == "закрыть программу":
                    idx = action_widget.process_combo.findText(action_data.get('process', ''))
                    if idx >= 0:
                        action_widget.process_combo.setCurrentIndex(idx)
                elif action_data['type'] == "сказать":
                    action_widget.text_input.setText(action_data.get('text', ''))
                elif action_data['type'] == "подождать":
                    action_widget.ms_input.setText(str(action_data.get('ms', 0)))
                elif action_data['type'] == "нажать клавишу":
                    action_widget.press_release_combo.setCurrentText(action_data.get('action', 'Нажать'))
                    action_widget.key_input.setText(action_data.get('key', ''))
                
                list_item = QListWidgetItem()
                list_item.setSizeHint(action_widget.sizeHint())
                self.actions_list.addItem(list_item)
                self.actions_list.setItemWidget(list_item, action_widget)
    
    def add_action(self):
        """Add a new action to the current command"""
        if not self.current_command:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите команду")
            return
            
        action_type = self.action_type_combo.currentText()
        
        action_widget = ActionItemWidget(action_type)
        list_item = QListWidgetItem()
        list_item.setSizeHint(action_widget.sizeHint())
        self.actions_list.addItem(list_item)
        self.actions_list.setItemWidget(list_item, action_widget)
        
        # Add to command data
        self.commands[self.current_command].append({"type": action_type})
        self.is_modified = True
        self.save_btn.setEnabled(True)
    
    def on_commands_reordered(self):
        """Handle reordering of commands"""
        self.is_modified = True
        self.save_btn.setEnabled(True)
    
    def on_actions_reordered(self):
        """Handle reordering of actions"""
        if self.current_command:
            self.update_actions_from_ui(self.current_command)
        self.is_modified = True
        self.save_btn.setEnabled(True)
    
    def update_actions_from_ui(self, command_text):
        """Update the actions data from UI"""
        actions = []
        for i in range(self.actions_list.count()):
            item = self.actions_list.item(i)
            widget = self.actions_list.itemWidget(item)
            if isinstance(widget, ActionItemWidget):
                actions.append(widget.get_action_data())
        self.commands[command_text] = actions
    
    def save_commands(self):
        """Save commands to file"""
        try:
            with open('commands.json', 'w', encoding='utf-8') as f:
                json.dump(self.commands, f, ensure_ascii=False, indent=2)
            self.is_modified = False
            self.save_btn.setEnabled(False)
            QMessageBox.information(self, "Сохранено", "Команды успешно сохранены!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить команды: {str(e)}")
    
    def test_scenario(self):
        """Test the current scenario"""
        if not self.current_command:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите команду для тестирования")
            return
        
        if self.current_command in self.commands:
            self.execute_actions(self.commands[self.current_command])
            if self.log_callback:
                self.log_callback(f"Тестирование сценария '{self.current_command}' завершено")
    
    def execute_actions(self, actions):
        """Execute a list of actions"""
        for action in actions:
            action_type = action['type']
            
            if action_type == "если активна программа":
                active_window = self.get_active_window_process()
                if active_window == action['process']:
                    continue  # Continue with next action
                else:
                    break  # Skip remaining actions
            elif action_type == "если запущена программа":
                if self.is_process_running(action['process']):
                    continue  # Continue with next action
                else:
                    break  # Skip remaining actions
            elif action_type == "открыть файл или программу":
                os.system(f'"{action["file_path"]}"')
            elif action_type == "закрыть программу":
                self.kill_process(action['process'])
            elif action_type == "сказать":
                self.speak_text(action['text'])
            elif action_type == "подождать":
                time.sleep(action['ms'] / 1000.0)
            elif action_type == "нажать клавишу":
                if action['action'] == "Нажать":
                    keyboard.press_and_release(action['key'])
                elif action['action'] == "Отжать":
                    keyboard.release(action['key'])
    
    def get_active_window_process(self):
        """Get the name of the currently active window process"""
        try:
            import pygetwindow as gw
            active_window = gw.getActiveWindow()
            if active_window:
                return active_window.title
        except ImportError:
            # Fallback method using psutil
            try:
                for proc in psutil.process_iter(['pid', 'name', 'status']):
                    if proc.info['status'] == 'running':
                        # On Linux, getting active window is complex, so we'll just return a placeholder
                        return "unknown"
            except:
                pass
        return "unknown"
    
    def is_process_running(self, process_name):
        """Check if a process is running"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] == process_name:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False
    
    def kill_process(self, process_name):
        """Kill a process by name"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] == process_name:
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    def speak_text(self, text):
        """Speak the given text"""
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except:
            print(f"Could not speak: {text}")


class SettingsTab(QWidget):
    """Settings tab for configuring the application"""
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # Theme settings
        theme_group = QGroupBox("Тема")
        theme_layout = QHBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Светлая", "Тёмная"])
        theme_layout.addWidget(QLabel("Выбор темы:"))
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)
        
        # Audio settings
        audio_group = QGroupBox("Запись голоса")
        audio_layout = QVBoxLayout()
        
        # Microphone selection
        mic_layout = QHBoxLayout()
        mic_layout.addWidget(QLabel("Микрофон:"))
        self.mic_combo = QComboBox()
        self.populate_microphones()
        mic_layout.addWidget(self.mic_combo)
        audio_layout.addLayout(mic_layout)
        
        # Hotkey toggle
        self.hotkey_toggle = QCheckBox("Запись только при зажатии LCtrl")
        self.hotkey_toggle.stateChanged.connect(self.toggle_hotkey)
        audio_layout.addWidget(self.hotkey_toggle)
        
        audio_group.setLayout(audio_layout)
        
        # Recognition service
        recognition_group = QGroupBox("Сервис распознавания голоса")
        rec_layout = QHBoxLayout()
        self.rec_service_combo = QComboBox()
        self.rec_service_combo.addItems(["Google"])  # Only Google for now
        self.rec_status_label = QLabel("Статус: Готов")
        rec_layout.addWidget(QLabel("Сервис:"))
        rec_layout.addWidget(self.rec_service_combo)
        rec_layout.addWidget(self.rec_status_label)
        recognition_group.setLayout(rec_layout)
        
        # Text-to-speech service
        tts_group = QGroupBox("Сервис произношения текста")
        tts_layout = QHBoxLayout()
        self.tts_service_combo = QComboBox()
        self.tts_service_combo.addItems(["Google"])  # Only Google for now
        self.tts_status_label = QLabel("Статус: Готов")
        tts_layout.addWidget(QLabel("Сервис:"))
        tts_layout.addWidget(self.tts_service_combo)
        tts_layout.addWidget(self.tts_status_label)
        tts_group.setLayout(tts_layout)
        
        # Add all groups to main layout
        layout.addWidget(theme_group)
        layout.addWidget(audio_group)
        layout.addWidget(recognition_group)
        layout.addWidget(tts_group)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def populate_microphones(self):
        """Populate the microphone selection combo box"""
        try:
            for device_index in sr.Microphone.list_microphone_names():
                self.mic_combo.addItem(device_index)
        except:
            self.mic_combo.addItem("Микрофон не найден")
    
    def toggle_hotkey(self, state):
        """Toggle hotkey functionality"""
        if state == Qt.Checked:
            # Show keyboard layout for selecting hotkey
            dialog = QDialog(self)
            dialog.setWindowTitle("Выберите клавишу для активации записи")
            dialog_layout = QVBoxLayout()
            
            keyboard_widget = KeyboardLayoutWidget(callback=lambda key: self.set_hotkey(key, dialog))
            dialog_layout.addWidget(keyboard_widget)
            
            dialog.setLayout(dialog_layout)
            dialog.exec_()
    
    def set_hotkey(self, key, dialog):
        """Set the hotkey and close dialog"""
        print(f"Hotkey set to: {key}")
        dialog.close()


class LogTab(QWidget):
    """Log tab for displaying voice recognition events"""
    def __init__(self):
        super().__init__()
        self.log_entries = []
        self.max_log_entries = 100
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # Create text area for logs
        self.log_text_area = QTextEdit()
        self.log_text_area.setReadOnly(True)
        
        # Clear button
        clear_btn = QPushButton("Очистить журнал")
        clear_btn.clicked.connect(self.clear_log)
        
        layout.addWidget(QLabel("Журнал событий:"))
        layout.addWidget(self.log_text_area)
        layout.addWidget(clear_btn)
        
        self.setLayout(layout)
    
    def add_log_entry(self, entry):
        """Add a new log entry"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"{timestamp} {entry}"
        
        self.log_entries.append(log_line)
        
        # Keep only the last max_log_entries
        if len(self.log_entries) > self.max_log_entries:
            self.log_entries.pop(0)
        
        # Update the display
        self.log_text_area.setPlainText("\n".join(self.log_entries))
    
    def clear_log(self):
        """Clear the log"""
        self.log_entries = []
        self.log_text_area.clear()


class VoiceThread(QThread):
    """Thread for handling voice recognition"""
    voice_detected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.running = False
        self.last_voice_time = time.time()
        self.voice_timeout = 1  # 1 second timeout between voice commands
        
    def run(self):
        """Main thread loop for voice recognition"""
        self.running = True
        while self.running:
            try:
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source)
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                    
                # Check if enough time has passed since last voice
                current_time = time.time()
                if current_time - self.last_voice_time > self.voice_timeout:
                    try:
                        text = self.recognizer.recognize_google(audio, language="ru-RU")
                        self.voice_detected.emit(text.lower())
                        self.last_voice_time = current_time
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError:
                        pass
            except:
                # Timeout occurred, continue listening
                pass
            time.sleep(0.1)
    
    def stop(self):
        """Stop the voice recognition thread"""
        self.running = False


class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SchVoice v0.01")
        self.setGeometry(100, 100, 1000, 700)
        
        # Create central widget and tab widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.log_tab = LogTab()
        self.editor_tab = EditorTab(log_callback=self.log_tab.add_log_entry)
        self.settings_tab = SettingsTab()
        
        # Add tabs to tab widget
        self.tab_widget.addTab(self.editor_tab, "Редактор")
        self.tab_widget.addTab(self.settings_tab, "Настройки")
        self.tab_widget.addTab(self.log_tab, "Журнал")
        
        layout.addWidget(self.tab_widget)
        
        # Load existing commands
        self.load_commands()
        
        # Start voice recognition thread
        self.voice_thread = VoiceThread()
        self.voice_thread.voice_detected.connect(self.handle_voice_command)
        self.voice_thread.start()
        
        # Add status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Готов к распознаванию команд")
    
    def handle_voice_command(self, text):
        """Handle recognized voice command"""
        log_msg = f"пользователь сказал: {text}"
        
        # Check if the command exists in our list
        commands = self.get_commands()
        matched_command = None
        
        for cmd in commands:
            if cmd.lower() == text:
                matched_command = cmd
                break
        
        if matched_command:
            log_msg += f" - команда найдена, запуск сценария '{matched_command}'"
            self.log_tab.add_log_entry(log_msg)
            
            # Execute the corresponding actions
            command_actions = commands[matched_command]
            self.editor_tab.execute_actions(command_actions)
        else:
            log_msg += " - команда не найдена, пропуск"
            self.log_tab.add_log_entry(log_msg)
    
    def get_commands(self):
        """Get loaded commands"""
        try:
            with open('commands.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def load_commands(self):
        """Load commands from file"""
        try:
            with open('commands.json', 'r', encoding='utf-8') as f:
                commands = json.load(f)
                # Populate the commands list in the editor
                for command in commands:
                    item = QListWidgetItem(command)
                    self.editor_tab.commands_list.addItem(item)
                self.editor_tab.commands = commands
        except FileNotFoundError:
            pass  # File doesn't exist yet, that's OK
    
    def closeEvent(self, event):
        """Clean up when closing the application"""
        if self.voice_thread:
            self.voice_thread.stop()
            self.voice_thread.wait()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()