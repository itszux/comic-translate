from PySide6 import QtWidgets, QtCore, QtGui
from app.ui.dayu_widgets.push_button import MPushButton
from app.ui.dayu_widgets.text_edit import MTextEdit
from app.ui.dayu_widgets.label import MLabel
from app.ui.dayu_widgets.combo_box import MComboBox
from app.ui.dayu_widgets.divider import MDivider
from modules.utils.textblock import TextBlock
import copy

class ManualTranslateDialog(QtWidgets.QDialog):
    def __init__(self, main_controller, parent=None):
        super().__init__(parent)
        self.main = main_controller
        self.setWindowTitle(self.tr("Manual Translation"))
        self.resize(800, 600)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowContextHelpButtonHint, False)

        self.blocks_mapping = [] # List of tuples: (image_path, TextBlock_reference)

        self._setup_ui()
        self._generate_prompt()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Top controls
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addWidget(MLabel(self.tr("Scope:")))
        self.scope_combo = MComboBox().medium()
        self.scope_combo.addItems([self.tr("Current Page"), self.tr("All Pages")])
        self.scope_combo.currentIndexChanged.connect(self._generate_prompt)
        top_layout.addWidget(self.scope_combo)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Splitter for prompt and input
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        
        # Prompt Area
        prompt_widget = QtWidgets.QWidget()
        prompt_layout = QtWidgets.QVBoxLayout(prompt_widget)
        prompt_layout.setContentsMargins(0, 0, 0, 0)
        
        prompt_header = QtWidgets.QHBoxLayout()
        prompt_header.addWidget(MLabel(self.tr("1. Copy this prompt and paste it into ChatGPT/Gemini:")).strong())
        prompt_header.addStretch()
        self.copy_btn = MPushButton(self.tr("Copy to Clipboard")).primary()
        self.copy_btn.clicked.connect(self._copy_prompt)
        prompt_header.addWidget(self.copy_btn)
        prompt_layout.addLayout(prompt_header)

        self.prompt_text = MTextEdit()
        self.prompt_text.setReadOnly(True)
        prompt_layout.addWidget(self.prompt_text)
        
        # Result Area
        result_widget = QtWidgets.QWidget()
        result_layout = QtWidgets.QVBoxLayout(result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)

        result_layout.addWidget(MLabel(self.tr("2. Paste the AI's exact response here:")).strong())
        self.result_text = MTextEdit()
        result_layout.addWidget(self.result_text)

        splitter.addWidget(prompt_widget)
        splitter.addWidget(result_widget)
        layout.addWidget(splitter)

        # Bottom buttons
        layout.addWidget(MDivider())
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        self.apply_btn = MPushButton(self.tr("Apply Translation")).success()
        self.apply_btn.clicked.connect(self._apply_translation)
        cancel_btn = MPushButton(self.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.apply_btn)
        layout.addLayout(btn_layout)

    def _generate_prompt(self):
        scope = self.scope_combo.currentText()
        self.blocks_mapping = []

        if scope == self.tr("Current Page"):
            if self.main.curr_img_idx < 0 or self.main.curr_img_idx >= len(self.main.image_files):
                self.prompt_text.setPlainText("No image selected.")
                return
            current_file = self.main.image_files[self.main.curr_img_idx]
            for blk in self.main.blk_list:
                if blk.text.strip():
                    self.blocks_mapping.append((current_file, blk))
        else:
            for file_path in self.main.image_files:
                state = self.main.image_states.get(file_path, {})
                blk_list = state.get("blk_list", [])
                
                # If current image, use main.blk_list to get latest edits
                if self.main.curr_img_idx >= 0 and self.main.image_files[self.main.curr_img_idx] == file_path:
                    blk_list = self.main.blk_list
                    
                for blk in blk_list:
                    if blk.text.strip():
                        self.blocks_mapping.append((file_path, blk))

        if not self.blocks_mapping:
            self.prompt_text.setPlainText("No text blocks found.")
            return

        source_lang = self.main.s_combo.currentText()
        target_lang = self.main.t_combo.currentText()

        prompt = f"Translate the following comic text blocks from {source_lang} to {target_lang}.\n"
        prompt += "Important Instructions:\n"
        prompt += "1. Provide ONLY the translated text. Do not add any conversational text, notes, or explanations before or after the translation.\n"
        prompt += "2. Keep exactly the same number of text blocks as the original. Each block is separated by '---BLOCK---'.\n"
        prompt += "3. For each block, provide your translation separated by the exact same separator '---BLOCK---'.\n"
        prompt += "4. Optimize Japanese ellipses (dots): if the original has many dots (e.g. .......), replace them with standard 3 dots (...).\n\n"
        
        prompt += "Original text blocks:\n"
        
        for _, blk in self.blocks_mapping:
            prompt += f"---BLOCK---\n{blk.text.strip()}\n"
        prompt += "---BLOCK---"

        self.prompt_text.setPlainText(prompt)

    def _copy_prompt(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.prompt_text.toPlainText())

    def _apply_translation(self):
        result = self.result_text.toPlainText().strip()
        if not result:
            QtWidgets.QMessageBox.warning(self, "Error", "Result text is empty.")
            return

        blocks_result = [b.strip() for b in result.split("---BLOCK---") if b.strip() != ""]
        
        if len(blocks_result) != len(self.blocks_mapping):
            QtWidgets.QMessageBox.warning(
                self, 
                "Error", 
                f"Count mismatch: Expected {len(self.blocks_mapping)} blocks, but got {len(blocks_result)}. Please check the formatting."
            )
            return

        for i, (file_path, blk) in enumerate(self.blocks_mapping):
            blk.translation = blocks_result[i]
            
        self.main.mark_project_dirty()
        
        # Refresh UI
        self.main.blk_list_updated.emit()
        self.main.finish_ocr_translate(single_block=False)
        
        # Re-trigger selection to update right panel text fields if an item was selected
        if self.main.text_block_list.currentItem():
            self.main.on_text_block_list_item_clicked(self.main.text_block_list.currentItem())

        self.accept()
