import sys
import os
import io
import time
import yaml
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from collections import OrderedDict
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFormLayout,QToolTip,
    QVBoxLayout, QHBoxLayout, QComboBox, QSlider, 
    QCheckBox, QLabel, QPushButton, QLineEdit, QFileDialog,QMessageBox, 
    QInputDialog, QDialog, QDoubleSpinBox, QGraphicsView, QGraphicsScene
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
from pathlib import Path
from humanfriendly import format_timespan
from PIL import Image
sys.path.insert(1, '/projectnb/lejlab2/quan/wound_compute_GUI/woundcomputeGUI/src')
import woundcomputegui.wc_functions as wcf
import woundcomputegui.wellplate_gui as wpg
import woundcomputegui.data_management as dm


class VisualizationWindow(QDialog):
    def __init__(self, path_output):
        super().__init__()
        self.path_output = path_output
        self.setWindowTitle("Data Visualization")
        self.setGeometry(100, 20, 1000, 600) # x, y, width, height
        self.setup_ui()
        self.sample_tooltips = {}
        self.old_data_type = None


    def setup_ui(self):
        layout = QVBoxLayout()

        # Dropdown boxes
        dropdown_layout = QHBoxLayout()

        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["Raw images", "Tissue mask", "Wound mask",
                                       "Wound mask all frames",
#                                        "Tissue broken status vs. frame", 
#                                        "Tissue closure status vs. frame", 
                                       "Wound area vs. frame",
                                       "Show all samples with wound masks"])
        dropdown_layout.addWidget(QLabel("Data type:"))
        dropdown_layout.addWidget(self.data_type_combo)

        self.basename_combo = QComboBox()
        self.basename_combo.addItems(self.get_basenames())
        self.basename_combo.currentIndexChanged.connect(self.update_samples)
        dropdown_layout.addWidget(QLabel("Base name:"))
        dropdown_layout.addWidget(self.basename_combo)

        self.sample_combo = QComboBox()
        dropdown_layout.addWidget(QLabel("Sample #:"))
        dropdown_layout.addWidget(self.sample_combo)

        layout.addLayout(dropdown_layout)

        # Image display area
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        layout.addWidget(self.view)

        #  Frame slider and label
        slider_layout = QHBoxLayout()
        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setEnabled(False)
        self.frame_slider.valueChanged.connect(self.update_frame)
        self.frame_label = QLabel("Frame: 0")
        slider_layout.addWidget(self.frame_slider)
        slider_layout.addWidget(self.frame_label)
        layout.addLayout(slider_layout)

        # Load button
        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self.load_data)
        layout.addWidget(self.load_button)

        self.setLayout(layout)

        # Initialize samples
        self.update_samples()


    def get_basenames(self):
        return [name for name in os.listdir(self.path_output) 
                if os.path.isdir(os.path.join(self.path_output, name))]


    def update_samples(self):
        basename = self.basename_combo.currentText()
        samples = [name for name in os.listdir(os.path.join(self.path_output, basename))
                   if os.path.isdir(os.path.join(self.path_output, basename, name))]

        # Sort the samples using a custom sorting function
        samples.sort(key=lambda x: int(''.join(filter(str.isdigit, x))))

        self.sample_combo.clear()
        self.sample_combo.addItems(samples)


    def load_data(self):
        data_type = self.data_type_combo.currentText()
        basename = self.basename_combo.currentText()
        sample = self.sample_combo.currentText()

        if data_type == "Raw images":
            self.load_raw_images(basename, sample)
        elif data_type == "Tissue mask":
            self.load_tissue_mask(basename, sample)
        elif data_type == "Wound mask":
            self.load_wound_mask(basename, sample)
        elif data_type == "Wound mask all frames":
            self.load_wound_mask_all_frames(basename, sample)
        elif data_type == "Wound area vs. frame":
            self.wound_area_v_frame(basename, sample)
        elif data_type == "Show all samples with wound masks":
            self.load_all_samples_grid(basename)
        else:
            # Implement other data type visualizations here
            QMessageBox.information(self, "Info", f"Visualization not implemented.")


    def load_raw_images(self, basename, sample):
        image_folder = os.path.join(self.path_output, basename, sample, "ph1_images")
        self.images = []
        for file in sorted(os.listdir(image_folder)):
            if file.endswith(".TIF") or file.endswith(".tif"):
                image_path = os.path.join(image_folder, file)
                image = Image.open(image_path)
                # Convert PIL Image to QPixmap
                pixmap = self.pil_to_qpixmap(image)
                self.images.append(pixmap)

        if self.images:
            self.frame_slider.setEnabled(True)
            self.frame_slider.setRange(0, len(self.images) - 1)
            self.frame_slider.setValue(0)
            self.update_frame()
        else:
            QMessageBox.warning(self, "Warning", "No .TIF (or .tif) files found in the selected folder.")


    def load_tissue_mask(self, basename, sample):
        image_folder = os.path.join(self.path_output, basename, sample, "ph1_images")
        self.images = []
        for file in sorted(os.listdir(image_folder)):
            if file.endswith(".TIF") or file.endswith(".tif"):
                image_path = os.path.join(image_folder, file)
                image = Image.open(image_path)
                self.images.append(image)
        
        tissue_mask_folder = os.path.join(self.path_output, basename, sample, "segment_ph1")
        self.tissue_masks = []
        for file in sorted(os.listdir(tissue_mask_folder)):
            if file.startswith("tissue_mask"):
                image_path = os.path.join(tissue_mask_folder, file)
                tissue_mask = np.load(image_path,allow_pickle=True)
                self.tissue_masks.append(tissue_mask)
        
        self.tissue_masked_images=[]
        for ind,image in enumerate(self.images):
            image_array = np.array(image)
            tissue_mask = self.tissue_masks[ind]
            if image_array.shape[:2] != tissue_mask.shape[:2]:
                QMessageBox.warning(self, "Warning", "The dimensions of the raw images and the tissue masks are not matching.")

            img_arr_rgb = np.stack([image_array] * 3, axis=-1)
            red_tissue_mask = np.zeros_like(img_arr_rgb)  # Initialize an empty RGB array
            red_tissue_mask[..., 0] = tissue_mask.astype(int)

            img_arr_rgb_normalized = img_arr_rgb / np.amax(img_arr_rgb)
            red_tissue_mask_normalized = red_tissue_mask / np.amax(red_tissue_mask)

            opacity = 0.25
            blended_image = (img_arr_rgb_normalized * (1 - opacity) + red_tissue_mask_normalized * opacity)
            blended_image_uint8 = (blended_image * 255).astype(np.uint8)
            final_image_pil = Image.fromarray(blended_image_uint8)

            # Convert PIL Image to QPixmap
            pixmap = self.pil_to_qpixmap(final_image_pil)

            self.tissue_masked_images.append(pixmap)

        if self.tissue_masked_images:
            self.frame_slider.setEnabled(True)
            self.frame_slider.setRange(0, len(self.tissue_masked_images) - 1)
            self.frame_slider.setValue(0)
            self.update_frame()
        else:
            QMessageBox.warning(self, "Warning", "No tissue mask data found in the selected folder.")


    def load_wound_mask(self, basename, sample):
        image_folder = os.path.join(self.path_output, basename, sample, "ph1_images")
        self.images = []
        for file in sorted(os.listdir(image_folder)):
            if file.endswith(".TIF") or file.endswith(".tif"):
                image_path = os.path.join(image_folder, file)
                image = Image.open(image_path)
                self.images.append(image)

        wound_mask_folder = os.path.join(self.path_output, basename, sample, "segment_ph1")
        self.wound_masks = []
        for file in sorted(os.listdir(wound_mask_folder)):
            if file.startswith("wound_mask"):
                image_path = os.path.join(wound_mask_folder, file)
                wound_mask = np.load(image_path,allow_pickle=True)
                self.wound_masks.append(wound_mask)

        self.wound_masked_images=[]
        for ind,image in enumerate(self.images):
            image_array = np.array(image)
            wound_mask = self.wound_masks[ind]
            if image_array.shape[:2] != wound_mask.shape[:2]:
                QMessageBox.warning(self, "Warning", "The dimensions of the raw images and the tissue masks are not matching.")

            opacity = 0.25
            if len(np.unique(wound_mask)) > 1: # check if there's a tissue mask
                img_arr_rgb = np.stack([image_array] * 3, axis=-1)
                red_wound_mask = np.zeros_like(img_arr_rgb)  # Initialize an empty RGB array
                red_wound_mask[..., 0] = wound_mask.astype(int)

                img_arr_rgb_normalized = img_arr_rgb / np.amax(img_arr_rgb)
                red_wound_mask_normalized = red_wound_mask / np.amax(red_wound_mask)

                blended_image = (img_arr_rgb_normalized * (1 - opacity) + red_wound_mask_normalized * opacity)
                blended_image_uint8 = (blended_image * 255).astype(np.uint8)
                final_image_pil = Image.fromarray(blended_image_uint8)

                # Convert PIL Image to QPixmap
                pixmap = self.pil_to_qpixmap(final_image_pil)
            else:
                img_arr_normalized = image_array / np.amax(image_array)
                blended_image = (img_arr_normalized*(1-opacity))
                blended_image_uint8 = (blended_image*255).astype(np.uint8)
                final_image_pil = Image.fromarray(blended_image_uint8)
                pixmap = self.pil_to_qpixmap(final_image_pil)

            self.wound_masked_images.append(pixmap)

        if self.wound_masked_images:
            self.frame_slider.setEnabled(True)
            self.frame_slider.setRange(0, len(self.wound_masked_images) - 1)
            self.frame_slider.setValue(0)
            self.update_frame()
        else:
            QMessageBox.warning(self, "Warning", "No wound mask data found in the selected folder.")


    def load_wound_mask_all_frames(self, basename, sample):
        image_folder = os.path.join(self.path_output, basename, sample, "ph1_images")
        wound_mask_folder = os.path.join(self.path_output, basename, sample, "segment_ph1")

        images = []
        wound_masks = []

        for file in sorted(os.listdir(image_folder)):
            if file.endswith((".TIF", ".tif")):
                image_path = os.path.join(image_folder, file)
                image = Image.open(image_path)
                images.append(image)

        for file in sorted(os.listdir(wound_mask_folder)):
            if file.startswith("wound_mask"):
                mask_path = os.path.join(wound_mask_folder, file)
                wound_mask = np.load(mask_path, allow_pickle=True)
                wound_masks.append(wound_mask)

        self.wound_masked_images = []
        self.frame_tooltips = {}

        for ind, (image, wound_mask) in enumerate(zip(images, wound_masks)):
            blended_image = self.blend_image_and_mask(image, wound_mask)
            self.wound_masked_images.append(blended_image)
            self.frame_tooltips[ind] = f"Frame: {ind}"

        self.create_wound_mask_grid()
        self.frame_slider.setEnabled(False)
        self.frame_slider.hide()
        self.frame_label.hide()


    def create_wound_mask_grid(self):
        num_images = len(self.wound_masked_images)

        # Calculate the available space for the grid
        available_width = self.width() - 40  # Subtracting some padding
        available_height = self.height() - 100  # Subtracting space for controls

        # Calculate the aspect ratio of the available space
        aspect_ratio = available_width / available_height

        # Determine the optimal grid dimensions
        grid_height = int(np.sqrt(num_images / aspect_ratio))
        grid_width = int(np.ceil(num_images / grid_height))

        # Calculate cell size to fit the grid within the available space
        cell_width = available_width // grid_width
        cell_height = available_height // grid_height
        cell_size = min(cell_width, cell_height)

        # Add a small gap between images
        gap = 2
        total_cell_size = cell_size + gap

        # Calculate the total grid size
        grid_width_pixels = grid_width * total_cell_size - gap
        grid_height_pixels = grid_height * total_cell_size - gap

        # Create a white background image for the grid
        grid_image = Image.new('RGB', (grid_width_pixels, grid_height_pixels), color='white')

        self.frame_tooltips = {}

        for i, img in enumerate(self.wound_masked_images):
            row = i // grid_width
            col = i % grid_width
            x = col * total_cell_size
            y = row * total_cell_size

            img_resized = img.copy()
            img_resized.thumbnail((cell_size, cell_size), Image.Resampling.LANCZOS)
            grid_image.paste(img_resized, (x, y))

            self.frame_tooltips[(x, y, x + cell_size, y + cell_size)] = f"Frame: {i}"

        # Convert the grid image to a QPixmap
        pixmap = self.pil_to_qpixmap(grid_image)

        # Clear the scene and add the pixmap
        self.scene.clear()
        pixmap_item = self.scene.addPixmap(pixmap)

        # Center the grid in the view
        self.view.setSceneRect(self.scene.itemsBoundingRect())
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.view.centerOn(pixmap_item)

        self.view.setMouseTracking(True)
        self.view.mouseMoveEvent = self.show_frame_number_on_hover


    def show_frame_number_on_hover(self, event):
        pos = self.view.mapToScene(event.pos())
        for key, frame_info in self.frame_tooltips.items():
            if isinstance(key, tuple) and len(key) == 4:
                x1, y1, x2, y2 = key
                if x1 <= pos.x() <= x2 and y1 <= pos.y() <= y2:
                    QToolTip.showText(self.view.mapToGlobal(event.pos()), frame_info)
                    return
            elif isinstance(key, int):
                # Handle the case where the key is an integer (frame number)
                QToolTip.showText(self.view.mapToGlobal(event.pos()), frame_info)
                return
        QToolTip.hideText()


    def wound_area_v_frame(self, basename, sample):
        image_folder = os.path.join(self.path_output, basename, sample, "segment_ph1")
        self.wound_area_plot = None
        for file in sorted(os.listdir(image_folder)):
            if file.startswith("wound_area") and file.endswith(".txt"):
                wound_area_path = os.path.join(image_folder, file)
                wound_area_vs_frame = np.loadtxt(wound_area_path)
                num_frame = len(wound_area_vs_frame)
                frame_steps = np.linspace(0, num_frame-1, num_frame, dtype=int)

                # Create a high-resolution figure
                fig, ax = plt.subplots(figsize=(12, 8), dpi=100)
                ax.plot(frame_steps, wound_area_vs_frame, '-o', c='red', markersize=4)
                ax.set_title('Wound area vs. frame', fontsize=16)
                ax.set_xlabel('Frame #', fontsize=14)
                ax.set_ylabel('Area (pixels)', fontsize=14)
                ax.tick_params(axis='both', which='major', labelsize=12)
                ax.grid(True, linestyle='--', alpha=0.7)

                # Adjust layout to use the entire figure
                plt.tight_layout()

                canvas = FigureCanvas(fig)
                self.wound_area_plot = canvas
                break

        if self.wound_area_plot:
            self.frame_slider.setEnabled(False)
            self.frame_slider.hide()  # Hide the slider
            self.frame_label.hide()   # Hide the frame label
            self.update_frame()
        else:
            QMessageBox.warning(self, "Warning", "No wound area data found in the selected folder.")


    def load_all_samples_grid(self, basename):
        all_wound_masked_images, max_frames, self.cell_size = self.load_all_samples_wound_masks(basename)
        num_samples = len(all_wound_masked_images)
        self.grid_size = int(np.ceil(np.sqrt(num_samples)))
        
        self.frame_slider.setEnabled(True)
        self.frame_slider.setRange(0, max_frames - 1)
        self.frame_slider.setValue(0)
        
        self.all_samples_grid = all_wound_masked_images
        self.update_frame()


    def load_all_samples_wound_masks(self, basename):
        samples = self.get_samples(basename)
        samples.sort(key=lambda x: int(''.join(filter(str.isdigit, x))))  # Sort samples numerically
        max_frames = 0
        all_wound_masked_images = OrderedDict()

        # Calculate dynamic grid size and cell size
        num_samples = len(samples)
        available_width = self.width() - 40  # Subtracting some padding
        available_height = self.height() - 100  # Subtracting space for controls

        # Calculate grid dimensions to match screen aspect ratio
        aspect_ratio = available_width / available_height
        grid_height = int(np.sqrt(num_samples / aspect_ratio))
        grid_width = int(np.ceil(num_samples / grid_height))

        cell_width = available_width // grid_width
        cell_height = available_height // grid_height
        cell_size = min(cell_width, cell_height)

        self.grid_width = grid_width
        self.grid_height = grid_height
        self.cell_size = cell_size

        for sample in samples:
            image_folder = os.path.join(self.path_output, basename, sample, "ph1_images")
            wound_mask_folder = os.path.join(self.path_output, basename, sample, "segment_ph1")

            images = []
            wound_masks = []

            for file in sorted(os.listdir(image_folder)):
                if file.endswith((".TIF", ".tif")):
                    image_path = os.path.join(image_folder, file)
                    image = Image.open(image_path)
                    images.append(image)

            for file in sorted(os.listdir(wound_mask_folder)):
                if file.startswith("wound_mask"):
                    mask_path = os.path.join(wound_mask_folder, file)
                    wound_mask = np.load(mask_path, allow_pickle=True)
                    wound_masks.append(wound_mask)

            max_frames = max(max_frames, len(images))

            wound_masked_images = []
            for image, wound_mask in zip(images, wound_masks):
                blended_image = self.blend_image_and_mask(image, wound_mask)
                blended_image.thumbnail((cell_size, cell_size), Image.Resampling.LANCZOS)
                wound_masked_images.append(blended_image)

            all_wound_masked_images[sample] = wound_masked_images

        # Pad samples with fewer frames
        for sample, images in all_wound_masked_images.items():
            while len(images) < max_frames:
                images.append(None)

        return all_wound_masked_images, max_frames, cell_size


    def blend_image_and_mask(self, image, wound_mask):
        image_array = np.array(image)
        opacity = 0.25

        if len(np.unique(wound_mask)) > 1:
            img_arr_rgb = np.stack([image_array] * 3, axis=-1)
            red_wound_mask = np.zeros_like(img_arr_rgb)
            red_wound_mask[..., 0] = wound_mask.astype(int)

            img_arr_rgb_normalized = img_arr_rgb / np.amax(img_arr_rgb)
            red_wound_mask_normalized = red_wound_mask / np.amax(red_wound_mask)

            blended_image = (img_arr_rgb_normalized * (1 - opacity) + red_wound_mask_normalized * opacity)
        else:
            img_arr_normalized = image_array / np.amax(image_array)
            blended_image = img_arr_normalized * (1 - opacity)

        blended_image_uint8 = (blended_image * 255).astype(np.uint8)
        return Image.fromarray(blended_image_uint8)


    def get_samples(self, basename):
        return [name for name in os.listdir(os.path.join(self.path_output, basename))
                if os.path.isdir(os.path.join(self.path_output, basename, name))]


    def create_grid_image(self, frame):
        grid_width = self.grid_width
        grid_height = self.grid_height
        cell_size = self.cell_size
        padding = 2  # Reduced padding

        grid_image = Image.new('RGB', (grid_width * (cell_size + padding), grid_height * (cell_size + padding)), color='white')

        for i, (sample, images) in enumerate(self.all_samples_grid.items()):
            row = i // grid_width
            col = i % grid_width
            x = col * (cell_size + padding)
            y = row * (cell_size + padding)

            if frame < len(images) and images[frame] is not None:
                img = images[frame].copy()
                grid_image.paste(img, (x, y))

            # Store the sample name and position for tooltips
            self.sample_tooltips[(x, y, x + cell_size, y + cell_size)] = sample

        return grid_image


    def update_frame(self):
        data_type = self.data_type_combo.currentText()
        frame = self.frame_slider.value()

        if self.old_data_type != data_type:
            self.scene.clear()
            self.view.setMouseTracking(False)
            self.view.setScene(None)
            self.scene = QGraphicsScene()
            self.view.setScene(self.scene)
            self.old_data_type = data_type

        if data_type == "Show all samples with wound masks":
            grid_image = self.create_grid_image(frame)
            pixmap = self.pil_to_qpixmap(grid_image)
            pixmap_item = self.scene.addPixmap(pixmap)
            self.view.setSceneRect(pixmap_item.boundingRect())
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            self.view.centerOn(pixmap_item)
            self.view.setMouseTracking(True)
            self.view.mouseMoveEvent = self.show_sample_name_on_hover
            self.frame_slider.show()
            self.frame_label.show()
            self.frame_label.setText(f"Frame: {frame}")
        elif data_type == "Wound area vs. frame":
            if self.wound_area_plot:
                self.view.setMouseTracking(True)
                proxy_widget = self.scene.addWidget(self.wound_area_plot)
                self.view.setSceneRect(proxy_widget.boundingRect())
                self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
                self.view.centerOn(proxy_widget)
            self.frame_slider.hide()
            self.frame_label.hide()
        else:
            if data_type == "Raw images":
                pixmap = self.images[frame]
            elif data_type == "Tissue mask":
                pixmap = self.tissue_masked_images[frame]
            elif data_type == "Wound mask":
                pixmap = self.wound_masked_images[frame]
            pixmap_item = self.scene.addPixmap(pixmap)
            self.view.setSceneRect(pixmap_item.boundingRect())
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            self.view.centerOn(pixmap_item)
            self.frame_slider.show()
            self.frame_label.show()
            self.frame_label.setText(f"Frame: {frame}")

        self.view.viewport().update()


    def show_sample_name_on_hover(self, event):
        pos = self.view.mapToScene(event.pos())
        for (x1, y1, x2, y2), sample in self.sample_tooltips.items():
            if x1 <= pos.x() <= x2 and y1 <= pos.y() <= y2:
                QToolTip.showText(self.view.mapToGlobal(event.pos()), sample)
                return
        QToolTip.hideText()


    def pil_to_qpixmap(self,pil_image):
        buffer = io.BytesIO()
        pil_image.save(buffer, format="PNG")
        q_image = QImage()
        q_image.loadFromData(buffer.getvalue())
        return QPixmap.fromImage(q_image)



class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wound Compute")
        self.setGeometry(100, 100, 540, 250)
        self.overlay = None
        self.basename_list = None
        self.path_output = None
        self.stage_pos_maps = None
        
        # Central widget for the main window
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main vertical layout
        main_layout = QVBoxLayout()

        # 1. Directory Input with Browse Button
#         main_layout.addWidget(QLabel("Please select the appropriate folder:"))

        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Enter folder path or browse...")
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_folder)
        
        dir_layout.addWidget(QLabel("Directory with .TIF files:"))
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.browse_button)
        main_layout.addLayout(dir_layout)

        # Use a form layout for other widgets
        form_layout = QFormLayout()

        # 2. Drop-down list (ComboBox) with description
        self.microscope_type = QComboBox()
        self.microscope_type.addItems(["General"]) # "Cytation" is under construction
        form_layout.addRow(QLabel("Microscope type:"), self.microscope_type)

        # 3. Slider (QSlider) with description and a value display
        slider_layout = QHBoxLayout()
        self.max_cpu_usage_percent = QSlider(Qt.Horizontal)
        self.max_cpu_usage_percent.setRange(1, 100)
        self.max_cpu_usage_percent.setValue(80)  # Default value
        self.max_cpu_usage_percent.setFixedWidth(320)
        self.max_cpu_usage_percent.setToolTip("Set the maximum CPU usage percentage")
        
        self.slider_label = QLabel(f"{self.max_cpu_usage_percent.value()}%")
        self.max_cpu_usage_percent.valueChanged.connect(self.update_slider_label)

        slider_layout.addWidget(self.max_cpu_usage_percent)
        slider_layout.addWidget(self.slider_label)
        form_layout.addRow(QLabel("Max CPU % usage:"), slider_layout)

        # Add form layout to the main layout
        main_layout.addLayout(form_layout)

        # 4. Imaging Interval input
        self.imaging_interval = QDoubleSpinBox()
        self.imaging_interval.setRange(0.01, 1000.0)  # Set a reasonable range
        self.imaging_interval.setValue(0.50)  # Default value
        self.imaging_interval.setSingleStep(0.1)  # Step size for arrow keys
        self.imaging_interval.setDecimals(2)  # Show 2 decimal places
        self.imaging_interval.setSuffix(" hours")  # Add units
        form_layout.addRow(QLabel("Imaging Interval (hours):"), self.imaging_interval)

        # 5. Four Checkboxes (QCheckBox)
        self.check_organize = QCheckBox("Organize .tif files and prepare .yaml files")
        self.check_run_wc = QCheckBox("Run Wound Compute in parallel")
        self.check_extract_data = QCheckBox("Extract metadata")
        # self.check_visualize = QCheckBox("Visualize data")

        main_layout.addWidget(self.check_organize)
        main_layout.addWidget(self.check_run_wc)
        main_layout.addWidget(self.check_extract_data)
        # main_layout.addWidget(self.check_visualize)

        # 6. Run and Exit Buttons
        button_layout = QHBoxLayout()

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_process)
        button_layout.addWidget(self.run_button)

        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.close_app)
        button_layout.addWidget(self.exit_button)

        main_layout.addLayout(button_layout)

        # 7. Status Message
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)

        # Set the main layout to the central widget
        central_widget.setLayout(main_layout)

    def browse_folder(self):
        """Open a dialog to browse and select a folder."""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.dir_input.setText(folder_path)

    def update_slider_label(self):
        """Update the label next to the slider to show its current value."""
        self.slider_label.setText(f"{self.max_cpu_usage_percent.value()}%")

    def run_process(self):
        """Run the main processing based on user selections."""
        self.show_overlay()

        path_input = self.dir_input.text()

        # Check if the directory is provided
        if not path_input:
            QMessageBox.warning(self, "Warning", "Please select a directory!")
            return
        else:
            path_input = Path(path_input)

        self.status_label.setText("Processing...")
        QApplication.processEvents()  # Update the UI immediately

        # Call the corresponding methods based on checkbox selections
        if self.check_organize.isChecked():
            self.organize_files(path_input)
            print(f'basename_list={self.basename_list}')
            print(f'path_output={self.path_output}')
        else:
            self.obtain_organized_files(path_input)


        if self.check_run_wc.isChecked():
            self.run_wound_compute()
        elif self.check_extract_data.isChecked(): #  or self.check_visualize.isChecked()
            self.check_for_segmentation(self.path_output, self.basename_list[0])

        if self.check_extract_data.isChecked():
            self.extract_metadata()

        # if self.check_visualize.isChecked():
        #     self.visualize_data()

        self.status_label.setText("Done!")
        self.hide_overlay()

    def organize_files(self,path_input:str,image_type:str='ph1'):
        """Organize .tif files and prepare .yaml files."""
        print("Organizing .tif files and preparing .yaml files...")

        # Create new folder for sorted files
        path_output = self.create_new_folder(path_input)
        
        # Create yaml file for image type
        wcf.create_wc_yaml(path_output, image_type_in=image_type, is_fl_in=False, is_pillars_in=True)
#         print("\tCreated .yaml file")

        basename_list, is_nd = wcf.define_basename_list(
            path_input, path_output,self.microscope_type
        )
        print("\tBasename list:", basename_list)
        print("\t.nd file found:", is_nd)

        # Sort images in input folder into Sorted/basename/ folders
        print("\tSorting images into corresponding basename folders...")
        wcf.sort_basename_folders(basename_list, path_input, path_output, self.microscope_type)
        print("\tDone!")
        
        # # Check if the .nd file is found
        # if not is_nd:
        #     # Show a pop-up warning that the .nd file is missing
        #     msg_box = QMessageBox()
        #     msg_box.setIcon(QMessageBox.Warning)
        #     msg_box.setText("No .nd file found in the selected directory!")
        #     msg_box.setInformativeText("The program cannot proceed without the .nd file. Please ensure the file is present.")
        #     msg_box.setWindowTitle("Missing .nd File")
        #     msg_box.setStandardButtons(QMessageBox.Ok)

        #     # Connect the "Ok" button to close the application
        #     msg_box.buttonClicked.connect(self.close_app)
        #     msg_box.exec_()
        
        # Extract stage position information from .nd file or from data in folder
        stage_pos_maps = wcf.extract_nd_info(
            basename_list, path_output, is_nd, ms_choice=self.microscope_type
        )
        print("\tExtracted stage position information")
        print(f"\t{stage_pos_maps}")
        # import sys
        # sys.exit("Exit code bc testing")
        
        #  Sort images in each basename folder into their corresponding stage position folders
        print("\tSorting images in each basename folder into their corresponding stage position folders...")
        wcf.efficient_sort_stage_pos(
            basename_list, path_output, stage_pos_maps, image_type, self.microscope_type, is_nd
        )
        print("\tDone organizing .tif files and preparing .yaml files!")
        self.basename_list = basename_list
        self.path_output = path_output
        self.stage_pos_maps = stage_pos_maps


    def create_new_folder(self,path_input:str)->str:
        """Create new folder to sort files."""
        while True:
            # Prompt the user for a new folder name
            folder_name, ok = QInputDialog.getText(
                self, "New Folder Name","Enter a name for the new sorted folder:")

            # Check if the user pressed "OK" and provided a name
            if not ok:
                # User canceled the dialog, exit the function
                return

            folder_name = folder_name.strip()
            if not folder_name:
                QMessageBox.warning(self, "Warning", "Folder name cannot be empty!")
                continue

            # Create the full path for the new folder
            new_folder_path = os.path.join(path_input, folder_name)

            # Check if the folder already exists
            if os.path.exists(new_folder_path):
                QMessageBox.warning(self, "Warning", f"Folder '{folder_name}' already exists! Please enter a new name.")
            else:
                # Create the new folder if it doesn't exist
                try:
                    os.makedirs(new_folder_path)
#                     QMessageBox.information(self, "Success", f"Folder '{folder_name}' created successfully!")
                    return new_folder_path
#                     break  # Exit the loop since the folder was successfully created
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create folder: {e}")
                    self.status_label.setText("Ready")
                    self.hide_overlay()
                    return


    def obtain_organized_files(self,path_input:str):
        
        # Prompt user to select the folder with organized data
        QMessageBox.information(
            self,"Note",
            "The 'Organized .tif files and prepare .yaml files' button was not checked. This indicates that the .tif files are sorted and .yaml files are prepared. Please select the location of the sorted folder. Thanks!",
        )
        organized_folder = QFileDialog.getExistingDirectory(self, "Select Folder with Organized Data")
        if not organized_folder:
            QMessageBox.warning(self, "Warning", "No folder selected. Process cancelled.")
            self.status_label.setText("Ready")
            return
        path_output = Path(organized_folder)
        
        all_folders_in_path = set([os.path.dirname(p) for p in glob.glob(organized_folder)])
        if not all_folders_in_path:
            QMessageBox.warning(self, "Warning", "No sorted folders found. Process cancelled.")
        
        file_list = os.listdir(path_output)
        if "basename_list.yaml" in file_list:
            print("\tFound basename_list.yaml file in the input folder")
            with open(os.path.join(path_output, 'basename_list.yaml'), 'r') as file:
                # Load the YAML content
                basename_list = yaml.safe_load(file)
        else:
            # If basename.yaml file is not found, then get the list of folders in the input folder
            # and set it as the basename list
            basename_list = os.listdir(path_output)
            basename_list = [name for name in basename_list if os.path.isdir(os.path.join(path_output, name))]
            if not basename_list:
                QMessageBox.warning(self,"Warning","No sorted directory found. Process cancelled.")

        if "stage_positions.yaml" in file_list:
            print("\tFound stage_positions.yaml file in the input folder")
            with open(os.path.join(path_output, 'stage_positions.yaml'), 'r') as file:
                # Load the YAML content
                data = yaml.safe_load(file)
            stage_pos_maps = {}
            for index, basename in enumerate(basename_list):
                stage_pos_maps[basename] = data[basename]
        else:
            # If stage_positions.yaml file is not found, then get the list of folders in the basename folder
            # and set it as the stage_pos_maps
            stage_pos_maps = {}
            for index, basename in enumerate(basename_list):
                path_temp = os.path.join(path_output, Path(basename))
                try:
                    positions = os.listdir(path_temp)
                    positions.sort()
                    positions = [n1 for n1 in positions if not n1.endswith('.nd')]
                    stage_pos_maps[basename] = {N: position for N, position in zip(range(1, len(positions) + 1), positions)}
                    print(f"\tFound {len(positions)} stage positions for {basename}.")
                except FileNotFoundError:
                    print(f"\tNo folder found for {basename}. Skipping...")
                    continue
        self.basename_list = basename_list
        self.path_output = path_output
        self.stage_pos_maps = stage_pos_maps

            
    def run_wound_compute(self):
        """Run Wound Compute in parallel."""
        print("Running Wound Compute...")
        basename_list = self.basename_list
        path_output = self.path_output

        time_start = time.time()
        print("\tStarting wound compute for each experiment folder...")
        print("\tStart time:", time.ctime())

        for index, basename in enumerate(basename_list):
            print("\tProcessing folder:", basename)
            wcf.wc_process_folder(os.path.join(path_output, basename), self.max_cpu_usage_percent.value())

        print("\tEnd time:", time.ctime())
        print("\tTotal time taken:", format_timespan(time.time() - time_start))
        print("\tDone running Wound Compute!")


    def check_for_segmentation(self,path_input_fn:str, basename_fn:str, image_type:str='ph1'):
        folder_path_list = sorted(os.scandir(os.path.join(path_input_fn, basename_fn)), key=lambda x: x.name)
        folder_path_list = [n1 for n1 in folder_path_list if os.path.isdir(n1)]

        frames = len(os.listdir(os.path.join(folder_path_list[0].path, image_type + "_images")))
        try:
            metrics = [f for f in os.listdir(os.path.join(folder_path_list[0].path, "segment_" + image_type)) if f.endswith(".txt")]
        except:
            QMessageBox.critical(self, "Error",
                                 "Cannot find folder containing segmented images. Please run again and check the 'Run Wound Compute' option."
                                )
            self.status_label.setText("Ready")
            self.hide_overlay()
            return


    def extract_metadata(
        self,image_type:str='ph1'
    ):
        """Extract metadata."""
        print("Extracting metadata...")
        imaging_interval = self.imaging_interval.value()
        path_output = self.path_output
        basename_list = self.basename_list
        stage_pos_maps = self.stage_pos_maps

        for index, basename in enumerate(basename_list):

            # Check if there's an existing condition map file
            condition_map_path = os.path.join(path_output, f'code_output_{basename}.xlsx')
            if os.path.exists(condition_map_path):
                print("\tFound existing condition map file.")
                try:
                    df_assignments = pd.read_excel(condition_map_path, sheet_name='condition_map')
                except Exception as e:
                    print("\tError reading condition map file:", e)
                    df_assignments = None
            else:
                df_assignments = None

            if df_assignments is None:
                # Extract stage position map for the current basename
                stage_pos_map = stage_pos_maps.get(basename, {})

                # Initialize the PyQt5-based WellPlateInterface
                dialog = wpg.WellPlateInterface(stage_pos_map, basename)

                # Make the dialog modal and wait for user input
                if dialog.exec_() == QDialog.Accepted:
                    df_assignments = dialog.get_assigned_dataframe()

                    # Save the condition map to an Excel file
                    df_assignments.to_excel(condition_map_path, sheet_name='condition_map', index=False)
                    print("\tCondition map saved to Excel file")

            # Extract data from the folders and create an Excel file
            dm.extract_data(
                path_output, basename, image_type, imaging_interval, df_assignments
            )
            print(f"\tData extracted to Excel file in {basename}.xlsx")
            
            # Move ph1_contour_all_*.png images from all samples into the same folder
            dm.find_and_copy_contour_images(
                path_output, basename, image_type
            )
            print(f"\tDone extracting data!")


    def visualize_data(self):
        """Visualize data."""
        print("Visualizing data...")
        vis_window = VisualizationWindow(self.path_output)
        vis_window.exec_()
#         vis_window.show()


    def show_overlay(self):
        if not self.overlay:
            self.overlay = QWidget(self)
            self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 128);")
            self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.overlay.resize(self.size())
        self.overlay.show()
        self.overlay.raise_()


    def hide_overlay(self):
        if self.overlay:
            self.overlay.hide()


    def close_app(self):
        """Close the application."""
        self.close()