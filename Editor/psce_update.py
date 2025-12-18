import sys
import os
import json
import time
import requests
import subprocess
import shutil
import logging
import tempfile
import re
import webbrowser
from datetime import datetime # 日時用
from tkinter import Toplevel, ttk, messagebox, Tk
from packaging import version
from psce_util import VERSION, ConfigUtility
from psce_translation import TranslationManager


UPDATE_STATUS_FILE = "Settings/update_status.json"
REPO_OWNER = "Riel2982"
REPO_NAME = "DIVA-PoseScaleTomlGenarator"

def get_status_path():
    if getattr(sys, 'frozen', False): # PyInstallerでビルドされた場合
        app_dir = os.path.dirname(os.path.abspath(sys.executable))
    else: # デバッグ用
        app_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(app_dir, UPDATE_STATUS_FILE)

def load_status():
    path = get_status_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_status(data):
    path = get_status_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig') as f:
        json.dump(data, f, indent=4)

def parse_release_filename(filename):
    # 例: PoseScaleTomlGenerator_v0.1.1-beta.zip → {"version": "0.1.1-beta"}
    base = os.path.splitext(filename)[0]
    # parts = base.split("_")

    # 単純にアンダースコアで分割して、最後の部分を取得する
    if "_" in base:
        ver_str = base.split("_")[-1]
    else:
        ver_str = base
    # もし "v0.1.1" のように "v" が付いていたら除去
    if ver_str.startswith("v"):
        ver_str = ver_str[1:]
     
    # "beta数字" の形式のみ "0.0.数字" に変換 (v0.1.1-beta のような形式は除外)
    match = re.match(r"^beta(\d+)$", ver_str)
    if match:
        return {"version": f"0.0.{match.group(1)}"}
        
    return {"version": ver_str}
    # return {"version": parts[-1]}


def check_update(force=False):
    """GitHubから最新リリースを確認して update_status.json に保存"""
    status = load_status()
    current_time = datetime.now()
    
    # 頻度制限: 1時間以内なら前回の結果を返す (force=Trueなら無視)
    if not force and 'last_checked_iso' in status:
        try:
            last_checked = datetime.fromisoformat(status['last_checked_iso'])
            if (current_time - last_checked).total_seconds() < 3600:
                logging.info("Skipping update check (cached)")
                return status
        except Exception:
            pass
    try:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            release = response.json()
            current_version = VERSION # 実行中のアプリバージョンを使用
            latest_version = ""
            # ZIPファイルからバージョン抽出
            for asset in release.get('assets', []):
                if asset['name'].endswith(".zip"):
                    info = parse_release_filename(asset['name'])
                    latest_version = info['version']
                    break
            
            # バージョンが見つからなかった場合のフォールバック（タグ名はバージョン判定に使えないため不使用）
            # if not latest_version:
                 # latest_version = release['tag_name'].lstrip('v')

            # SemVer比較
            is_newer = False
            try:
                is_newer = version.parse(latest_version) > version.parse(current_version)
            except Exception as e:
                logging.error(f"Version parse error: {e}")

            # exeアセット一覧を収集
            exe_assets = {}
            for asset in release.get('assets', []):
                if asset['name'].endswith(".exe"):
                    exe_assets[asset['name']] = asset['browser_download_url']
            new_status = {
                'last_checked_iso': current_time.isoformat(),
                'current_version': current_version, # ここにはアプリの現バージョンを記録
                'latest_version': latest_version,
                'available': is_newer,
                'release_url': release.get('html_url', ''), # リリースとページのURL
                'exe_assets': exe_assets
            }
            save_status(new_status)
            return new_status
        else:
            logging.error(f"Update Check Error: Status Code {response.status_code}")
            return None
            
    except Exception as e:
        logging.error(f"Update check failed: {e}")
        return None


# 更新ダイアログを表示し、ユーザーの選択に応じて処理を行う
def perform_update(root_window=None):
    

    if root_window is None:
        root = Tk()
        root.withdraw()
    else:
        root = root_window

    # --- 翻訳準備 ---
    utils = ConfigUtility()
    trans = TranslationManager()
    # 既存の設定から言語設定を読み込む（もし失敗したら英語デフォルト）
    try:
        config = utils.load_config(utils.main_config_path)
        if config:
            lang = config.get('GeneralSettings', 'Language', fallback='en')
            trans.set_language(lang)
    except Exception:
        pass

    status = load_status()
    if not status.get('available', False):
        messagebox.showinfo(trans.get("window_title"), trans.get("msg_no_update"), parent=root)
        return
    latest_ver = status.get('latest_version', 'Unknown')
    release_url = status.get('release_url', f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases")
    
    # --- カスタムダイアログの作成 ---
    dialog = Toplevel(root)
    dialog.title("アップデート確認")
    dialog.geometry("380x140")
    dialog.grab_set() # モーダルにする
    
    # 中央配置
    root.update_idletasks()
    """
    x = root.winfo_rootx() + (root.winfo_width() // 2) - (380 // 2)
    y = root.winfo_rooty() + (root.winfo_height() // 2) - (140 // 2)
    dialog.geometry(f"+{x}+{y}")
    """

    # マウスカーソル位置（ボタン付近）を基準に配置
    root.update_idletasks()
    
    # マウス座標を取得
    ptr_x, ptr_y = root.winfo_pointerxy()
    logging.info(f"DEBUG: Update Mouse Ptr: ({ptr_x}, {ptr_y})") 
    
    # ダイアログサイズ
    dlg_w = 380
    dlg_h = 140
    
    # マウス位置の少し右下に表示（画面からはみ出さないように簡易調整）
    x = ptr_x - (dlg_w // 2) # マウスを中心に左右描画
    y = ptr_y + 20 # マウスの少し下
    
    dialog.geometry(f"+{x}+{y}")

    msg = trans.get("update_msg", latest_ver)
    ttk.Label(dialog, text=msg, padding=20, justify='center').pack()

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(fill='x', padx=20, pady=10)

    # ユーザーの選択結果を格納する変数
    user_choice = {'action': 'cancel'}

    def on_update():
        user_choice['action'] = 'update'
        dialog.destroy()

    def on_browser():
        webbrowser.open(release_url)
        dialog.destroy() # ブラウザを開いて閉じる

    def on_cancel():
        dialog.destroy()

    # ボタン配置
    ttk.Button(btn_frame, text=trans.get("btn_update"), command=on_update).pack(side='left', expand=True, padx=4)
    ttk.Button(btn_frame, text=trans.get("btn_browser"), command=on_browser).pack(side='left', expand=True, padx=4)
    ttk.Button(btn_frame, text=trans.get("update_cancel"), command=on_cancel).pack(side='left', expand=True, padx=4)

    root.wait_window(dialog)

    if user_choice['action'] != 'update':
        return
    # === ダウンロード・更新実行処理 ===
    logging.info("DEBUG: Starting download process...") 
    exe_assets = status.get('exe_assets', {})
    
    if not exe_assets:
        messagebox.showerror(trans.get("error"), trans.get("err_update_file_missing"), parent=root)
        return
    
    # インストール先フォルダの特定
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))

    logging.info(f"DEBUG: App Dir: {app_dir}")
    updated_files = []

    try:
        # ダウンロード処理
        for exe_name, url in exe_assets.items():
            logging.info(f"DEBUG: Processing {exe_name}...")
            dst_path = os.path.join(app_dir, exe_name)
            
            # 一時ファイルへダウンロード
            logging.info(f"DEBUG: Downloading from {url}")
            response = requests.get(url, stream=True, timeout=30)
            tmp_path = os.path.join(tempfile.gettempdir(), exe_name)
            
            with open(tmp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if exe_name == "PoseScaleConfigEditor.exe":
                logging.info("DEBUG: Editor update deferred.")
                # Editorは最後に更新するため、情報を保存だけしておく
                editor_update_info = (tmp_path, dst_path)
            else:
                # Generatorなどは即座に上書きコピー
                shutil.copy2(tmp_path, dst_path)
                updated_files.append(exe_name)

        # Editorの更新がある場合、最後に実行            
        if editor_update_info:
            logging.info("DEBUG: Updating Editor...")
            tmp_path, dst_path = editor_update_info            
            # Editor自身は動いているので直接上書きできないため、BATファイルで更新
            bat_path = os.path.join(tempfile.gettempdir(), "update_editor.bat")
            
            # 文字化け防止のためUFJ-8で書き込み、timeoutを入れてファイルロック解除を待つ
            with open(bat_path, 'w', encoding='utf-8-sig') as bat:
                bat.write(f"""@echo off
chcp 65001 > nul
timeout /t 2
copy /Y "{tmp_path}" "{dst_path}"
del "{tmp_path}"
start "" "{dst_path}"
del "%~f0"
""")
            # BATを実行してアプリを終了
            logging.info("DEBUG: Executing BAT...") 
            subprocess.Popen(["cmd", "/c", bat_path])
            updated_files.append("PoseScaleConfigEditor.exe")
            
            # Editorはここで即終了してBATに処理を譲る
            logging.info("DEBUG: Exiting app.")
            sys.exit(0) # Editorに更新があるならここで終了

        if updated_files:
            logging.info("DEBUG: Update complete.")
            messagebox.showinfo(trans.get("success"), trans.get("msg_update_complete", ', '.join(updated_files)), parent=root)
            # self.app.show_status_message(self.trans.get("msg_update_complete", ', '.join(updated_files)), "sucess")

    except Exception as e:
        logging.error(f"Update failed: {e}")
        logging.error(f"DEBUG: Error occurred: {e}")
        messagebox.showerror(trans.get("error"), trans.get("err_update_failed", e), parent=root)


perform_update_gui = perform_update