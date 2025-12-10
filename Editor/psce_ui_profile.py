import tkinter as tk
from tkinter import ttk, messagebox
import configparser
import os
from psce_util import CustomMessagebox, normalize_comma_separated_string

# TomlProfileタブUIクラス
class ProfileTab:
    # コンストラクタ
    def __init__(self, notebook, app):
        self.app = app
        self.trans = app.trans
        self.tab = ttk.Frame(notebook)
        notebook.add(self.tab, text=self.trans.get("tab_profiles"))
        self.create_widgets()

    # UI要素の作成
    def create_widgets(self):
        paned = ttk.PanedWindow(self.tab, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=5, pady=5)

        # リスト表示用のフレーム
        frame_left = ttk.Frame(paned)
        # 編集用のフレーム
        frame_right = ttk.LabelFrame(paned, text=self.trans.get("edit_profile"), padding=10)
        paned.add(frame_left, weight=1)
        paned.add(frame_right, weight=2)

        # プロファイルリスト
        self.app.profile_listbox = tk.Listbox(frame_left, exportselection=False)
        self.app.profile_listbox.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(frame_left, orient='vertical', command=self.app.profile_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.app.profile_listbox.config(yscrollcommand=scrollbar.set)
        self.app.profile_listbox.bind('<<ListboxSelect>>', self.on_profile_select)

        # ボタンフレーム
        frame_btns = ttk.Frame(frame_left)
        frame_btns.pack(fill='x', pady=5)
        
        frame_btns1 = ttk.Frame(frame_btns)
        frame_btns1.pack(fill='x') # ボタンを水平方向に配置
        ttk.Button(frame_btns1, text=self.trans.get("add_new"), command=self.add_profile).pack(side='left', expand=True, fill='x') # 新規追加
        ttk.Button(frame_btns1, text=self.trans.get("duplicate"), command=self.duplicate_profile).pack(side='left', expand=True, fill='x') # ドラッグコピー
        
        frame_btns2 = ttk.Frame(frame_btns)
        frame_btns2.pack(fill='x')
        ttk.Button(frame_btns2, text=self.trans.get("up"), command=lambda: self.move_profile(-1)).pack(side='left', expand=True, fill='x') # 上移動
        ttk.Button(frame_btns2, text=self.trans.get("down"), command=lambda: self.move_profile(1)).pack(side='left', expand=True, fill='x') # 下移動
        
        frame_btns3 = ttk.Frame(frame_btns)
        frame_btns3.pack(fill='x')
        ttk.Button(frame_btns3, text=self.trans.get("delete"), command=self.delete_profile).pack(side='left', expand=True, fill='x') # 削除

        # Edit Fields（編集フィールド）
        ttk.Label(frame_right, text=self.trans.get("section_name")).pack(anchor='w')
        frame_section = ttk.Frame(frame_right)
        frame_section.pack(fill='x', pady=(0, 10))
        ttk.Label(frame_section, text="TomlProfile_").pack(side='left') # TomlProfileセクション名
        self.app.prof_section_suffix_var = tk.StringVar()
        entry_suffix = ttk.Entry(frame_section, textvariable=self.app.prof_section_suffix_var)
        entry_suffix.pack(side='left', fill='x', expand=True)
        self.app.enable_text_undo_redo(entry_suffix)

        # ModuleMatch（モジュール名一致条件）
        ttk.Label(frame_right, text=self.trans.get("module_match")).pack(anchor='w')
        self.app.prof_match_var = tk.StringVar()
        entry_match = ttk.Entry(frame_right, textvariable=self.app.prof_match_var)
        entry_match.pack(fill='x', pady=(0, 10))
        self.app.enable_text_undo_redo(entry_match)

        # ModuleExclude（モジュール名除外条件）
        ttk.Label(frame_right, text=self.trans.get("module_exclude")).pack(anchor='w')
        self.app.prof_exclude_var = tk.StringVar()
        entry_exclude = ttk.Entry(frame_right, textvariable=self.app.prof_exclude_var)
        entry_exclude.pack(fill='x', pady=(0, 10))
        self.app.enable_text_undo_redo(entry_exclude)

        # ConfigFile（設定ファイル）
        ttk.Label(frame_right, text=self.trans.get("config_file")).pack(anchor='w')
        frame_config = ttk.Frame(frame_right)
        frame_config.pack(fill='x', pady=(0, 10))
        self.app.prof_config_var = tk.StringVar()
        self.app.prof_config_combo = ttk.Combobox(frame_config, textvariable=self.app.prof_config_var, state='readonly')
        self.app.prof_config_combo.pack(side='left', fill='x', expand=True)
        self.app.prof_config_combo.bind('<Button-1>', self.refresh_config_file_combo)
        
        # EditThisFile（このファイルを編集）
        ttk.Button(frame_config, text=self.trans.get("edit_this_file"), command=self.jump_to_pose_editor).pack(side='left', padx=(5, 0))

        # PoseFileOutput（ポーズファイル出力）
        ttk.Label(frame_right, text=self.trans.get("pose_file_output")).pack(anchor='w')
        self.app.prof_pose_file_var = tk.StringVar()
        entry_pose = ttk.Entry(frame_right, textvariable=self.app.prof_pose_file_var)
        entry_pose.pack(fill='x', pady=(0, 10))
        self.app.enable_text_undo_redo(entry_pose)

        # UpdateSaveProfile（更新保存プロファイル）
        ttk.Button(frame_right, text=self.trans.get("update_save_profile"), command=self.save_profile).pack(pady=10)

        self.refresh_profile_list(select_first=True)

    # TomlProfileの追加
    def add_profile(self):
        self.app.history.snapshot('profile')
        base_suffix = "New"
        suffix = base_suffix
        counter = 1
        while self.app.profile_config.has_section(f"TomlProfile_{suffix}"):
            suffix = f"{base_suffix}_{counter}"
            counter += 1
        
        # TomlProfileの追加
        section = f"TomlProfile_{suffix}"
        self.app.profile_config.add_section(section)
        self.app.profile_config.set(section, 'ModuleMatch', '')
        self.app.profile_config.set(section, 'ModuleExclude', '')
        self.app.profile_config.set(section, 'ConfigFile', 'PoseScaleData.ini') # Default value
        self.app.profile_config.set(section, 'PoseFileName', 'gm_module_pose_tbl') # Default value
        
        # TomlProfileの保存
        self.app.utils.save_config(self.app.profile_config, self.app.utils.profile_config_path)
        self.refresh_profile_list()
        self.app.select_listbox_item(self.app.profile_listbox, section)

    # プロファイルリストの更新
    def refresh_profile_list(self, select_first=False):
        self.app.profile_listbox.delete(0, 'end')
        if not self.app.profile_config: return
        
        for section in self.app.profile_config.sections():
            if section.startswith('TomlProfile_'):
                self.app.profile_listbox.insert('end', section)
        
        # Select first item only on initial load
        if select_first and self.app.profile_listbox.size() > 0:
            self.app.profile_listbox.selection_set(0)
            # Directly call handler to ensure UI is updated
            self.on_profile_select(None)

    # ConfigFileコンボボックスの更新
    def refresh_config_file_combo(self, event=None):
        files = []
        if os.path.exists(self.app.utils.pose_data_dir):
            for f in os.listdir(self.app.utils.pose_data_dir):
                if f.endswith('.ini'):
                    files.append(os.path.splitext(f)[0])
        self.app.prof_config_combo['values'] = sorted(files)

    # TomlProfileの選択時処理
    def on_profile_select(self, event):
        selection = self.app.profile_listbox.curselection()
        if not selection:
            self.app.selected_profile_section = None
            return

        section = self.app.profile_listbox.get(selection[0])
        self.app.selected_profile_section = section
        
        # Load values
        suffix = section.replace("TomlProfile_", "", 1)
        self.app.prof_section_suffix_var.set(suffix)
        self.app.prof_match_var.set(self.app.profile_config.get(section, 'ModuleMatch', fallback=''))
        self.app.prof_exclude_var.set(self.app.profile_config.get(section, 'ModuleExclude', fallback=''))
        self.app.prof_config_var.set(self.app.profile_config.get(section, 'ConfigFile', fallback=''))
        self.app.prof_pose_file_var.set(self.app.profile_config.get(section, 'PoseFileName', fallback=''))

    # TomlProfileの複製
    def duplicate_profile(self):
        if not self.app.selected_profile_section: return
        self.app.history.snapshot('profile')
        
        old_section = self.app.selected_profile_section
        base_suffix = old_section.replace("TomlProfile_", "", 1) + "_Copy"
        suffix = base_suffix
        counter = 1
        while self.app.profile_config.has_section(f"TomlProfile_{suffix}"):
            suffix = f"{base_suffix}_{counter}"
            counter += 1
            
        new_section = f"TomlProfile_{suffix}"
        self.app.profile_config.add_section(new_section)
        for k, v in self.app.profile_config.items(old_section):
            self.app.profile_config.set(new_section, k, v)
            
        self.app.utils.save_config(self.app.profile_config, self.app.utils.profile_config_path)
        self.refresh_profile_list()
        self.app.select_listbox_item(self.app.profile_listbox, new_section)

    # TomlProfileの移動
    def move_profile(self, direction):
        selection = self.app.profile_listbox.curselection()
        if not selection: return
        idx = selection[0]
        
        # Check bounds
        if direction == -1 and idx == 0: return
        if direction == 1 and idx == self.app.profile_listbox.size() - 1: return
        
        self.app.history.snapshot('profile')
        
        sections = self.app.profile_config.sections()
        profile_sections = [s for s in sections if s.startswith('TomlProfile_')]
        
        current_section = profile_sections[idx]
        target_section = profile_sections[idx + direction]
        
        full_idx1 = sections.index(current_section)
        full_idx2 = sections.index(target_section)
        sections[full_idx1], sections[full_idx2] = sections[full_idx2], sections[full_idx1]
        
        # Rebuild config（再構築）
        new_config = configparser.ConfigParser()
        new_config.optionxform = str
        for s in sections:
            new_config.add_section(s)
            for k, v in self.app.profile_config.items(s):
                new_config.set(s, k, v)
        self.app.profile_config = new_config
        
        self.app.utils.save_config(self.app.profile_config, self.app.utils.profile_config_path)
        self.refresh_profile_list()
        self.app.profile_listbox.selection_set(idx + direction)
        self.app.profile_listbox.event_generate("<<ListboxSelect>>")


    # TomlProfileの削除
    def delete_profile(self):
        selection = self.app.profile_listbox.curselection()
        if not selection: return
        section = self.app.profile_listbox.get(selection[0])
        
        # No confirmation as requested（確認なしで削除）
        self.app.history.snapshot('profile')
        
        idx = selection[0]
        self.app.profile_config.remove_section(section)
        self.app.utils.save_config(self.app.profile_config, self.app.utils.profile_config_path)
        self.app.selected_profile_section = None
        self.refresh_profile_list()
        
        # 隣接する項目を選択して、その内容を読み込む
        count = self.app.profile_listbox.size()
        if count > 0:
            new_idx = idx if idx < count else count - 1
            self.app.profile_listbox.selection_set(new_idx)
            self.app.profile_listbox.activate(new_idx)
            # 選択されたプロファイルを読み込む
            self.on_profile_select(None)

    # TomlProfileの保存
    def save_profile(self):
        suffix = self.app.prof_section_suffix_var.get()
        if not suffix:
            CustomMessagebox.show_error(self.trans.get("error"), self.trans.get("req_suffix"), self.app.root)
            return
        new_section = f"TomlProfile_{suffix}"

        # 現在のセクションと異なる場合
        if self.app.selected_profile_section and self.app.selected_profile_section != new_section:
            # 新しいセクションが存在する場合
            if self.app.profile_config.has_section(new_section):
                CustomMessagebox.show_error(self.trans.get("error"), self.trans.get("duplicate_section_error", new_section), self.app.root)
                return
            # 現在のセクションを新しいセクションに移動
            if self.app.profile_config.has_section(self.app.selected_profile_section):
                sections = self.app.profile_config.sections()
                new_config = configparser.ConfigParser()
                new_config.optionxform = str
                # 新しいセクションを追加
                for section in sections:
                    # 現在のセクションを新しいセクションに移動
                    if section == self.app.selected_profile_section:
                        new_config.add_section(new_section)
                        for k, v in self.app.profile_config.items(section, raw=True):
                            new_config.set(new_section, k, v)
                    else:   
                        # 他のセクションを新しいセクションに移動
                        new_config.add_section(section)
                        for k, v in self.app.profile_config.items(section, raw=True):
                            new_config.set(section, k, v)
                self.app.profile_config = new_config
        
        # セクションが存在しない場合は作成
        if not self.app.profile_config.has_section(new_section):
            self.app.profile_config.add_section(new_section)
        
        # Get values from UI（UI から値を取得してカンマ正規化を適用）
        match_val = normalize_comma_separated_string(self.app.prof_match_var.get())
        exclude_val = normalize_comma_separated_string(self.app.prof_exclude_var.get())
        config_file = self.app.prof_config_var.get()
        pose_file_name = self.app.prof_pose_file_var.get()
        
        # 半角英数と特定の記号のみを許可する
        if not all(c.isascii() and (c.isalnum() or c in ('_', '-', '.')) for c in pose_file_name):
             # エラーメッセージ表示
             CustomMessagebox.show_error(self.trans.get("error"), self.trans.get("err_filename_chars"), self.app.root)
             return

        # Check for changes (変更があるか確認)
        has_changes = False
        if self.app.selected_profile_section == new_section:
            # 同じセクション、値を比較して変更があるか確認
            current_match = normalize_comma_separated_string(self.app.profile_config.get(new_section, 'ModuleMatch', fallback=''))
            current_exclude = normalize_comma_separated_string(self.app.profile_config.get(new_section, 'ModuleExclude', fallback=''))
            current_config = self.app.profile_config.get(new_section, 'ConfigFile', fallback='')
            current_pose = self.app.profile_config.get(new_section, 'PoseFileName', fallback='')
            
            if (current_match != match_val or
                current_exclude != exclude_val or
                current_config != config_file or
                current_pose != pose_file_name):
                has_changes = True
        else:
            # セクション名が変更された
            has_changes = True
            
        if not has_changes:
            return
        
        # 変更が検出された場合のみスナップショットを取る
        self.app.history.snapshot('profile')

        # Set values（値を設定する）
        self.app.profile_config.set(new_section, 'ModuleMatch', match_val)
        self.app.profile_config.set(new_section, 'ModuleExclude', exclude_val)
        self.app.profile_config.set(new_section, 'ConfigFile', config_file)
        self.app.profile_config.set(new_section, 'PoseFileName', pose_file_name)
        
        # Save config（configを保存する）
        self.app.utils.save_config(self.app.profile_config, self.app.utils.profile_config_path)
        self.refresh_profile_list()
        self.app.select_listbox_item(self.app.profile_listbox, new_section)

    # Jump to pose editor（ポーズエディタに移動する）
    def jump_to_pose_editor(self):
        config_base = self.app.prof_config_var.get()
        if not config_base: return
        filename = f"{config_base}.ini"
        filepath = os.path.join(self.app.utils.pose_data_dir, filename)
        
        # Check if file exists（ファイルが存在するか確認する）
        if not os.path.exists(filepath):
            if CustomMessagebox.ask_yes_no(self.trans.get("file_not_found"), self.trans.get("create_it", filename), self.app.root):
                try:
                    with open(filepath, 'w', encoding='utf-8-sig') as f:
                        f.write("")
                except Exception as e:
                    CustomMessagebox.show_error(self.trans.get("error"), self.trans.get("failed_create", e), self.app.root)
                    return
            else:
                return

        self.app.notebook.select(2) # Select pose editor（ポーズエディタを選択する）
        self.app.refresh_pose_files() # Refresh pose files（ポーズファイルを更新する）
        self.app.pose_file_combo.set(filename) # Set pose file（ポーズファイルを設定する）
        self.app.load_pose_data_file() # Load pose data file（ポーズデータファイルを読み込む）
