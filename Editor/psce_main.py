import tkinter as tk
from psce_gui import ConfigEditorApp

# メイン関数
if __name__ == "__main__":
    root = tk.Tk()  # ルートウィンドウを作成
    app = ConfigEditorApp(root) # アプリケーションのインスタンスを作成
    root.mainloop() # メインループを開始
