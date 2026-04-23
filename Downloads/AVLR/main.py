import sys
import cv2
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QComboBox, QSpinBox,
    QProgressBar, QMessageBox, QStatusBar, QGroupBox, QGridLayout,
    QTabWidget, QLineEdit, QListWidget, QListWidgetItem, QDial
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor
from PyQt5.QtWidgets import QScrollArea

from video_processor import VideoProcessor


class VideoProcessingWorker(QThread):
    """Worker thread for video processing"""
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, processor, output_path, effects_config):
        super().__init__()
        self.processor = processor
        self.output_path = output_path
        self.effects_config = effects_config
    
    def run(self):
        success, message = self.processor.process_video_with_all_effects(
            self.output_path, 
            self.effects_config,
            self.progress.emit
        )
        self.finished.emit(success, message)


class VideoWatermarkRemover(QMainWindow):
    """Enhanced video editor with watermark removal, text replacement, and color changing"""
    
    def __init__(self):
        super().__init__()
        self.processor = VideoProcessor()
        self.drawing = False
        self.start_x = 0
        self.start_y = 0
        self.scale_factor = 1.0
        self.current_frame_num = 0
        self.processing_worker = None
        self.show_mask = False
        
        # New feature attributes
        self.drawing_color_region = False
        self.show_color_regions = False
        self.color_regions = []  # List of (x1, y1, x2, y2, hue_shift)
        self.text_replacements = []  # List of (old_text, new_text)
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Advanced Video Editor - Watermark Removal & Effects")
        self.setGeometry(100, 100, 1600, 900)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left side - Video display
        left_layout = QVBoxLayout()
        
        # Video label
        self.video_label = QLabel()
        self.video_label.setStyleSheet("border: 2px solid gray; background-color: black;")
        self.video_label.setMinimumSize(700, 600)
        self.video_label.mousePressEvent = self.on_video_mouse_press
        self.video_label.mouseMoveEvent = self.on_video_mouse_move
        self.video_label.mouseReleaseEvent = self.on_video_mouse_release
        left_layout.addWidget(self.video_label)
        
        # Frame slider
        slider_layout = QHBoxLayout()
        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.sliderMoved.connect(self.on_slider_moved)
        slider_layout.addWidget(QLabel("Frame:"))
        slider_layout.addWidget(self.frame_slider)
        self.frame_label = QLabel("0/0")
        slider_layout.addWidget(self.frame_label)
        left_layout.addLayout(slider_layout)
        
        # Right side - Tabbed controls
        tab_widget = QTabWidget()
        
        # Tab 1: Watermark Removal
        tab1 = self.create_watermark_tab()
        tab_widget.addTab(tab1, "🚫 Watermark Removal")
        
        # Tab 2: Text Replacement
        tab2 = self.create_text_tab()
        tab_widget.addTab(tab2, "📝 Text Replacement")
        
        # Tab 3: Color Change
        tab3 = self.create_color_tab()
        tab_widget.addTab(tab3, "🎨 Color Change")
        
        # Tab 4: Export
        tab4 = self.create_export_tab()
        tab_widget.addTab(tab4, "💾 Export")
        
        main_layout.addLayout(left_layout, 3)
        main_layout.addWidget(tab_widget, 1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
    def create_watermark_tab(self):
        """Create watermark removal tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # File selection
        file_group = QGroupBox("Video File")
        file_layout = QVBoxLayout()
        self.file_label = QLabel("No video loaded")
        self.file_label.setStyleSheet("color: gray;")
        file_layout.addWidget(self.file_label)
        self.load_btn = QPushButton("📁 Load Video")
        self.load_btn.clicked.connect(self.load_video)
        file_layout.addWidget(self.load_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Mask controls
        mask_group = QGroupBox("Selection Tools")
        mask_layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "📌 How to use:\n"
            "1. Draw rectangles on watermarks\n"
            "2. Left-click and drag\n"
            "3. Click 'Clear' to reset\n"
            "4. Preview with 'Show/Hide'"
        )
        instructions.setStyleSheet("color: #555; font-size: 9px; background: #f0f0f0; padding: 8px;")
        mask_layout.addWidget(instructions)
        
        self.clear_mask_btn = QPushButton("🗑️ Clear Selection")
        self.clear_mask_btn.clicked.connect(self.clear_mask)
        self.clear_mask_btn.setEnabled(False)
        mask_layout.addWidget(self.clear_mask_btn)
        
        self.show_mask_btn = QPushButton("👁️ Show/Hide Selection")
        self.show_mask_btn.clicked.connect(self.toggle_mask_display)
        self.show_mask_btn.setEnabled(False)
        mask_layout.addWidget(self.show_mask_btn)
        
        mask_group.setLayout(mask_layout)
        layout.addWidget(mask_group)
        
        # Settings
        settings_group = QGroupBox("Settings")
        settings_layout = QGridLayout()
        
        settings_layout.addWidget(QLabel("Removal Method:"), 0, 0)
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Inpaint (Better)", "Morphological"])
        settings_layout.addWidget(self.method_combo, 0, 1)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        layout.addStretch()
        return widget
    
    def create_text_tab(self):
        """Create text replacement tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Text replacement controls
        group = QGroupBox("Replace Text in Video")
        group_layout = QVBoxLayout()
        
        info = QLabel(
            "🔤 Automatically detect and replace text:\n"
            "Old name → New name"
        )
        info.setStyleSheet("font-size: 9px; color: #555;")
        group_layout.addWidget(info)
        
        # Input fields
        input_layout = QGridLayout()
        
        input_layout.addWidget(QLabel("Old Text:"), 0, 0)
        self.old_text_input = QLineEdit()
        self.old_text_input.setPlaceholderText("e.g., Rishi")
        input_layout.addWidget(self.old_text_input, 0, 1)
        
        input_layout.addWidget(QLabel("New Text:"), 1, 0)
        self.new_text_input = QLineEdit()
        self.new_text_input.setPlaceholderText("e.g., Raj")
        input_layout.addWidget(self.new_text_input, 1, 1)
        
        add_btn = QPushButton("➕ Add Replacement")
        add_btn.clicked.connect(self.add_text_replacement)
        input_layout.addWidget(add_btn, 2, 0, 1, 2)
        
        group_layout.addLayout(input_layout)
        
        # List of replacements
        list_label = QLabel("Replacements:")
        group_layout.addWidget(list_label)
        
        self.text_list = QListWidget()
        group_layout.addWidget(self.text_list)
        
        # Remove button
        remove_btn = QPushButton("❌ Remove Selected")
        remove_btn.clicked.connect(self.remove_text_replacement)
        group_layout.addWidget(remove_btn)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
        
        layout.addStretch()
        return widget
    
    def create_color_tab(self):
        """Create color change tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Color change info
        info = QLabel(
            "🎨 Change Clothes Color:\n"
            "Draw rectangle on clothes,\n"
            "adjust hue slider, add to list"
        )
        info.setStyleSheet("font-size: 9px; color: #555; background: #f0f0f0; padding: 8px;")
        layout.addWidget(info)
        
        # Mode toggle
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.color_mode_combo = QComboBox()
        self.color_mode_combo.addItems(["Watermark Mode", "Color Mode"])
        self.color_mode_combo.currentTextChanged.connect(self.toggle_draw_mode)
        mode_layout.addWidget(self.color_mode_combo)
        layout.addLayout(mode_layout)
        
        # Hue slider
        hue_layout = QGridLayout()
        hue_layout.addWidget(QLabel("Hue Shift:"), 0, 0)
        self.hue_slider = QSlider(Qt.Horizontal)
        self.hue_slider.setMinimum(-180)
        self.hue_slider.setMaximum(180)
        self.hue_slider.setValue(0)
        self.hue_slider.setTickPosition(QSlider.TicksBelow)
        self.hue_slider.setTickInterval(30)
        hue_layout.addWidget(self.hue_slider, 0, 1)
        self.hue_label = QLabel("0°")
        hue_layout.addWidget(self.hue_label, 0, 2)
        self.hue_slider.valueChanged.connect(self.update_hue_label)
        layout.addLayout(hue_layout)
        
        # Preview color
        self.color_preview = QLabel()
        self.color_preview.setFixedHeight(40)
        self.color_preview.setStyleSheet("background-color: rgb(200, 200, 200); border: 1px solid gray;")
        layout.addWidget(QLabel("Color Preview:"))
        layout.addWidget(self.color_preview)
        
        # Add color region button
        add_color_btn = QPushButton("➕ Add Color Region")
        add_color_btn.clicked.connect(self.add_color_region)
        layout.addWidget(add_color_btn)
        
        # Regions list
        list_label = QLabel("Color Changes:")
        layout.addWidget(list_label)
        
        self.color_list = QListWidget()
        layout.addWidget(self.color_list)
        
        # Remove button
        remove_color_btn = QPushButton("❌ Remove Selected")
        remove_color_btn.clicked.connect(self.remove_color_region)
        layout.addWidget(remove_color_btn)
        
        # Show regions toggle
        self.show_color_regions_btn = QPushButton("👁️ Show/Hide Regions")
        self.show_color_regions_btn.clicked.connect(self.toggle_color_regions_display)
        layout.addWidget(self.show_color_regions_btn)
        
        layout.addStretch()
        return widget
    
    def create_export_tab(self):
        """Create export tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Summary
        summary_label = QLabel("Processing Summary:")
        summary_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(summary_label)
        
        self.summary_text = QLabel("")
        self.summary_text.setStyleSheet("border: 1px solid #ccc; padding: 10px; background: #f9f9f9; font-size: 9px;")
        self.summary_text.setWordWrap(True)
        layout.addWidget(self.summary_text)
        
        # Process button
        self.process_btn = QPushButton("🎬 Process & Export Video")
        self.process_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 12px; font-size: 11px;"
        )
        self.process_btn.clicked.connect(self.process_video)
        self.process_btn.setEnabled(False)
        layout.addWidget(self.process_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        layout.addStretch()
        update_summary_btn = QPushButton("🔄 Refresh Summary")
        update_summary_btn.clicked.connect(self.update_summary)
        layout.addWidget(update_summary_btn)
        
        return widget
    
    def load_video(self):
        """Load a video file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            str(Path.home()),
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        success, message = self.processor.load_video(file_path)
        
        if success:
            self.file_label.setText(f"📹 {Path(file_path).name}")
            self.file_label.setStyleSheet("color: green;")
            self.status_label.setText(message)
            
            # Update frame slider
            self.frame_slider.setMaximum(self.processor.total_frames - 1)
            
            # Load and display first frame
            self.display_frame(0)
            
            # Enable controls
            self.clear_mask_btn.setEnabled(True)
            self.show_mask_btn.setEnabled(True)
            self.process_btn.setEnabled(True)
            
            self.update_summary()
        else:
            QMessageBox.critical(self, "Error", message)
            self.status_label.setText("Error loading video")
    
    def display_frame(self, frame_num):
        """Display a specific frame"""
        if self.processor.cap is None:
            return
        
        frame = self.processor.get_frame(frame_num)
        if frame is None:
            return
        
        self.current_frame_num = frame_num
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(frame_num)
        self.frame_slider.blockSignals(False)
        self.frame_label.setText(f"{frame_num + 1}/{self.processor.total_frames}")
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Overlay watermark mask if enabled
        if self.show_mask and self.processor.mask is not None:
            mask_display = cv2.cvtColor(self.processor.mask, cv2.COLOR_GRAY2BGR)
            frame_rgb = cv2.addWeighted(frame_rgb, 0.7, mask_display * 255, 0.3, 0)
        
        # Overlay color regions if enabled
        if self.show_color_regions:
            for x1, y1, x2, y2, hue in self.color_regions:
                cv2.rectangle(frame_rgb, (x1, y1), (x2, y2), (0, 255, 255), 2)  # Yellow rectangle
        
        h, w, ch = frame_rgb.shape
        bytes_per_line = 3 * w
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.scale_factor = scaled_pixmap.width() / w if w > 0 else 1.0
        self.video_label.setPixmap(scaled_pixmap)
    
    def on_video_mouse_press(self, event):
        """Handle mouse press on video"""
        if self.processor.cap is None:
            return
        
        mode = self.color_mode_combo.currentText()
        
        if mode == "Watermark Mode":
            self.drawing = True
        else:  # Color Mode
            self.drawing_color_region = True
        
        self.start_x = int(event.x() / self.scale_factor)
        self.start_y = int(event.y() / self.scale_factor)
        
        self.start_x = max(0, min(self.start_x, self.processor.width - 1))
        self.start_y = max(0, min(self.start_y, self.processor.height - 1))
    
    def on_video_mouse_move(self, event):
        """Handle mouse move on video - draw preview rectangle"""
        if (not self.drawing and not self.drawing_color_region) or self.processor.cap is None:
            return
        
        frame = self.processor.get_frame(self.current_frame_num)
        if frame is None:
            return
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        end_x = int(event.x() / self.scale_factor)
        end_y = int(event.y() / self.scale_factor)
        
        end_x = max(0, min(end_x, self.processor.width - 1))
        end_y = max(0, min(end_y, self.processor.height - 1))
        
        # Draw based on mode
        if self.drawing:
            color = (255, 0, 0)  # Red for watermark
        else:
            color = (0, 255, 255)  # Yellow for color region
        
        cv2.rectangle(frame_rgb, (self.start_x, self.start_y), (end_x, end_y), color, 2)
        
        # Overlay masks
        if self.show_mask and self.processor.mask is not None:
            mask_display = cv2.cvtColor(self.processor.mask, cv2.COLOR_GRAY2BGR)
            frame_rgb = cv2.addWeighted(frame_rgb, 0.7, mask_display * 255, 0.3, 0)
        
        if self.show_color_regions:
            for x1, y1, x2, y2, hue in self.color_regions:
                cv2.rectangle(frame_rgb, (x1, y1), (x2, y2), (0, 255, 255), 2)
        
        h, w, ch = frame_rgb.shape
        bytes_per_line = 3 * w
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled_pixmap)
    
    def on_video_mouse_release(self, event):
        """Handle mouse release on video"""
        if self.processor.cap is None:
            return
        
        if self.drawing:
            self.drawing = False
            
            end_x = int(event.x() / self.scale_factor)
            end_y = int(event.y() / self.scale_factor)
            
            self.processor.add_mask_region(self.start_x, self.start_y, end_x, end_y)
            self.display_frame(self.current_frame_num)
            self.status_label.setText("✅ Watermark region added")
        
        elif self.drawing_color_region:
            self.drawing_color_region = False
            
            end_x = int(event.x() / self.scale_factor)
            end_y = int(event.y() / self.scale_factor)
            
            # This prepares the region; user adds it via button
            self.pending_color_region = (self.start_x, self.start_y, end_x, end_y)
            self.display_frame(self.current_frame_num)
            self.status_label.setText("✅ Draw completed. Adjust hue and click 'Add Color Region'")
    
    def on_slider_moved(self, value):
        """Handle slider movement"""
        self.display_frame(value)
    
    def clear_mask(self):
        """Clear the removal mask"""
        self.processor.clear_mask()
        self.display_frame(self.current_frame_num)
        self.status_label.setText("🗑️ Selection mask cleared")
    
    def toggle_mask_display(self):
        """Toggle mask display overlay"""
        self.show_mask = not self.show_mask
        self.display_frame(self.current_frame_num)
    
    def toggle_draw_mode(self):
        """Toggle between watermark and color drawing modes"""
        mode = self.color_mode_combo.currentText()
        if mode == "Color Mode":
            self.status_label.setText("📌 Draw rectangles on clothes to change color")
        else:
            self.status_label.setText("📌 Draw rectangles on watermarks to remove")
    
    def update_hue_label(self):
        """Update hue display"""
        hue = self.hue_slider.value()
        self.hue_label.setText(f"{hue}°")
        
        # Update color preview
        # Convert hue to RGB for preview
        hsv = np.array([[[hue % 180, 255, 200]]], dtype=np.uint8)
        rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        r, g, b = rgb[0][0]
        self.color_preview.setStyleSheet(f"background-color: rgb({r}, {g}, {b}); border: 1px solid gray;")
    
    def add_color_region(self):
        """Add a color region to the list"""
        if not hasattr(self, 'pending_color_region'):
            QMessageBox.warning(self, "Error", "Draw a rectangle first!")
            return
        
        x1, y1, x2, y2 = self.pending_color_region
        hue = self.hue_slider.value()
        
        self.color_regions.append((x1, y1, x2, y2, hue))
        
        item_text = f"Region ({x1},{y1}) → ({x2},{y2}) | Hue: {hue}°"
        self.color_list.addItem(item_text)
        
        self.status_label.setText(f"✅ Color region added (Hue: {hue}°)")
        self.update_summary()
    
    def remove_color_region(self):
        """Remove selected color region"""
        row = self.color_list.currentRow()
        if row >= 0:
            self.color_list.takeItem(row)
            self.color_regions.pop(row)
            self.status_label.setText("🗑️ Color region removed")
            self.update_summary()
    
    def toggle_color_regions_display(self):
        """Toggle color regions display"""
        self.show_color_regions = not self.show_color_regions
        self.display_frame(self.current_frame_num)
    
    def add_text_replacement(self):
        """Add text replacement to list"""
        old_text = self.old_text_input.text().strip()
        new_text = self.new_text_input.text().strip()
        
        if not old_text or not new_text:
            QMessageBox.warning(self, "Error", "Both fields required!")
            return
        
        self.text_replacements.append((old_text, new_text))
        
        item_text = f"'{old_text}' → '{new_text}'"
        self.text_list.addItem(item_text)
        
        self.old_text_input.clear()
        self.new_text_input.clear()
        
        self.status_label.setText(f"✅ Text replacement added")
        self.update_summary()
    
    def remove_text_replacement(self):
        """Remove selected text replacement"""
        row = self.text_list.currentRow()
        if row >= 0:
            self.text_list.takeItem(row)
            self.text_replacements.pop(row)
            self.status_label.setText("🗑️ Text replacement removed")
            self.update_summary()
    
    def update_summary(self):
        """Update the processing summary"""
        summary = f"""
        📁 Video: {self.file_label.text()}
        
        ✂️ Watermark Regions: {cv2.countNonZero(self.processor.mask) if self.processor.mask is not None else 0} pixels marked
        💬 Text Replacements: {len(self.text_replacements)} replacements
        🎨 Color Changes: {len(self.color_regions)} regions
        """
        self.summary_text.setText(summary.strip())
    
    def process_video(self):
        """Process the video with all effects"""
        if self.processor.cap is None:
            QMessageBox.warning(self, "Error", "No video loaded!")
            return
        
        # Check if at least one effect is enabled
        has_watermark = cv2.countNonZero(self.processor.mask) > 0 if self.processor.mask is not None else False
        has_text = len(self.text_replacements) > 0
        has_color = len(self.color_regions) > 0
        
        if not (has_watermark or has_text or has_color):
            QMessageBox.warning(self, "Error", "Select at least one effect!")
            return
        
        # Get output file path
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Processed Video",
            str(Path.home()),
            "MP4 Video (*.mp4)"
        )
        
        if not output_path:
            return
        
        if not output_path.endswith('.mp4'):
            output_path += '.mp4'
        
        # Prepare effects config
        effects_config = {
            'removal_method': 'inpaint' if 'Inpaint' in self.method_combo.currentText() else 'morphological',
            'text_replacements': self.text_replacements if has_text else [],
            'recolor_regions': self.color_regions if has_color else []
        }
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Disable controls
        self.load_btn.setEnabled(False)
        self.process_btn.setEnabled(False)
        self.status_label.setText("⏳ Processing video...")
        
        # Start processing in worker thread
        self.processing_worker = VideoProcessingWorker(self.processor, output_path, effects_config)
        self.processing_worker.progress.connect(self.on_processing_progress)
        self.processing_worker.finished.connect(self.on_processing_finished)
        self.processing_worker.start()
    
    def on_processing_progress(self, current, total):
        """Update progress during video processing"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"⏳ Processing: {current}/{total} frames")
    
    def on_processing_finished(self, success, message):
        """Handle processing completion"""
        self.progress_bar.setVisible(False)
        self.load_btn.setEnabled(True)
        self.process_btn.setEnabled(True)
        
        if success:
            self.status_label.setText("✅ " + message)
            QMessageBox.information(self, "✅ Success", message)
        else:
            self.status_label.setText("❌ Processing failed")
            QMessageBox.critical(self, "❌ Error", message)
    
    def closeEvent(self, event):
        """Clean up resources on close"""
        self.processor.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = VideoWatermarkRemover()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
