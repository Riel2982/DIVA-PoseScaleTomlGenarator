import io
import os
import configparser

class HistoryManager:
    """
    アプリケーションの履歴（Undo/Redo）を管理するクラス。
    設定のスナップショットと、ファイルの削除操作の履歴を保持。
    タブ（コンテキスト）ごとに独立したスタックを持つ。
    """
    def __init__(self, app):
        self.app = app
        self.stacks = {
            'general': {'undo': [], 'redo': []},
            'profile': {'undo': [], 'redo': []},
            'data': {'undo': [], 'redo': []},
            'map': {'undo': [], 'redo': []},
            'key': {'undo': [], 'redo': []}
        }
        self.max_history = app.main_config.getint('DebugSettings', 'HistoryLimit', fallback=50)

    def _get_stack(self, context):
        if context not in self.stacks:
            self.stacks[context] = {'undo': [], 'redo': []}
        return self.stacks[context]

    def snapshot(self, context):
        """現在の設定状態をスナップショットとして保存"""
        if not context: return
        
        state = self._capture_current_state(context)
        state['file_moves'] = [] # List of {src, dst}
        stack = self._get_stack(context)
        
        stack['undo'].append(state)
        # 履歴を最大値を超えたら古い履歴を削除
        if len(stack['undo']) > self.max_history:
            stack['undo'].pop(0)
        stack['redo'].clear()
        self.app.update_undo_redo_buttons()

    def register_file_move(self, context, src, dst):
        """
        直前のスナップショットにファイル移動操作を紐付ける
        :param context: コンテキスト
        :param src: 移動元パス
        :param dst: 移動先パス
        """
        if not context: return
        stack = self._get_stack(context)
        if not stack['undo']: return
        
        # 直近のステートに追加
        last_state = stack['undo'][-1]
        if 'file_moves' not in last_state:
            last_state['file_moves'] = []
        last_state['file_moves'].append({'src': src, 'dst': dst})

    def undo(self, context):
        """元に戻す"""
        if not context: return
        stack = self._get_stack(context)
        
        if not stack['undo']: return
        
        state = stack['undo'].pop()
        
        # ファイル移動のUndo（逆操作：dst -> src）
        if 'file_moves' in state:
            import shutil
            for move in reversed(state['file_moves']):
                src, dst = move['src'], move['dst']
                try:
                    if os.path.exists(dst):
                        if not os.path.exists(os.path.dirname(src)):
                            os.makedirs(os.path.dirname(src))
                        shutil.move(dst, src)
                except Exception as e:
                    print(f"Failed to undo file move: {e}")

        if isinstance(state, dict):
            if state.get('type') == 'file_delete':
                # ファイル削除の取り消し（復元）
                self._restore_file(state)
                stack['redo'].append(state)
            elif state.get('type') == 'image_delete':
                # 画像削除の取り消し（ゴミ箱から戻す）
                self._restore_image(state)
                stack['redo'].append(state)
            else:
                # 設定変更の取り消し
                current_state = self._capture_current_state(context)
                # 現在の状態にもfile_movesが含まれている可能性があるので保存...
                # しかしRedo時は「この操作をやり直す」なので、popしたstateのfile_movesを使う
                stack['redo'].append(current_state)
                self._restore_state(context, state)
        
        self.app.update_undo_redo_buttons()

    def redo(self, context):
        """やり直す"""
        if not context: return
        stack = self._get_stack(context)
        
        if not stack['redo']: return
        
        state = stack['redo'].pop()
        
        # ファイル移動のRedo（順操作：src -> dst）
        if 'file_moves' in state:
            import shutil
            for move in state['file_moves']:
                src, dst = move['src'], move['dst']
                try:
                    if os.path.exists(src):
                        if not os.path.exists(os.path.dirname(dst)):
                            os.makedirs(os.path.dirname(dst))
                        shutil.move(src, dst)
                    else:
                        print(f"Redo failed: Source file not found: {src}")
                except Exception as e:
                    print(f"Failed to redo file move: {e}")

        if isinstance(state, dict):
            if state.get('type') == 'file_delete':
                # ファイル削除のやり直し（再削除）
                self._delete_file(state)
                stack['undo'].append(state)
            elif state.get('type') == 'image_delete':
                # 画像削除のやり直し（ゴミ箱へ移動）
                self._delete_image(state)
                stack['undo'].append(state)
            else:
                # 設定変更のやり直し
                current_state = self._capture_current_state(context)
                stack['undo'].append(current_state)
                self._restore_state(context, state)
            
        self.app.update_undo_redo_buttons()

    def _capture_current_state(self, context):
        # Capture state relevant to the context
        state = {}
        if context == 'general':
            state['main_config'] = self._serialize_config(self.app.main_config)
        elif context == 'profile':
            state['profile_config'] = self._serialize_config(self.app.profile_config)
            state['selected_section'] = self.app.selected_profile_section
        elif context == 'map':
            state['pose_id_map'] = self._serialize_config(self.app.pose_id_map)
            state['selected_key'] = self.app.selected_map_key
        elif context == 'data':
            state['current_pose_file'] = self.app.current_pose_file_path
            state['current_pose_config'] = self._serialize_config(self.app.current_pose_config) if self.app.current_pose_config else None
            state['selected_section'] = self.app.selected_pose_data_section
            
            # ファイルの作成/削除/リネームを検出
            if os.path.exists(self.app.utils.pose_data_dir):
                state['file_list'] = sorted([f for f in os.listdir(self.app.utils.pose_data_dir) if f.endswith('.ini')])
            else:
                state['file_list'] = []
        elif context == 'key':
            if hasattr(self.app, 'key_manager'):
                 state['key_map'] = self._serialize_config(self.app.key_manager.key_map)
        return state

    def _serialize_config(self, config):
        """設定を文字列にシリアライズする"""
        if config is None: return None
        sio = io.StringIO()
        config.write(sio)
        return sio.getvalue()

    def _restore_config(self, config_str):
        """文字列から設定を復元する"""
        if config_str is None: return None
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read_file(io.StringIO(config_str))
        return config

    def _restore_state(self, context, state):
        """設定を復元する"""
        if context == 'general':
            if 'main_config' in state:
                self.app.main_config = self._restore_config(state['main_config'])
                self.app.utils.save_config(self.app.main_config, self.app.utils.main_config_path)
                self.app.general_tab.load_settings()
        
        elif context == 'profile':
            if 'profile_config' in state:
                self.app.profile_config = self._restore_config(state['profile_config'])
                self.app.utils.save_config(self.app.profile_config, self.app.utils.profile_config_path)
                self.app.ui_profile.refresh_profile_list()
                
                # Restore selection（復元する）
                if 'selected_section' in state and state['selected_section']:
                    self.app.select_listbox_item(self.app.profile_listbox, state['selected_section'])
        
        elif context == 'map':
            if 'pose_id_map' in state:
                self.app.pose_id_map = self._restore_config(state['pose_id_map'])
                self.app.utils.save_config(self.app.pose_id_map, self.app.utils.pose_id_map_path)
                self.app.map_tab.refresh_pose_id_map_list()
                
                # Restore selection（復元する）
                if 'selected_key' in state and state['selected_key']:
                    self.app.map_tab.select_map_item_by_id(state['selected_key'])

        elif context == 'data':
            if 'current_pose_file' in state:
                target_file = state['current_pose_file']
                target_config = self._restore_config(state.get('current_pose_config'))
                
                # ファイルリストの変更（作成/削除/リネーム）
                if 'file_list' in state:
                    current_files = sorted([f for f in os.listdir(self.app.utils.pose_data_dir) if f.endswith('.ini')]) if os.path.exists(self.app.utils.pose_data_dir) else []
                    target_files = state['file_list']
                    
                    # 現在のファイルがスナップショットで存在しないファイル（作成されたファイル - 削除する）
                    files_to_delete = set(current_files) - set(target_files)
                    for filename in files_to_delete:
                        filepath = os.path.join(self.app.utils.pose_data_dir, filename)
                        try:
                            if os.path.exists(filepath):
                                os.remove(filepath)
                        except Exception as e:
                            print(f"Failed to delete file during undo: {e}")
                    
                    # スナップショットで存在していたが、現在のファイルが存在しないファイル（削除されたファイル - 作成する）
                    files_to_create = set(target_files) - set(current_files)
                    for filename in files_to_create:
                        filepath = os.path.join(self.app.utils.pose_data_dir, filename)
                        try:
                            with open(filepath, 'w', encoding='utf-8-sig') as f:
                                f.write("")
                        except Exception as e:
                            print(f"Failed to create file during undo: {e}")
                
                # 目標の設定を目標のファイルに保存する
                self.app.current_pose_file_path = target_file
                self.app.current_pose_config = target_config
                
                if target_config and target_file and os.path.exists(os.path.dirname(target_file)):
                    self.app.utils.save_config(target_config, target_file)
                
                # ファイルリストを更新して復元されたファイルを選択する
                self.app.pose_data_tab.refresh_pose_files()
                if target_file:
                    filename = os.path.basename(target_file)
                    self.app.pose_file_combo.set(filename)
                    self.app.pose_data_tab.load_pose_data_file()
                    
                    # 選択されたセクションを復元する
                    if 'selected_section' in state and state['selected_section']:
                        self.app.select_listbox_item(self.app.pose_data_listbox, state['selected_section'])
                    elif self.app.pose_data_listbox.size() > 0:
                        self.app.pose_data_listbox.selection_set(0)
                        self.app.pose_data_listbox.event_generate("<<ListboxSelect>>")

        elif context == 'key':
            if 'key_map' in state and hasattr(self.app, 'key_manager'):
                self.app.key_manager.key_map = self._restore_config(state['key_map'])
                self.app.key_manager.save_key_map()
                self.app.ui_key.refresh_key_list()

    def _restore_file(self, state):
        """削除されたファイルを復元"""
        path = state['path']
        content = state['content']
        try:
            with open(path, 'w', encoding='utf-8-sig') as f:
                f.write(content)
            
            # UI更新
            if hasattr(self.app, 'pose_data_tab'):
                self.app.pose_data_tab.refresh_pose_files()
                # 復元したファイルを選択状態にする
                filename = os.path.basename(path)
                self.app.pose_file_combo.set(filename)
                self.app.pose_data_tab.load_pose_data_file()
                
        except Exception as e:
            print(f"Failed to restore file: {e}")

    def _delete_file(self, state):
        """ファイルを再削除"""
        path = state['path']
        try:
            if os.path.exists(path):
                os.remove(path)
            
            # UI更新
            if hasattr(self.app, 'pose_data_tab'):
                # 現在開いているファイルが削除対象なら閉じる
                if self.app.current_pose_file_path == path:
                    self.app.current_pose_file_path = None
                    self.app.current_pose_config = None
                    
                self.app.pose_data_tab.refresh_pose_files()
                
        except Exception as e:
            print(f"Failed to delete file: {e}")

    def _restore_image(self, state):
        """画像をゴミ箱から復元"""
        path = state['path']
        trash_path = state['trash_path']
        try:
            if os.path.exists(trash_path):
                # 元の場所に戻す
                import shutil
                shutil.move(trash_path, path)
                
            # UI更新（現在のマップ選択で画像を表示）
            if hasattr(self.app, 'map_tab') and self.app.selected_map_key:
                self.app.map_tab.load_map_image(self.app.selected_map_key)
                
        except Exception as e:
            print(f"Failed to restore image: {e}")

    def _delete_image(self, state):
        """画像をゴミ箱へ移動（再削除）"""
        path = state['path']
        trash_path = state['trash_path']
        try:
            if os.path.exists(path):
                # ゴミ箱へ移動
                import shutil
                if not os.path.exists(os.path.dirname(trash_path)):
                    os.makedirs(os.path.dirname(trash_path))
                shutil.move(path, trash_path)
            
            # UI更新
            if hasattr(self.app, 'map_tab'):
                self.app.map_tab.app.map_image_label.configure(image='')
                self.app.map_tab.app.map_image_label.image = None
                
        except Exception as e:
            print(f"Failed to delete image: {e}")
