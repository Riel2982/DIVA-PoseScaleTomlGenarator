import logging
import time     # デバッグログ用（起動時間計測）
print(f"[DEBUG] {time.time()}: Start importing modules...")

import tkinter as tk
import os
import configparser
import sys
import ctypes
from psce_gui import ConfigEditorApp
from psce_util import setup_editor_logging, ConfigUtility, VERSION
from psce_update import check_update

print(f"[DEBUG] {time.time()}: Finished importing modules")

# メイン関数
if __name__ == "__main__":
    print(f"[DEBUG] {time.time()}: Entering main")

    # 高DPI対応（文字滲み解消）
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()      

    # アップデートチェックモード
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        # まだパスが通っていない場合があるので追加
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        try:
            check_update(current_version=VERSION, exe_name="PoseScaleConfigEditor.exe")
        except Exception as e:
            pass # エラーでも黙って終了
        sys.exit(0)

    # ConfigUtilityを使ってConfig.iniを読み込む
    print(f"[DEBUG] {time.time()}: Loading ConfigUtility...")

    utils = ConfigUtility()
    config = utils.load_config(utils.main_config_path)
    
    print(f"[DEBUG] {time.time()}: Loaded ConfigUtility")

    show_debug = False
    output_log = False
    if config:
        show_debug = config.getboolean('DebugSettings', 'ShowDebugSettings', fallback=False)
        output_log = config.getboolean('DebugSettings', 'OutputLog', fallback=False)
    
    # ログ初期化
    setup_editor_logging(show_debug=show_debug, output_log=output_log)
    print(f"[DEBUG] {time.time()}: Creating Tk root...")

    root = tk.Tk()  # ルートウィンドウを作成
    print(f"[DEBUG] {time.time()}: Created Tk root. Initializing App...")
    app = ConfigEditorApp(root) # アプリケーションのインスタンスを作成
    print(f"[DEBUG] {time.time()}: Initialized App. Validating font caches...")
    print(f"[DEBUG] {time.time()}: Starting mainloop")
    root.mainloop() # メインループを開始

    # sys.exit(0)