import pandas as pd
import re
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QComboBox, 
    QGridLayout, QVBoxLayout, QHBoxLayout, QFrame, QMessageBox
)


class WellPlateInterface(QDialog):
    def __init__(self, stage_pos_map_in, basename_in):
        super().__init__()
        self.setWindowTitle(f"96-Well Plate Layout: {basename_in}")

        self.conditions = []
        self.wells = {}
        self.df = pd.DataFrame(columns=['Well', 'Condition_Number', 'Condition_Name'])

        # Filter stage_pos_map
        self.stage_pos_map_out = self.filter_stage_pos_map(stage_pos_map_in)
        print(f'wellplate stage_pos_map_out = {self.stage_pos_map_out}')

        if not self.stage_pos_map_out:
            QMessageBox.critical(self, "Error", "Invalid stage position map. Assigning all wells to condition 1.")
            self.df = pd.DataFrame({'Well': list(stage_pos_map_in.values()), 
                                    'Condition_Number': 1, 
                                    'Condition_Name': 'Condition_1'})
            self.reject()  # Close dialog if error

        # Extract positions for the given basename
        self.allowed_wells = set(self.stage_pos_map_out.values())

        self.init_ui()

    def filter_stage_pos_map(self, stage_pos_map_in):
        pattern = re.compile(r'([A-H]\d{2})')
        stage_pos_map_out = {k: pattern.search(v).group(1) for k, v in stage_pos_map_in.items() if pattern.search(v)}
        return stage_pos_map_out

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Input for number of conditions
        condition_layout = QHBoxLayout()
        condition_layout.addWidget(QLabel("Number of Conditions (Integer Only):"))
        self.condition_entry = QLineEdit("1")
        self.condition_entry.setFixedWidth(50)
        condition_layout.addWidget(self.condition_entry)

        set_btn = QPushButton("Set")
        set_btn.clicked.connect(self.update_conditions)
        condition_layout.addWidget(set_btn)
        main_layout.addLayout(condition_layout)

        # Frame for condition names
        self.condition_frame = QFrame()
        self.condition_frame_layout = QGridLayout()
        self.condition_frame.setLayout(self.condition_frame_layout)
        main_layout.addWidget(self.condition_frame)

        # Condition dropdown and buttons
        action_layout = QHBoxLayout()
        self.condition_dropdown = QComboBox()
        action_layout.addWidget(self.condition_dropdown)

        assign_btn = QPushButton("Assign Condition")
        assign_btn.clicked.connect(self.assign_condition)
        action_layout.addWidget(assign_btn)

        unassign_btn = QPushButton("Unassign Wells")
        unassign_btn.clicked.connect(self.unassign_wells)
        action_layout.addWidget(unassign_btn)

        finish_btn = QPushButton("Finish Assignment")
        finish_btn.clicked.connect(self.end_selection)
        action_layout.addWidget(finish_btn)

        select_all_btn = QPushButton("Select/Deselect All")
        select_all_btn.clicked.connect(self.toggle_all_selection)
        action_layout.addWidget(select_all_btn)

        main_layout.addLayout(action_layout)

        # Plate creation
        self.plate_frame = QFrame()
        self.plate_layout = QGridLayout()
        self.plate_frame.setLayout(self.plate_layout)
        self.create_plate()
        main_layout.addWidget(self.plate_frame)

        self.setLayout(main_layout)
        self.update_conditions()

    def update_conditions(self):
        try:
            num_conditions = int(self.condition_entry.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter a valid number")
            return

        # Clear existing entries
        while self.condition_frame_layout.count():
            widget = self.condition_frame_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()

        self.conditions.clear()
        self.condition_entries = []

        # Create new entries
        for i in range(num_conditions):
            label = QLabel(f"Condition {i + 1}:")
            entry = QLineEdit(f"Condition_{i + 1}")
            self.condition_frame_layout.addWidget(label, i, 0)
            self.condition_frame_layout.addWidget(entry, i, 1)
            entry.textChanged.connect(self.update_dropdown)
            self.condition_entries.append(entry)

        self.update_dropdown()

    def update_dropdown(self):
        self.conditions = [entry.text() for entry in self.condition_entries]
        self.condition_dropdown.clear()
        self.condition_dropdown.addItems(self.conditions)

    def create_plate(self):
        for row in range(8):
            for col in range(12):
                well = f"{chr(65 + row)}{col + 1:02}"
                button = QPushButton(well)
                button.setCheckable(True)
                button.setFixedSize(90, 45)  # Width, height
                if well not in self.allowed_wells:
                    button.setDisabled(True)
                    button.setStyleSheet("color: grey; font-style: italic;")
                else:
                    button.clicked.connect(lambda checked, w=well: self.toggle_selection(w))
                self.plate_layout.addWidget(button, row, col)
                self.wells[well] = {"button": button, "selected": False, "condition": None}

    def toggle_selection(self, well):
        if well in self.allowed_wells:
            button = self.wells[well]["button"]
            self.wells[well]["selected"] = not self.wells[well]["selected"]
            button.setChecked(self.wells[well]["selected"])

    def assign_condition(self):
        condition_name = self.condition_dropdown.currentText()
        condition_number = self.conditions.index(condition_name) + 1
        for well, info in self.wells.items():
            if info["selected"]:  # Only assign to selected wells
                button = info["button"]
                button.setText(f"{well}\n{condition_name}")
                info['condition'] = condition_name
                info["selected"] = False  # Uncheck after assignment
                button.setChecked(False)
        self.reset_well_selection()

    def unassign_wells(self):
        for well, info in self.wells.items():
            if info["selected"]:  # Only unassign from selected wells
                button = info["button"]
                info["condition"] = None
                button.setText(well)  # Reset text to just the well name
                info["selected"] = False  # Uncheck after unassignment
                button.setChecked(False)
        self.reset_well_selection()

    def reset_well_selection(self):
        for well, info in self.wells.items():
            info["selected"] = False
            info["button"].setChecked(False)

    def end_selection(self):
        self.accept()  # Close the dialog and save

    def toggle_all_selection(self):
        all_selected = all(info["selected"] for well, info in self.wells.items() if well in self.allowed_wells)
        for well, info in self.wells.items():
            if well in self.allowed_wells:
                button = info["button"]
                new_state = not all_selected
                button.setChecked(new_state)
                info["selected"] = new_state

    def get_assigned_dataframe(self):
        """Return the assigned dataframe."""
        data = []
        for well, info in self.wells.items():
            if info['condition'] is not None:
                condition_name = info['condition']
                condition_number = self.conditions.index(condition_name) + 1
                data.append({
                    'Well': well,
                    'Condition_Number': condition_number,
                    'Condition_Name': condition_name
                })
        return pd.DataFrame(data)