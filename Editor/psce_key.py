import configparser
import os
import tkinter as tk
import sys
import subprocess
import logging

class KeyManager:
    """
    ショートカットキーを管理するクラス。
    KeyMap.ini の読み込み・保存、およびキーイベントのバインディングとアクションの実行を担当。
    """
    def __init__(self, app):
        self.app = app
        self.config_path = os.path.join(self.app.utils.settings_dir, 'KeyMap.ini')
        self.key_map = configparser.ConfigParser()
        self.key_map.optionxform = str  # 大文字小文字を区別する
        
        # デフォルトのショートカットキー設定
        # Windows標準のショートカット（Ctrl+Cなど）との競合を避けるため、
        # 修飾キー(Ctrl, Alt, Shift)を組み合わせたり、ファンクションキーを使用することを推奨。
        self.default_map = {
            'SaveCurrentTab': '<Control-s>',           # 現在のタブの内容を保存
            'SaveAndExit': '<Control-Alt-F4>',               # 保存して終了
            'ExitNoSave': '<Alt-F4>',                    # 保存せずに終了 ※設定していなくてもAlt+F4でアプリはWindwsが閉じてくれる
            'RestartNoSave': '<Control-r>',             # 保存せずに再起動
            'SaveAndRestart': '<Control-Shift-R>',      # 保存して再起動
            'Undo': '<Control-Shift-Z>',                # 元に戻す (HistoryManager)
            'Redo': '<Control-Shift-Y>',                # やり直す (HistoryManager)
            'ToggleDebugSettings': '<Shift-F12>',             # Debug設定表示切替
        }
        
        # アクションの定義
        self.actions = {
            'SaveCurrentTab': self.action_save_current_tab,    # 現在のタブの内容を保存
            'SaveAndExit': self.action_save_and_exit,          # 保存して終了
            'ExitNoSave': self.action_exit_no_save,            # 保存せずに終了
            'RestartNoSave': self.action_restart_no_save,      # 保存せずに再起動
            'SaveAndRestart': self.action_save_and_restart,    # 保存して再起動
            'Undo': self.action_undo,                          # 元に戻す (HistoryManager)
            'Redo': self.action_redo,                          # やり直す (HistoryManager)
            'ToggleDebugSettings': self.action_toggle_debug,   # Debug設定表示切替
        }
        
        # キー設定を読み込む
        self.load_key_map()

    def load_key_map(self):
        # KeyMap.ini から設定を読み込み、ファイルが存在しない場合はデフォルト設定で作成。
        if not os.path.exists(self.config_path):
            self.create_default_key_map()
        # KeyMap.ini から設定を読み込む
        else:
            try:
                self.key_map.read(self.config_path, encoding='utf-8-sig')
                # 設定ファイルにセクションがない、またはキーが不足している場合は補完する
                if not self.key_map.has_section('Shortcuts'):
                    self.key_map.add_section('Shortcuts')
                
                changed = False
                
                # 古いキー名から新しいキー名への移行処理
                if self.key_map.has_option('Shortcuts', 'SaveGeneralSettings'):
                    # 古いキー設定を取得
                    old_key = self.key_map.get('Shortcuts', 'SaveGeneralSettings')
                    # 新しいキー名で設定
                    self.key_map.set('Shortcuts', 'SaveCurrentTab', old_key)
                    # 古いキー名を削除
                    self.key_map.remove_option('Shortcuts', 'SaveGeneralSettings')
                    changed = True
                
                # 不足しているキーを補完
                for action, default_key in self.default_map.items():
                    if not self.key_map.has_option('Shortcuts', action):
                        self.key_map.set('Shortcuts', action, default_key)
                        changed = True
                
                if changed:
                    self.save_key_map()
            except Exception as e:
                logging.error(f"Failed to load KeyMap.ini: {e}")
                self.create_default_key_map()

    def create_default_key_map(self):
        # デフォルトの設定で KeyMap.ini を作成
        self.key_map = configparser.ConfigParser()
        self.key_map.optionxform = str
        self.key_map.add_section('Shortcuts')
        for action, key in self.default_map.items():
            self.key_map.set('Shortcuts', action, key)
        self.save_key_map()

    def save_key_map(self):
        # 現在の設定を KeyMap.ini に保存
        try:
            with open(self.config_path, 'w', encoding='utf-8-sig') as f:
                self.key_map.write(f)
        except Exception as e:
            logging.error(f"Failed to save KeyMap.ini: {e}")

    def apply_shortcuts(self, root):
        # ルートウィンドウにショートカットキーをバインド
        # 既存のバインドを上書きして再設定（古いバインドを追跡して unbind するロジックではなく、シンプルに設定されたキーに対して bind を行う
        
        # キー設定がない場合は何もしない
        if not self.key_map.has_section('Shortcuts'):
            return

        for action, func in self.actions.items():
            key = self.key_map.get('Shortcuts', action, fallback='')
            if key:
                # tkinterのイベントバインド（ラムダ式で event 引数を受け取るようにしないとエラーになる）
                try:
                    root.bind(key, lambda event, f=func: f(event))
                except tk.TclError:
                    logging.error(f"Invalid key format: {key}")

    # --- Actions ---

    def action_save_current_tab(self, event=None):
        """現在のタブの内容を保存するアクション（タブ別処理）"""
        context = self.app.get_current_context()
        
        # KeyMapタブではショートカット無効化（キー入力と競合する可能性があるため）
        if context == 'key':
            return
        
        # コンテキストに応じて保存メソッドを呼び出す
        if context == 'general':
            if hasattr(self.app, 'general_tab'):
                self.app.general_tab.save_general_settings()
        elif context == 'profile':
            if hasattr(self.app, 'ui_profile'):
                self.app.ui_profile.save_profile()
        elif context == 'data':
            if hasattr(self.app, 'pose_data_tab'):
                self.app.pose_data_tab.save_pose_data()
        elif context == 'map':
            if hasattr(self.app, 'map_tab'):
                self.app.map_tab.save_map_entry()

    def action_save_and_exit(self, event=None):
        """現在のタブを保存して終了するアクション"""
        # 現在のタブを保存（SaveCurrentTabと同じロジック）
        self.action_save_current_tab()
        self.app.save_geometry()
        self.app.root.destroy()

    def action_exit_no_save(self, event=None):
        """保存せずに終了するアクション"""
        self.app.root.destroy()

    def action_restart_no_save(self, event=None):
        """保存せずに再起動するアクション"""
        self.restart_app()

    def action_save_and_restart(self, event=None):
        """現在のタブを保存して再起動するアクション"""
        try:
            # 現在のタブを保存（SaveCurrentTabと同じロジック）
            self.action_save_current_tab()
            self.app.save_geometry()
        except Exception as e:
            logging.error(f"Error saving before restart: {e}")
        self.restart_app()

    def action_undo(self, event=None):
        """元に戻すアクション"""
        context = self.app.get_current_context()
        if context:
            self.app.undo()

    def action_redo(self, event=None):
        """やり直すアクション"""
        context = self.app.get_current_context()
        if context:
            self.app.redo()
    
    def action_toggle_debug(self, event=None):
        """Debug設定の表示切替"""
        if hasattr(self.app, 'general_tab'):
            current = self.app.show_debug_var.get()
            new_value = not current
            self.app.show_debug_var.set(new_value)
            self.app.general_tab.toggle_debug_settings()

    def restart_app(self):
            """アプリケーションを再起動する内部メソッド（直接起動・デバッグ版）"""
            try:
                # 1. 実行ファイルのパス
                exe_path = sys.executable
                # 2. 環境変数のクリーンアップ
                # PyInstallerの環境変数が残っていると再起動後のアプリがクラッシュするため除去
                env = {}
                ignore_keys = {
                    'TCL_LIBRARY', 'TK_LIBRARY',
                    '_MEIPASS', '_MEIPASS2',
                    'PYTHONPATH', 'PYTHONHOME',
                }
                ignore_prefixes = ('_MEI', 'PYTHON', 'TCL', 'TK')
                
                for k, v in os.environ.items():
                    k_upper = k.upper()
                    if k_upper not in ignore_keys and not k_upper.startswith(ignore_prefixes):
                        env[k] = v
                # 3. 新しいプロセスを起動
                # creationflags=0x00000010 (CREATE_NEW_CONSOLE) で別コンソールとして分離
                if getattr(sys, 'frozen', False):
                    # EXEの場合
                    subprocess.Popen([exe_path], env=env, creationflags=0x00000010)
                else:
                    # 開発環境の場合
                    subprocess.Popen([exe_path] + sys.argv, env=env, creationflags=0x00000010)
            except Exception as e:
                # エラーが起きたらダイアログで表示
                import traceback
                err_msg = f"再起動に失敗しました:\n{e}\n{traceback.format_exc()}"
                tk.messagebox.showerror("Restart Error", err_msg)
                logging.error(err_msg)
                return  # 起動失敗時は終了しない
            # 4. 現在のプロセスを終了
            logging.info("Restarting... closing current process.")
            self.app.perform_cleanup()
            self.app.root.destroy()
            sys.exit(0)

if False:
    def restart_app(self):
        """VBScriptで再起動（環境変数を継承しない）"""
        import tempfile
        
        try:
            # 実行ファイル情報の取得
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                # 開発環境ではフォールバック
                logging.warning("VBS restart is only available in frozen mode")
                self._restart_fallback()
                return
            
            # VBScriptファイル生成
            vbs_path = os.path.join(tempfile.gettempdir(), "psce_restart.vbs")
            
            # VBScriptでプロセスを明示的に終了させる
            exe_name = os.path.basename(exe_path)
            vbs_content = f"""Set WshShell = CreateObject("WScript.Shell")
Set objWMIService = GetObject("winmgmts:\\\\.\\root\\cimv2")

' 対象プロセスを強制終了
Set colProcesses = objWMIService.ExecQuery("Select * from Win32_Process Where Name = '{exe_name}'")
For Each objProcess in colProcesses
    objProcess.Terminate()
Next

' プロセスが完全に終了し、MEIフォルダが削除されるまで待機
WScript.Sleep 3000

' 念のため、プロセスが本当に存在しないか確認
Do
    Set colProcesses = objWMIService.ExecQuery("Select * from Win32_Process Where Name = '{exe_name}'")
    If colProcesses.Count = 0 Then
        Exit Do
    End If
    WScript.Sleep 500
Loop

' さらに2秒待機（MEIフォルダの完全削除を確実にする）
WScript.Sleep 2000

' アプリを起動（完全にクリーンな状態で）
WshShell.Run Chr(34) & "{exe_path}" & Chr(34), 1, False
"""
            
            with open(vbs_path, 'w', encoding='utf-8') as f:
                f.write(vbs_content)
            
            # VBScriptを実行
            subprocess.Popen(["wscript.exe", vbs_path], creationflags=subprocess.CREATE_NO_WINDOW)
            
            logging.info(f"Restart initiated via VBScript (script: {vbs_path})")
            
            # クリーンアップして終了
            self.app.perform_cleanup()
            self.app.root.quit()
            # sys.exit(0)
            
        except Exception as e:
            logging.error(f"Restart failed: {e}")
            import traceback
            logging.error(traceback.format_exc())
            # エラー時はフォールバックせずメッセージのみ
            tk.messagebox.showerror("再起動エラー", f"再起動に失敗しました:\n{e}")

if False:
    def restart_app(self):
        """BATファイルを動的生成してPowerShellスクリプトを実行"""
        import tempfile
        
        try:
            # 実行ファイル情報の取得
            if getattr(sys, 'frozen', False):
                exe_name = os.path.basename(sys.executable)
            else:
                # 開発環境ではフォールバック
                logging.warning("BAT restart is only available in frozen mode")
                self._restart_fallback()
                return
            
            # PowerShellスクリプト生成
            ps_script_path = os.path.join(tempfile.gettempdir(), "psce_restart.ps1")
            ps_content = f"""# Auto-generated restart script
$ExeName = "{exe_name}"
Get-WmiObject Win32_Process | Where-Object {{ $_.Name -eq $ExeName }} | ForEach-Object {{
    $ExePath = $_.Path
    $ExeDir = Split-Path -Path $ExePath -Parent
    
    Stop-Process -Id $_.ProcessId -Force
    Start-Sleep -Seconds 1
    
    Set-Location $ExeDir
    Start-Process -FilePath $ExePath -WorkingDirectory $ExeDir
}}
"""
            with open(ps_script_path, 'w', encoding='utf-8') as f:
                f.write(ps_content)
            
            # BATファイル生成
            bat_path = os.path.join(tempfile.gettempdir(), "psce_restart.bat")
            bat_content = f"""@echo off
    powershell.exe -ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File "{ps_script_path}"
    del "%~f0"
    """
            with open(bat_path, 'w', encoding='cp932') as f:
                f.write(bat_content)
            
            # BATを実行
            subprocess.Popen(["cmd", "/c", bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
            
            logging.info(f"Restart initiated via BAT+PowerShell")
            
            self.app.perform_cleanup()
            self.app.root.destroy()
            sys.exit(0)
            
        except Exception as e:
            logging.error(f"Restart failed: {e}")
            import traceback
            logging.error(traceback.format_exc())
            self._restart_fallback()

    def _restart_fallback(self):
        """フォールバック: 環境変数クリーニング方式"""
        try:
            exe_path = sys.executable
            
            # 環境変数のクリーンアップ（PyInstaller関連をすべて除去）
            env = {}
            ignore_keys = {
                'TCL_LIBRARY', 'TK_LIBRARY',
                '_MEIPASS', '_MEIPASS2',  # PyInstaller一時フォルダ
                'PYTHONPATH', 'PYTHONHOME',  # Python環境
            }
            ignore_prefixes = ('_MEI', 'PYTHON', 'TCL', 'TK')  # プレフィックスマッチ
    
            for k, v in os.environ.items():
                k_upper = k.upper()
                # 除外リストとプレフィックスの両方でチェック
                if k_upper not in ignore_keys and not k_upper.startswith(ignore_prefixes):
                    env[k] = v
            
            # 新しいプロセスを起動
            if getattr(sys, 'frozen', False):
                subprocess.Popen([exe_path], env=env, creationflags=0x00000010)
            else:
                subprocess.Popen([exe_path] + sys.argv, env=env, creationflags=0x00000010)
            
            logging.info("Restart initiated via fallback method")
            
        except Exception as e:
            import traceback
            err_msg = f"再起動に失敗しました:\n{e}\n{traceback.format_exc()}"
            tk.messagebox.showerror("Restart Error", err_msg)
            logging.error(err_msg)
            return  # 起動失敗時は終了しない
        
        # 現在のプロセスを終了
        self.app.perform_cleanup()
        self.app.root.destroy()
        sys.exit(0)


if False:
    def restart_app(self):
            """アプリケーションを再起動する内部メソッド（直接起動・デバッグ版）"""
            try:
                # 1. 実行ファイルのパス
                exe_path = sys.executable
                # 2. 環境変数のクリーンアップ
                # PyInstallerの環境変数が残っていると再起動後のアプリがクラッシュするため除去
                env = {}
                ignore_keys = {'TCL_LIBRARY', 'TK_LIBRARY', '_MEIPASS2'}
                for k, v in os.environ.items():
                    if k.upper() not in ignore_keys:
                        env[k] = v
                # 3. 新しいプロセスを起動
                # creationflags=0x00000010 (CREATE_NEW_CONSOLE) で別コンソールとして分離
                if getattr(sys, 'frozen', False):
                    # EXEの場合
                    subprocess.Popen([exe_path], env=env, creationflags=0x00000010)
                else:
                    # 開発環境の場合
                    subprocess.Popen([exe_path] + sys.argv, env=env, creationflags=0x00000010)
            except Exception as e:
                # エラーが起きたらダイアログで表示
                import traceback
                err_msg = f"再起動に失敗しました:\n{e}\n{traceback.format_exc()}"
                tk.messagebox.showerror("Restart Error", err_msg)
                logging.error(err_msg)
                return  # 起動失敗時は終了しない
            # 4. 現在のプロセスを終了
            logging.info("Restarting... closing current process.")
            self.app.perform_cleanup()
            self.app.root.destroy()
            sys.exit(0)

if False:        
    def restart_app(self):
        """アプリケーションを再起動する内部メソッド"""

        # 現在のウィンドウを閉じる（リソース解放のため）
        # self.app.root.destroy() # ここでdestroyすると後続の処理が動かない可能性があるため、sys.exit直前に任せるか、非表示にする
        
        # 環境変数の準備 (PyInstaller対策)
        # 古いTCL/TKライブラリパスを削除しないと、新しいプロセスが見つけられずにエラーになる
        env = os.environ.copy()
        # 削除すべき環境変数リスト
        # keys_to_remove = ['TCL_LIBRARY', 'TK_LIBRARY', '_MEIPASS2']
        keys_to_remove = {'TCL_LIBRARY', 'TK_LIBRARY', '_MEIPASS2'} # 大文字小文字を無視して削除
        
        # 辞書のキーをリスト化してループ（削除中のエラーを防止）
        for key in keys_to_remove:
            if key in env:
                del env[key]        
                
        # 新しいインスタンスを起動
        if getattr(sys, 'frozen', False):
            # EXEの場合
            try:
                # subprocess.Popen([sys.executable], creationflags=subprocess.CREATE_NEW_CONSOLE)
                # env引数を追加
                subprocess.Popen([sys.executable], creationflags=subprocess.CREATE_NEW_CONSOLE, env=env)
            except Exception as e:
                logging.error(f"Failed to restart exe: {e}")
                # フォールバック
                try:
                    os.startfile(sys.executable)
                except:
                    pass
        else:
            # 開発モードの場合
            try:
                # subprocess.Popen([sys.executable] + sys.argv, creationflags=subprocess.CREATE_NEW_CONSOLE)
                subprocess.Popen([sys.executable] + sys.argv, creationflags=subprocess.CREATE_NEW_CONSOLE, env=env)                
            except:
                # subprocess.Popen([sys.executable] + sys.argv)
                subprocess.Popen([sys.executable] + sys.argv, env=env) 

        # 現在のプロセスを終了
        self.app.perform_cleanup()
        self.app.root.quit() # メインループを抜ける
        sys.exit()
