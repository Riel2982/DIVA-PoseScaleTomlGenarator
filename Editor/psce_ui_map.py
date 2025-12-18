import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import os
import shutil
from psce_util import CustomMessagebox, normalize_text, make_hidden_folder


# PoseID MapタブUIクラス
class PoseIDMapTab:
    # 初期化
    def __init__(self, notebook, app):
        self.app = app
        self.trans = app.trans
        self.tab = ttk.Frame(notebook)
        notebook.add(self.tab, text=self.trans.get("tab_pose_id_map"))
        self.create_widgets()

    # ウィジェット作成
    def create_widgets(self):
        paned = ttk.PanedWindow(self.tab, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=5, pady=5)

        # リスト表示用フレーム
        frame_left = ttk.Frame(paned)
        frame_right = ttk.LabelFrame(paned, text=self.trans.get("edit_mapping"), padding=10)
        paned.add(frame_left, weight=1)
        paned.add(frame_right, weight=2)

        # リスト表示用
        self.app.map_listbox = tk.Listbox(frame_left, exportselection=False)
        self.app.map_listbox.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(frame_left, orient='vertical', command=self.app.map_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.app.map_listbox.config(yscrollcommand=scrollbar.set)
        self.app.map_listbox.bind('<<ListboxSelect>>', self.on_map_select)

        # ボタン用フレーム
        frame_btns = ttk.Frame(frame_left)
        frame_btns.pack(fill='x', pady=5)
        
        frame_btns1 = ttk.Frame(frame_btns)
        frame_btns1.pack(fill='x')
        ttk.Button(frame_btns1, text=self.trans.get("add_new"), command=self.add_map_entry).pack(side='left', expand=True, fill='x')   # 新規追加
        ttk.Button(frame_btns1, text=self.trans.get("duplicate"), command=self.duplicate_map_entry).pack(side='left', expand=True, fill='x')  # 重複    
        
        frame_btns2 = ttk.Frame(frame_btns)
        frame_btns2.pack(fill='x')
        ttk.Button(frame_btns2, text=self.trans.get("up"), command=lambda: self.move_map_entry(-1)).pack(side='left', expand=True, fill='x')  # 上
        ttk.Button(frame_btns2, text=self.trans.get("down"), command=lambda: self.move_map_entry(1)).pack(side='left', expand=True, fill='x')  # 下
        
        frame_btns3 = ttk.Frame(frame_btns)
        frame_btns3.pack(fill='x')
        ttk.Button(frame_btns3, text=self.trans.get("delete"), command=self.delete_map_entry).pack(side='left', expand=True, fill='x')  # 削除

        # Edit Fields（編集フィールド）
        ttk.Label(frame_right, text=self.trans.get("pose_id")).pack(anchor='w')
        self.app.map_id_var = tk.StringVar()
        self.app.map_id_entry = ttk.Entry(frame_right, textvariable=self.app.map_id_var)
        self.app.map_id_entry.pack(fill='x', pady=(0, 10))
        self.app.enable_text_undo_redo(self.app.map_id_entry)
        
        # ポーズ名
        ttk.Label(frame_right, text=self.trans.get("pose_name")).pack(anchor='w')
        self.app.map_name_var = tk.StringVar()
        self.app.map_name_entry = ttk.Entry(frame_right, textvariable=self.app.map_name_var)
        self.app.map_name_entry.pack(fill='x', pady=(0, 10))
        self.app.enable_text_undo_redo(self.app.map_name_entry)

        # Image Preview（画像プレビュー）
        self.app.map_image_frame = ttk.LabelFrame(frame_right, text=self.trans.get("image_preview"), padding=5)
        self.app.map_image_frame.pack(fill='both', expand=True)
        
        # 画像表示位置
        self.app.map_image_label = ttk.Label(self.app.map_image_frame, text=self.trans.get("no_image"), anchor='center')
        self.app.map_image_label.pack(fill='both', expand=True)
        
        # 画像選択用フレーム
        frame_img_btns = ttk.Frame(frame_right)
        frame_img_btns.pack(pady=5)
        ttk.Button(frame_img_btns, text=self.trans.get("select_image"), command=self.select_map_image).pack(side='left', padx=2)  # 画像選択
        ttk.Button(frame_img_btns, text=self.trans.get("delete_image"), command=self.delete_map_image).pack(side='left', padx=2)  # 画像削除

        ttk.Button(frame_right, text=self.trans.get("update_save_map"), command=self.save_map_entry).pack(pady=10)  # 更新保存
        
        self.refresh_pose_id_map_list(select_first=True)

    # ポーズIDマップリストの更新
    def refresh_pose_id_map_list(self, select_first=False):
        # 現在の選択を保存
        last_selection_key = self.app.selected_map_key

        self.app.map_listbox.delete(0, 'end')
        # ポーズIDマップセクションがある場合
        if self.app.pose_id_map.has_section('PoseIDs'):
            for key, value in self.app.pose_id_map.items('PoseIDs'):
                self.app.map_listbox.insert('end', f"{key}: {value}")
        
        # 選択を復元
        restored = False
        if last_selection_key:
            items = self.app.map_listbox.get(0, 'end')
            for i, item in enumerate(items):
                if item.startswith(f"{last_selection_key}:"):
                    self.app.map_listbox.selection_set(i)
                    self.app.map_listbox.activate(i)
                    self.app.map_listbox.see(i) # Ensure visible
                    # Ensure UI is updated
                    self.on_map_select(None)
                    restored = True
                    break

        # Select first item only on initial load if restoration failed
        if select_first and not restored and self.app.map_listbox.size() > 0:
            self.app.map_listbox.selection_set(0)
            # Directly call handler to ensure UI is updated
            self.on_map_select(None)

    # ポーズIDマップリストの選択
    def on_map_select(self, event):
        selection = self.app.map_listbox.curselection()
        if not selection:   # 選択がない場合
            self.app.selected_map_key = None
            return
        
        # 選択された項目を取得
        item = self.app.map_listbox.get(selection[0])
        key, value = item.split(':', 1)
        key = key.strip()
        value = value.strip()
        
        # 選択された項目を設定
        self.app.selected_map_key = key
        self.app.map_id_var.set(key)
        self.app.map_name_var.set(value)
        
        # Reset undo stack for text fields to prevent mixing history from different entries
        if hasattr(self.app, 'map_id_entry') and hasattr(self.app.map_id_entry, 'reset_undo_stack'):
            self.app.map_id_entry.reset_undo_stack(key)
        if hasattr(self.app, 'map_name_entry') and hasattr(self.app.map_name_entry, 'reset_undo_stack'):
            self.app.map_name_entry.reset_undo_stack(value)
        
        self.image_deleted_pending = False # Reset pending flag
        self.pending_trash_image = None # Reset pending trash
        
        # 画像を表示
        self.load_map_image(key)

    # 画像を表示
    def load_map_image(self, pose_id):
        image_path = self.app.utils.find_image_for_pose(pose_id)
        
        if image_path:
            try:
                with Image.open(image_path) as img:
                    img.thumbnail((390, 390))  # 画像を縮小
                    photo = ImageTk.PhotoImage(img)
                self.app.map_image_label.configure(image=photo)
                self.app.map_image_label.image = photo
            except Exception:
                self.app.map_image_label.configure(image='')
                self.app.map_image_label.image = None
        else:
            self.app.map_image_label.configure(image='')
            self.app.map_image_label.image = None

    # 画像を選択
    def select_map_image(self):
        if not self.app.selected_map_key: return
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp"), ("All Files", "*.*")])     # 画像を選択
        # 画像を選択した場合
        if path:
            # Snapshot map state BEFORE changes
            self.app.history.snapshot('map')
            
            # Process pending trash if exists (User deleted old image then selected new one)
            if getattr(self, 'pending_trash_image', None):
                try:
                    trash_dir = os.path.join(self.app.utils.pose_images_dir, '_trash')
                    if not os.path.exists(trash_dir):
                        make_hidden_folder(trash_dir)   # 隠し属性を付けて「_trash」フォルダを作成                    
                    # 隠し属性はつけないでフォルダ作成
                    # trash_dir = os.path.join(self.app.utils.pose_images_dir, '_trash')
                    # if not os.path.exists(trash_dir):
                        # os.makedirs(trash_dir)
                    trash_path = os.path.join(trash_dir, os.path.basename(self.pending_trash_image))
                    shutil.move(self.pending_trash_image, trash_path)
                    self.app.history.register_file_move('map', self.pending_trash_image, trash_path)
                    self.pending_trash_image = None
                except Exception as e:
                    logging.error(f"Failed to move pending trash image: {e}")

            pose_id = self.app.selected_map_key
            pose_name = self.app.map_name_var.get()
            
            # ファイル名を正規化
            safe_name = "".join(c for c in pose_name if c.isalnum() or c in (' ', '_', '-')).strip()
            _, ext = os.path.splitext(path)
            new_filename = f"{pose_id}_{safe_name}{ext}"
            
            dest_path = os.path.join(self.app.utils.pose_images_dir, new_filename)  # 画像を保存するパス
            
            import shutil # 画像をコピー
            try:
                if not os.path.exists(self.app.utils.pose_images_dir):
                    os.makedirs(self.app.utils.pose_images_dir)
                shutil.copy2(path, dest_path)
                
                # Image is saved with filename-based naming convention, no config update needed
                self.load_map_image(pose_id)
            # 画像コピー失敗時 (select_map_image)
            except Exception as e:
                # messagebox.showerror(self.trans.get("error"), self.trans.get("copy_image_fail", path))
                self.app.show_status_message(self.trans.get("copy_image_fail", path), "error")


    # 画像を削除
    def delete_map_image(self):
        if not self.app.selected_map_key: return
        
        image_path = self.app.utils.find_image_for_pose(self.app.selected_map_key)  # 画像のパス
        if not image_path:
            # messagebox.showinfo(self.trans.get("no_image"), self.trans.get("no_image"))
            self.app.show_status_message(self.trans.get("no_image"), "warning") # またはerror
            return

        filename = os.path.basename(image_path)
        # 確認なしで削除するため無効化中
        # if not messagebox.askyesno(self.trans.get("confirm"), self.trans.get("delete_image_confirm", filename)):
        #     return

        # Tentative delete (will be executed on Save)
        # 削除完了の案内
        self.app.show_status_message(self.trans.get("msg_deleted_image"), "info")

        self.pending_trash_image = image_path
       
        # 画像プレビューをクリア
        self.app.map_image_label.configure(image='')
        self.app.map_image_label.image = None

    # 新規PoseIDMapを追加
    def add_map_entry(self):
        self.app.history.snapshot('map')  # ヒストリを保存
        if not self.app.pose_id_map.has_section('PoseIDs'):
            self.app.pose_id_map.add_section('PoseIDs')
            
        # Find next available ID（次の利用可能なIDを検索する）
        existing_ids = [int(k) for k in self.app.pose_id_map['PoseIDs'].keys() if k.isdigit()]
        next_id = 1
        if existing_ids:
            next_id = max(existing_ids) + 1

        # 新しいIDを設定    
        self.app.pose_id_map.set('PoseIDs', str(next_id), 'New Pose')
        self.app.utils.save_config(self.app.pose_id_map, self.app.utils.pose_id_map_path)

        # 新規追加完了の案内
        self.app.show_status_message(self.trans.get("msg_added_map", next_id), "success")

        self.refresh_pose_id_map_list()
        
        # 新しい項目を選択
        idx = self.app.map_listbox.size() - 1
        self.app.map_listbox.selection_clear(0, 'end')  # 一度すべての選択状態を解除
        self.app.map_listbox.selection_set(idx) # 作成したものに選択を切り替える
        self.app.map_listbox.event_generate("<<ListboxSelect>>")

    # 既存のPoseIDMapを複製
    def duplicate_map_entry(self):
        if not self.app.selected_map_key: return
        source_id = self.app.selected_map_key # 複製元IDの取得

        self.app.history.snapshot('map')  # ヒストリを保存
        
        # Find next available ID
        existing_ids = [int(k) for k in self.app.pose_id_map['PoseIDs'].keys() if k.isdigit()]
        next_id = 1
        if existing_ids:
            next_id = max(existing_ids) + 1
            
        current_name = self.app.map_name_var.get()
        new_name = f"{current_name}_Copy"
        
        self.app.pose_id_map.set('PoseIDs', str(next_id), new_name)
        self.app.utils.save_config(self.app.pose_id_map, self.app.utils.pose_id_map_path)

        # 複製完了の案内
        self.app.show_status_message(self.trans.get("msg_duplicated_map", source_id), "info")

        self.refresh_pose_id_map_list()
        
        # 新しいアイテムを選択
        items = self.app.map_listbox.get(0, 'end')
        for i, item in enumerate(items):
            if item.startswith(f"{next_id}:"):
                self.app.map_listbox.selection_clear(0, 'end')  # すべての選択を解除
                self.app.map_listbox.selection_set(i)   # 複製物を選択状態に
                self.app.map_listbox.event_generate("<<ListboxSelect>>")
                break

    # マップを移動
    def move_map_entry(self, direction):
        selection = self.app.map_listbox.curselection()
        if not selection: return
        idx = selection[0]
        
        # Check bounds
        if direction == -1 and idx == 0: return
        if direction == 1 and idx == self.app.map_listbox.size() - 1: return
        
        self.app.history.snapshot('map')
        
        # Get all items
        items = []
        if self.app.pose_id_map.has_section('PoseIDs'):
             items = list(self.app.pose_id_map.items('PoseIDs'))
             
        if not items: return
        
        # Swap
        items[idx], items[idx + direction] = items[idx + direction], items[idx]
        
        # Rebuild section (to preserve order)
        self.app.pose_id_map.remove_section('PoseIDs')
        self.app.pose_id_map.add_section('PoseIDs')
        for k, v in items:
            self.app.pose_id_map.set('PoseIDs', k, v)
            
        self.app.utils.save_config(self.app.pose_id_map, self.app.utils.pose_id_map_path)
        self.refresh_pose_id_map_list()
        
        # Restore selection
        self.app.map_listbox.selection_set(idx + direction)
        self.app.map_listbox.event_generate("<<ListboxSelect>>")

    # マップを削除
    def delete_map_entry(self):
        if not self.app.selected_map_key: return
        
        # Confirm deletion
        # if not messagebox.askyesno(self.trans.get("confirm"), self.trans.get("delete_confirm", self.app.selected_map_key)):
        #     return
        
        # Undo/Redo履歴に記録
        self.app.history.snapshot('map')
        
        # 削除完了の案内
        pose_id = self.app.selected_map_key # 削除対象のID
        self.app.show_status_message(self.trans.get("msg_deleted_map", pose_id), "success")

        # Get current selection index before deletion
        selection = self.app.map_listbox.curselection()
        if not selection: return
        idx = selection[0]
        
        # Remove from config
        if self.app.pose_id_map.has_section('PoseIDs'):
            self.app.pose_id_map.remove_option('PoseIDs', self.app.selected_map_key)
            
        # Move image to trash if it exists (filename-based matching)
        image_path = self.app.utils.find_image_for_pose(self.app.selected_map_key)
        if image_path:
            trash_dir = os.path.join(self.app.utils.pose_images_dir, '_trash')
            if not os.path.exists(trash_dir):
                make_hidden_folder(trash_dir) # 隠し属性を付けてフォルダ生成           
            # 隠し属性を付けない場合
            # trash_dir = os.path.join(self.app.utils.pose_images_dir, '_trash')
            # if not os.path.exists(trash_dir):
                # os.makedirs(trash_dir)
            trash_path = os.path.join(trash_dir, os.path.basename(image_path))
            try:
                shutil.move(image_path, trash_path)
                self.app.history.register_file_move('map', image_path, trash_path)
            except:
                pass
                
        self.app.utils.save_config(self.app.pose_id_map, self.app.utils.pose_id_map_path)
        self.app.selected_map_key = None
        self.refresh_pose_id_map_list()
        
        # Select adjacent item and load its content
        count = self.app.map_listbox.size()
        if count > 0:
            new_idx = idx if idx < count else count - 1
            self.app.map_listbox.selection_set(new_idx)
            self.app.map_listbox.activate(new_idx)
            # Load the selected map entry
            self.on_map_select(None)

    # マップを保存
    def save_map_entry(self):
        pose_id = normalize_text(self.app.map_id_var)
        name = normalize_text(self.app.map_name_var)
        # pose_id = normalize_text(self.app.map_id_var.get())
        # name = normalize_text(self.app.map_name_var.get())

        # Check for changes (変更があるか確認)
        has_changes = False
        if self.app.selected_map_key != pose_id:
            has_changes = True
        else:
            if self.app.pose_id_map.get('PoseIDs', pose_id, fallback='') != name:
                has_changes = True
            # Check for pending trash or image changes (implicit check via pending_trash)
            if getattr(self, 'pending_trash_image', None):
                has_changes = True
                
        if not has_changes:
            self.app.show_status_message(self.trans.get("msg_no_changes"), "warning")  # 変更事項がない場合の案内
            return

        # 変更が検出された場合のみスナップショットを取る
        self.app.history.snapshot('map')

        # IDを変更する場合、重複するIDをチェックする
        if self.app.selected_map_key and self.app.selected_map_key != pose_id:
            if self.app.pose_id_map.has_option('PoseIDs', pose_id):
                 if not messagebox.askyesno(self.trans.get("confirm"), self.trans.get("overwrite_confirm", pose_id)):
                     return
            # Remove old（古いものを削除する）
            self.app.pose_id_map.remove_option('PoseIDs', self.app.selected_map_key)

        self.app.pose_id_map.set('PoseIDs', pose_id, name)
        
        try:
            # Process Pending Trash (Execute deletion)
            if getattr(self, 'pending_trash_image', None):
                trash_dir = os.path.join(self.app.utils.pose_images_dir, '_trash')
                if not os.path.exists(trash_dir):
                    make_hidden_folder(trash_dir) # 隠し属性を付けてフォルダ生成   
                # 隠し属性を付けない場合
                # trash_dir = os.path.join(self.app.utils.pose_images_dir, '_trash')
                # if not os.path.exists(trash_dir):
                    # os.makedirs(trash_dir)
                trash_path = os.path.join(trash_dir, os.path.basename(self.pending_trash_image))
                
                try:
                    if os.path.exists(self.pending_trash_image):
                        shutil.move(self.pending_trash_image, trash_path)
                        self.app.history.register_file_move('map', self.pending_trash_image, trash_path)
                except Exception as e:
                    logging.error(f"Failed to move pending trash image: {e}")
                
                self.pending_trash_image = None

            # 画像ファイルを再命名する
            if self.app.selected_map_key:
                old_image_path = self.app.utils.find_image_for_pose(self.app.selected_map_key)
                if old_image_path: # 削除待ち（既に移動済み）または見つからない場合は名前を変更しない
                    old_filename = os.path.basename(old_image_path)
                    _, ext = os.path.splitext(old_filename)
                    
                    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
                    new_filename = f"{pose_id}_{safe_name}{ext}"
                    
                    if old_filename != new_filename:
                        self.app.utils.rename_image(old_filename, new_filename)

            # configを保存
            self.app.utils.save_config(self.app.pose_id_map, self.app.utils.pose_id_map_path)

            # 保存完了の案内
            if self.app.selected_map_key and self.app.selected_map_key != pose_id:
                # ID変更の場合
                message = self.trans.get("msg_renamed_map_id").format(old=self.app.selected_map_key, new=pose_id)
                # message = self.trans.get("msg_renamed_map_id").format(self.app.selected_map_key, pose_id)
            else:
                # 通常保存の場合
                message = self.trans.get("msg_saved_map").format(pose_id)            
            self.app.show_status_message(message, "success")
            # self.app.show_status_message(self.trans.get("msg_saved_map", pose_id), "success")
        
            self.refresh_pose_id_map_list()    # 画面更新
            
            # 選択を再設定
            items = self.app.map_listbox.get(0, 'end')
            for i, item in enumerate(items):
                if item.startswith(f"{pose_id}:"):
                    self.app.map_listbox.selection_set(i)
                    self.app.map_listbox.event_generate("<<ListboxSelect>>")
                    break
        except Exception as e:
            messagebox.showerror(self.trans.get("error"), self.trans.get("failed_save", e))

    # 選択を再設定
    def select_map_item_by_id(self, pose_id):
        items = self.app.map_listbox.get(0, 'end')
        for i, item in enumerate(items):
            if item.startswith(f"{pose_id}:"):
                self.app.map_listbox.selection_clear(0, 'end')
                self.app.map_listbox.selection_set(i)
                self.app.map_listbox.activate(i)
                self.app.map_listbox.see(i)
                self.app.map_listbox.event_generate("<<ListboxSelect>>")
                break
