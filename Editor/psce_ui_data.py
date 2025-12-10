import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import configparser
import os
from psce_util import CustomMessagebox, normalize_text, normalize_comma_separated_string

# PoseScaleDataタブUIクラス
class PoseDataTab:
    # タブの作成
    def __init__(self, notebook, app):
        self.app = app
        self.trans = app.trans
        self.tab = ttk.Frame(notebook)
        notebook.add(self.tab, text=self.trans.get("tab_pose_data")) # タブの作成
        self.create_widgets()

    # UI要素の作成
    def create_widgets(self):
        frame_top = ttk.Frame(self.tab, padding=5)
        frame_top.pack(fill='x')
        ttk.Label(frame_top, text=self.trans.get("target_file")).pack(side='left')
        self.app.pose_file_combo = ttk.Combobox(frame_top, width=40)
        self.app.pose_file_combo.pack(side='left', padx=5)
        self.app.pose_file_combo.bind('<<ComboboxSelected>>', self.load_pose_data_file)
        
        # Left side buttons（左側のボタン配置）
        # Reordered Buttons: Create New -> Duplicate -> Delete（作成 -> 重複 -> 削除）
        ttk.Button(frame_top, text=self.trans.get("rename_file"), command=self.rename_current_pose_file).pack(side='left', padx=2)  # リネーム
        # Refresh is hidden.（再読み込みは非表示）
        # ttk.Button(frame_top, text=self.trans.get("refresh"), command=self.refresh_pose_files).pack(side='left')

        # Right side buttons (Order: Create, Duplicate, Delete)（右側のボタン配置（作成 -> 重複 -> 削除））
        # Desired: [Create] [Duplicate] [Delete] (Left to Right on the right side)（左から右に配置）
        ttk.Button(frame_top, text=self.trans.get("delete_file"), command=self.delete_current_pose_file).pack(side='right', padx=2)  # 削除
        ttk.Button(frame_top, text=self.trans.get("duplicate_file"), command=self.duplicate_current_pose_file).pack(side='right', padx=2)  # 重複
        ttk.Button(frame_top, text=self.trans.get("create_new_file"), command=self.create_new_pose_file).pack(side='right', padx=2)  # 作成

        # Paned Window（ペインウィンドウ）
        paned = ttk.PanedWindow(self.tab, orient='horizontal') # 水平方向
        paned.pack(fill='both', expand=True, padx=5, pady=5)

        # Left Frame（左フレーム）
        frame_left = ttk.Frame(paned)
        frame_right = ttk.LabelFrame(paned, text=self.trans.get("edit_setting"), padding=10) # 右フレーム
        paned.add(frame_left, weight=1)
        paned.add(frame_right, weight=2)

        # Listbox（リストボックス）
        self.app.pose_data_listbox = tk.Listbox(frame_left, exportselection=False)
        self.app.pose_data_listbox.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(frame_left, orient='vertical', command=self.app.pose_data_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.app.pose_data_listbox.config(yscrollcommand=scrollbar.set)
        self.app.pose_data_listbox.bind('<<ListboxSelect>>', self.on_pose_data_select) # リストボックス選択時

        # Button Frame（リスト横のボタンフレーム）
        frame_btns = ttk.Frame(frame_left)
        frame_btns.pack(fill='x', pady=5)  # x方向に配置
        
        frame_btns1 = ttk.Frame(frame_btns)
        frame_btns1.pack(fill='x')
        ttk.Button(frame_btns1, text=self.trans.get("add_new"), command=self.add_pose_data).pack(side='left', expand=True, fill='x') # 新規追加
        ttk.Button(frame_btns1, text=self.trans.get("duplicate"), command=self.duplicate_pose_data).pack(side='left', expand=True, fill='x') # 重複
        
        frame_btns2 = ttk.Frame(frame_btns)
        frame_btns2.pack(fill='x')
        ttk.Button(frame_btns2, text=self.trans.get("up"), command=lambda: self.move_pose_data(-1)).pack(side='left', expand=True, fill='x') # 上移動
        ttk.Button(frame_btns2, text=self.trans.get("down"), command=lambda: self.move_pose_data(1)).pack(side='left', expand=True, fill='x') # 下移動
        
        frame_btns3 = ttk.Frame(frame_btns)
        frame_btns3.pack(fill='x')
        ttk.Button(frame_btns3, text=self.trans.get("delete"), command=self.delete_pose_data).pack(side='left', expand=True, fill='x') # 削除

        # Edit Fields（編集フィールド）
        ttk.Label(frame_right, text=self.trans.get("section_name")).pack(anchor='w') # PoseScaleSettingセクション名
        frame_pd_section = ttk.Frame(frame_right)
        frame_pd_section.pack(fill='x', pady=(0, 10))
        ttk.Label(frame_pd_section, text="PoseScaleSetting_").pack(side='left') # PoseScaleSetting_XXX
        self.app.pd_section_suffix_var = tk.StringVar()
        entry_suffix = ttk.Entry(frame_pd_section, textvariable=self.app.pd_section_suffix_var)
        entry_suffix.pack(side='left', fill='x', expand=True)
        self.app.enable_text_undo_redo(entry_suffix)

        ttk.Label(frame_right, text=self.trans.get("chara")).pack(anchor='w') # キャラクター枠
        self.app.pd_chara_var = tk.StringVar()
        
        # Display Order (User Preference)（表示順序）
        self.chara_display_order = ["MIKU", "RIN", "LEN", "LUKA", "KAITO", "MEIKO", "NERU", "HAKU", "SAKINE", "TETO"]
        # Map Display Name -> Internal Code（表示名 -> 内部コード）
        self.chara_map = {
            "MIKU": "MIK", "RIN": "RIN", "LEN": "LEN", "LUKA": "LUK",
            "KAITO": "KAI", "MEIKO": "MEI", "NERU": "NER", "HAKU": "HAK",
            "SAKINE": "SAK", "TETO": "TET"
        }
        # Map Internal Code -> Display Name（内部コード -> 表示名）
        self.chara_reverse_map = {v: k for k, v in self.chara_map.items()}
        
        # キャラクター枠
        ttk.Combobox(frame_right, textvariable=self.app.pd_chara_var, values=self.chara_display_order, state='readonly').pack(fill='x', pady=(0, 10))

        # モジュール名に一致
        ttk.Label(frame_right, text=self.trans.get("module_name_contains")).pack(anchor='w')
        self.app.pd_match_var = tk.StringVar()
        self.app.pd_match_entry = ttk.Entry(frame_right, textvariable=self.app.pd_match_var)
        self.app.pd_match_entry.pack(fill='x', pady=(0, 10))
        self.app.enable_text_undo_redo(self.app.pd_match_entry)

        # モジュール名に一致しない
        ttk.Label(frame_right, text=self.trans.get("module_exclude")).pack(anchor='w')
        self.app.pd_exclude_var = tk.StringVar()
        self.app.pd_exclude_entry = ttk.Entry(frame_right, textvariable=self.app.pd_exclude_var)
        self.app.pd_exclude_entry.pack(fill='x', pady=(0, 10))
        self.app.enable_text_undo_redo(self.app.pd_exclude_entry)

        # Pose ID選択
        ttk.Label(frame_right, text=self.trans.get("pose_id")).pack(anchor='w')
        self.app.pd_pose_id_var = tk.StringVar()
        self.app.pd_pose_id_combo = ttk.Combobox(frame_right, textvariable=self.app.pd_pose_id_var)
        self.app.pd_pose_id_combo.pack(fill='x', pady=(0, 10))
        self.app.pd_pose_id_combo.bind('<Button-1>', self.refresh_pose_id_combo)

        # Scale設定
        ttk.Label(frame_right, text=self.trans.get("scale")).pack(anchor='w')
        self.app.pd_scale_var = tk.StringVar()
        self.app.pd_scale_entry = ttk.Entry(frame_right, textvariable=self.app.pd_scale_var)
        self.app.pd_scale_entry.pack(fill='x', pady=(0, 10))
        self.app.enable_text_undo_redo(self.app.pd_scale_entry)

        # 更新（保存）
        ttk.Button(frame_right, text=self.trans.get("update_save_file"), command=self.save_pose_data).pack(pady=10)

        self.refresh_pose_files()  # This will call refresh_pose_data_list with select_first=True（最初のファイルを選択）

    # Pose IDコンボボックス更新 
    def refresh_pose_id_combo(self, event=None):
        values = []
        if self.app.pose_id_map.has_section('PoseIDs'):
            for key, value in self.app.pose_id_map.items('PoseIDs'):
                values.append(f"{value} ({key})")
        self.app.pd_pose_id_combo['values'] = values

    # ポーズファイルコンボボックス更新
    def refresh_pose_files(self):
        files = [f for f in os.listdir(self.app.utils.pose_data_dir) if f.endswith('.ini')]
        self.app.pose_file_combo['values'] = files
        # ファイルが存在する場合
        if files:
            if not self.app.pose_file_combo.get() or self.app.pose_file_combo.get() not in files:
                self.app.pose_file_combo.current(0)
            self.load_pose_data_file()
        # ファイルが存在しない場合
        else:
            self.app.pose_file_combo.set('')
            self.app.current_pose_file_path = None
            self.app.current_pose_config = None
            self.refresh_pose_data_list()
            # Clear fields（フィールドをクリア）
            self.app.pd_section_suffix_var.set("")
            self.app.pd_chara_var.set("")
            self.app.pd_match_var.set("")
            self.app.pd_exclude_var.set("")
            self.app.pd_pose_id_var.set("")
            self.app.pd_scale_var.set("")

    # ポーズファイルの読み込み
    def load_pose_data_file(self, event=None):
        filename = self.app.pose_file_combo.get()
        if not filename: return
        
        self.app.current_pose_file_path = os.path.join(self.app.utils.pose_data_dir, filename)
        self.app.current_pose_config = self.app.utils.load_config(self.app.current_pose_file_path)
        self.refresh_pose_data_list(select_first=True)

    # ポーズデータリストの更新
    def refresh_pose_data_list(self, select_first=False):
        # 現在の選択を保存
        last_selection = self.app.selected_pose_data_section

        self.app.pose_data_listbox.delete(0, 'end')
        if not self.app.current_pose_config: return
        for section in self.app.current_pose_config.sections():
            if section.startswith('PoseScaleSetting_'):
                self.app.pose_data_listbox.insert('end', section)
        
        # 選択を復元
        restored = False
        if last_selection:
            items = self.app.pose_data_listbox.get(0, 'end')
            try:
                idx = items.index(last_selection)
                self.app.pose_data_listbox.selection_set(idx)
                self.app.pose_data_listbox.activate(idx)
                # Ensure UI is updated
                self.on_pose_data_select(None)
                restored = True
            except ValueError:
                pass # Previous selection not found

        # Select first item only on initial load if restoration failed
        if select_first and not restored and self.app.pose_data_listbox.size() > 0:
            self.app.pose_data_listbox.selection_set(0)
            # Directly call handler to ensure UI is updated
            self.on_pose_data_select(None)

    # ポーズデータリストの選択
    def on_pose_data_select(self, event):
        selection = self.app.pose_data_listbox.curselection()
        # 選択がなければ
        if not selection or not self.app.current_pose_config: 
            self.app.selected_pose_data_section = None
            return
        
        # 選択されたセクションを取得
        section = self.app.pose_data_listbox.get(selection[0])
        self.app.selected_pose_data_section = section
        
        # セクション名を取得
        suffix = section.replace("PoseScaleSetting_", "", 1)
        self.app.pd_section_suffix_var.set(suffix)
        
        # キャラクターを取得
        code = self.app.current_pose_config.get(section, 'Chara', fallback='')
        display_name = self.chara_reverse_map.get(code, code) # Fallback to code if not found
        self.app.pd_chara_var.set(display_name)
        
        # モジュール名を取得
        self.app.pd_match_var.set(self.app.current_pose_config.get(section, 'ModuleNameContains', fallback=''))
        self.app.pd_exclude_var.set(self.app.current_pose_config.get(section, 'ModuleExclude', fallback=''))
        
        # Pose IDを取得（表示名）
        pose_id = self.app.current_pose_config.get(section, 'PoseID', fallback='')
        display_val = pose_id
        # Pose IDが存在する場合
        if self.app.pose_id_map.has_section('PoseIDs'):
            name = self.app.pose_id_map.get('PoseIDs', pose_id, fallback=None)
            # 名前が存在する場合
            if name:
                display_val = f"{name} ({pose_id})"
        self.app.pd_pose_id_var.set(display_val)
        
        self.app.pd_scale_var.set(self.app.current_pose_config.get(section, 'Scale', fallback='')) # スケールを取得

    # ポーズデータの追加
    def add_pose_data(self):
        # ファイルが存在しない場合
        if not self.app.current_pose_config:
            CustomMessagebox.show_error(self.trans.get("error"), self.trans.get("no_file_selected"), self.app.root)
            return
        self.app.history.snapshot('data')

        # 新しいセクション名を生成
        base_suffix = "New"
        suffix = base_suffix
        counter = 1
        # セクション名が存在する場合
        while self.app.current_pose_config.has_section(f"PoseScaleSetting_{suffix}"):
            suffix = f"{base_suffix}_{counter}"
            counter += 1

        # 新しいセクションを追加    
        section = f"PoseScaleSetting_{suffix}"
        self.app.current_pose_config.add_section(section)
        self.app.current_pose_config.set(section, 'Chara', '')
        self.app.current_pose_config.set(section, 'ModuleNameContains', '')
        self.app.current_pose_config.set(section, 'ModuleExclude', '')
        self.app.current_pose_config.set(section, 'PoseID', '')
        self.app.current_pose_config.set(section, 'Scale', '')
        
        # 新しいセクションを保存
        self.app.utils.save_config(self.app.current_pose_config, self.app.current_pose_file_path)
        self.refresh_pose_data_list()
        self.app.select_listbox_item(self.app.pose_data_listbox, section)

    # ポーズデータの複製
    def duplicate_pose_data(self):
        if not self.app.selected_pose_data_section or not self.app.current_pose_config: return
        self.app.history.snapshot('data')
        
        # 既存のセクション名を取得
        old_section = self.app.selected_pose_data_section
        base_suffix = old_section.replace("PoseScaleSetting_", "", 1) + "_Copy"
        suffix = base_suffix
        counter = 1
        # セクション名が存在する場合
        while self.app.current_pose_config.has_section(f"PoseScaleSetting_{suffix}"):
            suffix = f"{base_suffix}_{counter}"
            counter += 1
            
        # 新しいセクションを追加
        new_section = f"PoseScaleSetting_{suffix}"
        self.app.current_pose_config.add_section(new_section)
        for key, value in self.app.current_pose_config.items(old_section):
            self.app.current_pose_config.set(new_section, key, value)

        # 新しいセクションを保存    
        self.app.utils.save_config(self.app.current_pose_config, self.app.current_pose_file_path)
        self.refresh_pose_data_list()
        self.app.select_listbox_item(self.app.pose_data_listbox, new_section)

    # ポーズデータの移動
    def move_pose_data(self, direction):
        selection = self.app.pose_data_listbox.curselection()
        # 選択項目が存在しない場合
        if not selection or not self.app.current_pose_config: return
        idx = selection[0]
        # 最初の項目を移動できない
        if direction == -1 and idx == 0: return
        # 最後の項目を移動できない
        if direction == 1 and idx == self.app.pose_data_listbox.size() - 1: return
        
        self.app.history.snapshot('data')     # 保存
        
        # セクションを取得
        sections = self.app.current_pose_config.sections()
        pose_sections = [s for s in sections if s.startswith('PoseScaleSetting_')]
        
        # 現在のセクションと目標のセクションを取得
        current_section = pose_sections[idx]
        target_section = pose_sections[idx + direction]
        
        # セクションの位置を交換
        full_idx1 = sections.index(current_section)
        full_idx2 = sections.index(target_section)
        sections[full_idx1], sections[full_idx2] = sections[full_idx2], sections[full_idx1]
        
        # 新しいセクションを追加
        new_config = configparser.ConfigParser()
        new_config.optionxform = str
        for s in sections:
            new_config.add_section(s)
            for k, v in self.app.current_pose_config.items(s):
                new_config.set(s, k, v)
        self.app.current_pose_config = new_config
        
        # 新しいセクションを保存
        self.app.utils.save_config(self.app.current_pose_config, self.app.current_pose_file_path)
        self.refresh_pose_data_list()
        self.app.pose_data_listbox.selection_set(idx + direction)
        self.app.pose_data_listbox.event_generate("<<ListboxSelect>>")

    # ポーズデータの削除
    def delete_pose_data(self):
        selection = self.app.pose_data_listbox.curselection()
        # 選択項目が存在しない場合
        if not selection or not self.app.current_pose_config: return
        section = self.app.pose_data_listbox.get(selection[0])
        self.app.history.snapshot('data')
        
        idx = selection[0]
        self.app.current_pose_config.remove_section(section)
        self.app.utils.save_config(self.app.current_pose_config, self.app.current_pose_file_path)
        self.app.selected_pose_data_section = None
        self.refresh_pose_data_list()
        
        # Select adjacent item
        count = self.app.pose_data_listbox.size()
        if count > 0:
            new_idx = idx if idx < count else count - 1
            self.app.pose_data_listbox.selection_set(new_idx)
            self.app.pose_data_listbox.activate(new_idx)
            self.app.pose_data_listbox.event_generate("<<ListboxSelect>>")

    # ポーズデータの保存
    def save_pose_data(self):
        # ファイルが存在しない場合
        if not self.app.current_pose_config:
            CustomMessagebox.show_error(self.trans.get("error"), self.trans.get("no_file_selected"), self.app.root)
            return
        
        # セクション名を取得
        suffix = normalize_text(self.app.pd_section_suffix_var.get())
        # セクション名が存在しない場合
        if not suffix:
            CustomMessagebox.show_error(self.trans.get("error"), self.trans.get("req_suffix"), self.app.root)
            return
        new_section = f"PoseScaleSetting_{suffix}"
        
        # 既存のセクション名と異なる場合
        if self.app.selected_pose_data_section and self.app.selected_pose_data_section != new_section:
            # 新しいセクション名と既存のセクション名が異なる場合
            if self.app.current_pose_config.has_section(new_section):
                CustomMessagebox.show_error(self.trans.get("error"), self.trans.get("duplicate_section_error", new_section), self.app.root)
                return
            # 既存のセクション名が存在する場合
            if self.app.current_pose_config.has_section(self.app.selected_pose_data_section):
                sections = self.app.current_pose_config.sections()
                new_config = configparser.ConfigParser()
                new_config.optionxform = str
                for section in sections:
                    if section == self.app.selected_pose_data_section:
                        new_config.add_section(new_section)
                        for k, v in self.app.current_pose_config.items(section, raw=True):
                            new_config.set(new_section, k, v)
                    else:
                        new_config.add_section(section)
                        for k, v in self.app.current_pose_config.items(section, raw=True):
                            new_config.set(section, k, v)
                self.app.current_pose_config = new_config
        
        # 新しいセクション名が存在しない場合
        if not self.app.current_pose_config.has_section(new_section):
            self.app.current_pose_config.add_section(new_section)
            
        # データを設定（カンマ正規化を適用）
        display_name = self.app.pd_chara_var.get()
        code = self.chara_map.get(display_name, display_name) # Fallback to display name if not found（表示名が見つからない場合は表示名を使用する）
        # スナップショットロジックの後に移動
        match_val = normalize_comma_separated_string(self.app.pd_match_var.get())
        exclude_val = normalize_comma_separated_string(self.app.pd_exclude_var.get())
        
        # PoseIDとScaleの検証
        raw_val = normalize_text(self.app.pd_pose_id_var.get())
        if '(' in raw_val and raw_val.endswith(')'):        # ポーズIDが括弧で囲まれている場合
            pose_id = raw_val.split('(')[-1].strip(')')     # ポーズIDを括弧で囲まれた部分に変換
        else:
            pose_id = raw_val   # ポーズIDが括弧で囲まれていない場合
        
        # Convert full-width numbers to half-width（全角数字を半角に変換）
        pose_id = pose_id.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

        scale_val = normalize_text(self.app.pd_scale_var.get())
        # Convert full-width numbers and period to half-width（全角数字とピリオドを半角に変換）
        scale_val = scale_val.translate(str.maketrans('０１２３４５６７８９．', '0123456789.'))

        # Check if both are empty（両方が空の場合） 
        if not pose_id and not scale_val:
             CustomMessagebox.show_error(self.trans.get("error"), "Either Pose ID or Scale must be set.", self.app.root)
             return

        # PoseIDの検証
        if pose_id:
            if not pose_id.isdigit():   # ポーズIDが半角数字でない場合
                 CustomMessagebox.show_error(self.trans.get("error"), "Pose ID must be half-width numbers only.", self.app.root)
                 return

        # Scaleの検証
        if scale_val:
            if not all(c.isdigit() or c == '.' for c in scale_val):   # Scaleが半角数字とピリオドでない場合
                 CustomMessagebox.show_error(self.trans.get("error"), "Scale must be half-width numbers and period only.", self.app.root)
                 return
            
            try:
                # Auto-format 1 -> 1.0（1を1.0に自動変換）
                if '.' not in scale_val:
                    scale_val = f"{scale_val}.0"
                else:
                    # Ensure valid float（有効な浮動小数点数を確保）
                    float(scale_val)
            except ValueError:
                 CustomMessagebox.show_error(self.trans.get("error"), "Invalid Scale value.", self.app.root)
                 return

        # セクション名を取得
        suffix = normalize_text(self.app.pd_section_suffix_var.get())
        # セクション名が存在しない場合
        if not suffix:
            CustomMessagebox.show_error(self.trans.get("error"), self.trans.get("req_suffix"), self.app.root)
            return
        new_section = f"PoseScaleSetting_{suffix}"

        # Check for changes
        has_changes = False
        if self.app.selected_pose_data_section != new_section:
            has_changes = True
        else:
            # 値の比較用にconfig値を正規化
            current_chara = self.app.current_pose_config.get(new_section, 'Chara', fallback='')
            current_match = normalize_comma_separated_string(self.app.current_pose_config.get(new_section, 'ModuleNameContains', fallback=''))
            current_exclude = normalize_comma_separated_string(self.app.current_pose_config.get(new_section, 'ModuleExclude', fallback=''))
            current_pose_id = self.app.current_pose_config.get(new_section, 'PoseID', fallback='')
            current_scale = self.app.current_pose_config.get(new_section, 'Scale', fallback='')
            
            if (current_chara != code or
                current_match != normalize_comma_separated_string(self.app.pd_match_var.get()) or
                current_exclude != normalize_comma_separated_string(self.app.pd_exclude_var.get()) or
                current_pose_id != pose_id or
                current_scale != scale_val):
                has_changes = True
            
            # 生の値が正規化された値と異なるかどうかを確認する（UI更新をトリガーするため）
            if not has_changes:
                if (self.app.pd_match_var.get() != normalize_comma_separated_string(self.app.pd_match_var.get()) or
                    self.app.pd_exclude_var.get() != normalize_comma_separated_string(self.app.pd_exclude_var.get())):
                    has_changes = True

                
        if not has_changes:
            return
        
        # 変更が検出された場合のみスナップショットを取る
        self.app.history.snapshot('data')

        self.app.current_pose_config.set(new_section, 'Chara', code)
        self.app.current_pose_config.set(new_section, 'ModuleNameContains', match_val)
        self.app.current_pose_config.set(new_section, 'ModuleExclude', exclude_val)
        self.app.current_pose_config.set(new_section, 'PoseID', pose_id) # ポーズIDを設定
        self.app.current_pose_config.set(new_section, 'Scale', scale_val) # Scaleを設定
        
        self.app.utils.save_config(self.app.current_pose_config, self.app.current_pose_file_path) # ポーズデータを保存
        self.refresh_pose_data_list() # ポーズデータリストを更新
        self.app.select_listbox_item(self.app.pose_data_listbox, new_section) # 新しいセクションを選択
        
        # 再選択後にUIを更新して訂正を表示（再選択はon_pose_data_selectをトリガーし、configから読み込むので、その後にUIを更新する必要がある）
        # プログラム変更フラグを設定して逆元スタック汚染を防ぐ
        
        # カンマ区切りフィールドを正規化してUIに反映
        if hasattr(self.app.pd_match_entry, 'programmatic_change'):
            self.app.pd_match_entry.programmatic_change = True
        self.app.pd_match_var.set(normalize_comma_separated_string(self.app.pd_match_var.get()))
        if hasattr(self.app.pd_match_entry, 'programmatic_change'):
            self.app.pd_match_entry.programmatic_change = False
            self.app.pd_match_entry.last_value = self.app.pd_match_var.get()
            
        if hasattr(self.app.pd_exclude_entry, 'programmatic_change'):
            self.app.pd_exclude_entry.programmatic_change = True
        self.app.pd_exclude_var.set(normalize_comma_separated_string(self.app.pd_exclude_var.get()))
        if hasattr(self.app.pd_exclude_entry, 'programmatic_change'):
            self.app.pd_exclude_entry.programmatic_change = False
            self.app.pd_exclude_entry.last_value = self.app.pd_exclude_var.get()
        
        # PoseIDの表示値を更新（括弧付き表示名に変換）
        if pose_id:
            display_val = pose_id
            if self.app.pose_id_map.has_section('PoseIDs'):
                name = self.app.pose_id_map.get('PoseIDs', pose_id, fallback=None)
                if name:
                    display_val = f"{name} ({pose_id})"
            self.app.pd_pose_id_var.set(display_val)
        
        # Scaleを補正後の値に更新
        if hasattr(self.app.pd_scale_entry, 'programmatic_change'):
            self.app.pd_scale_entry.programmatic_change = True
        self.app.pd_scale_var.set(scale_val)
        if hasattr(self.app.pd_scale_entry, 'programmatic_change'):
            self.app.pd_scale_entry.programmatic_change = False
            self.app.pd_scale_entry.last_value = scale_val

    # 新しいポーズファイルを作成
    def create_new_pose_file(self):
        # PoseScaleDataフォルダにファイルを作成するためのカスタムダイアログ）
        filename = simpledialog.askstring(self.trans.get("create_new_file"), self.trans.get("enter_filename"))
        if not filename: return
        
        # ファイル名がiniで終わっていない場合は自動的に追加
        if not filename.endswith('.ini'):
            filename += '.ini'
            
        filepath = os.path.join(self.app.utils.pose_data_dir, filename)
        
        # ファイルが既に存在する場合はエラー
        if os.path.exists(filepath):
            CustomMessagebox.show_error(self.trans.get("error"), f"File '{filename}' already exists.", self.app.root)
            return
            
        try:
            # 新しいファイルを作成する前にスナップショットを取る
            self.app.history.snapshot('data')
            
            with open(filepath, 'w', encoding='utf-8-sig') as f:
                f.write("") # 空のファイルを作成
            self.refresh_pose_files()
            self.app.pose_file_combo.set(filename)
            self.load_pose_data_file()
        except Exception as e:
            CustomMessagebox.show_error(self.trans.get("error"), self.trans.get("failed_create", e), self.app.root)

    # 現在のポーズファイルを複製
    def duplicate_current_pose_file(self):
        # 現在のポーズファイルが存在しない場合は何もしない
        if not self.app.current_pose_file_path: return
        
        # 現在のファイル名を取得
        old_filename = os.path.basename(self.app.current_pose_file_path)
        base_name, ext = os.path.splitext(old_filename)
        default_new_name = f"{base_name}_Copy"
        
        # 新しいファイル名を入力するダイアログを表示
        new_filename = simpledialog.askstring(self.trans.get("duplicate_file"), self.trans.get("enter_filename"), initialvalue=default_new_name)
        if not new_filename: return
        
        # ファイル名がiniで終わっていない場合は自動的に追加
        if not new_filename.endswith('.ini'):
            new_filename += '.ini'

        # 新しいファイルパスを生成    
        new_filepath = os.path.join(self.app.utils.pose_data_dir, new_filename)
        
        # 新しいファイルが既に存在する場合はエラー
        if os.path.exists(new_filepath):
            CustomMessagebox.show_error(self.trans.get("error"), f"File '{new_filename}' already exists.", self.app.root)
            return
            
        try:
            # 新しいファイルを作成する前にスナップショットを取る
            self.app.history.snapshot('data')
            
            import shutil
            shutil.copy2(self.app.current_pose_file_path, new_filepath)
            self.refresh_pose_files()
            self.app.pose_file_combo.set(new_filename)
            self.load_pose_data_file()
        except Exception as e:
            CustomMessagebox.show_error(self.trans.get("error"), f"Failed to duplicate file: {e}", self.app.root)

    # 現在のポーズファイルをリネーム
    def rename_current_pose_file(self):
        # 現在のポーズファイルが存在しない場合は何もしない
        if not self.app.current_pose_file_path: return
        
        # 現在のファイル名を取得
        old_filename = os.path.basename(self.app.current_pose_file_path)
        base_name, ext = os.path.splitext(old_filename)
        
        # 初期値を渡す
        # simpledialog.askstringは標準のtkinterで初期値をサポート
        new_filename = simpledialog.askstring(self.trans.get("rename_file"), self.trans.get("enter_filename"), initialvalue=base_name)
        if not new_filename: return
        
        # ファイル名がiniで終わっていない場合は自動的に追加
        if not new_filename.endswith('.ini'):
            new_filename += '.ini'

        # 新しいファイルパスを生成    
        new_filepath = os.path.join(self.app.utils.pose_data_dir, new_filename)
        
        # 新しいファイルが既に存在する場合はエラー
        if os.path.exists(new_filepath):
            CustomMessagebox.show_error(self.trans.get("error"), f"File '{new_filename}' already exists.", self.app.root)
            return
            
        try:
            # Snapshot before renaming file
            self.app.history.snapshot('data')
            
            os.rename(self.app.current_pose_file_path, new_filepath)
            self.app.current_pose_file_path = new_filepath
            self.refresh_pose_files()
            self.app.pose_file_combo.set(new_filename)
            # Reload data to ensure UI is consistent（UIを一致させるためにデータを再読み込み）
            self.load_pose_data_file()
        except Exception as e:
            CustomMessagebox.show_error(self.trans.get("error"), f"Failed to rename file: {e}", self.app.root)

    # 現在のポーズファイルを削除
    def delete_current_pose_file(self):
        if not self.app.current_pose_file_path: return
        filename = os.path.basename(self.app.current_pose_file_path)
        # 削除時に確認はしない（Undoで対応）
        if True:
            try:
                # Snapshot before deletion for undo
                self.app.history.snapshot('data')
                
                os.remove(self.app.current_pose_file_path)
                self.app.current_pose_file_path = None
                self.app.current_pose_config = None
                self.refresh_pose_files()
                # ファイルが残っていない場合、フィールドをクリアする
            except Exception as e:
                CustomMessagebox.show_error(self.trans.get("error"), f"Failed to delete file: {e}", self.app.root)
