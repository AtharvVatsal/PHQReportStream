"""PyQt5 GUI for HP Police ReportStream Desktop Application."""

import sys
import os
import threading
import time
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QLabel,
    QTabWidget, QDialog, QLineEdit, QMessageBox, QFileDialog,
    QGroupBox, QCheckBox, QScrollArea, QFrame, QProgressBar,
    QSplitter, QStatusBar, QMenuBar, QMenu, QAction, QScrollBar,
    QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QPixmap

# Import backend services directly
from app.services.extractor import extraction_service
from app.services.pdf_service import pdf_service
from app.services.export_service import export_service
from app.database import (
    init_db, save_report_simple as save_report, 
    get_all_reports_simple as get_all_reports,
    get_reports_count_simple as get_reports_count,
    delete_report_simple as db_delete_report
)
from app.core.config import settings

# Configuration
ADMIN_PASSWORD = "admin@123"
APP_TITLE = "HP Police ReportStream"
APP_VERSION = "4.0.0"

AI_MODE_INFO = {
    "fast": ("Regex + Typo Dictionary", "Fastest, ~70% accuracy"),
    "accurate": ("spaCy NER + BERT", "Balanced, ~85% accuracy"),
    "llm": ("Ollama LLM", "Most accurate, requires Ollama")
}


def get_asset_path(filename):
    """Get path to asset file."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "assets", filename)


class ProcessWorker(QThread):
    """Worker thread for processing reports."""
    finished = pyqtSignal(dict, dict, float, list)
    error = pyqtSignal(str)
    
    def __init__(self, text, ai_mode):
        super().__init__()
        self.text = text
        self.ai_mode = ai_mode
    
    def run(self):
        try:
            from app.services.ai_coordinator import get_ai_coordinator
            coordinator = get_ai_coordinator()
            coordinator.switch_mode(self.ai_mode)
            result = coordinator.extract(self.text)
            
            self.finished.emit(
                result.extracted, 
                result.confidences, 
                result.processing_time, 
                result.corrections
            )
        except Exception as e:
            import traceback
            print(f"ProcessWorker error: {e}")
            print(traceback.format_exc())
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.current_result = None
        self.current_confidences = None
        self.current_corrections = []
        self.pending_corrections = {}
        self.process_worker = None
        self.init_db()
        self.init_ui()
    
    def init_db(self):
        """Initialize database."""
        try:
            init_db()
        except Exception as e:
            print(f"Database init error: {e}")
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(f"{APP_TITLE} v{APP_VERSION}")
        
        # Set window icon
        icon_path = get_asset_path("Himachal_Pradesh_Police_Logo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget with tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Create tabs
        self.process_tab = self.create_process_tab()
        self.batch_tab = self.create_batch_tab()
        self.templates_tab = self.create_templates_tab()
        self.analytics_tab = self.create_analytics_tab()
        
        self.tabs.addTab(self.process_tab, "📋 Single Report")
        self.tabs.addTab(self.batch_tab, "📚 Batch Processing")
        self.tabs.addTab(self.templates_tab, "📄 Templates")
        self.tabs.addTab(self.analytics_tab, "📊 Analytics")
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Center window
        self.center()
    
    def center(self):
        """Center the window on screen."""
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2,
                  (screen.height() - size.height()) // 2)
    
    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Report", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.clear_input)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        
        admin_action = QAction("Admin Settings...", self)
        admin_action.triggered.connect(self.show_admin_dialog)
        settings_menu.addAction(admin_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_process_tab(self) -> QWidget:
        """Create the process report tab."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Left panel - Input
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Logo header
        logo_label = QLabel()
        logo_path = get_asset_path("Himachal_Pradesh_Police_Logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(200, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            left_layout.addWidget(logo_label)
        
        # Input group
        input_group = QGroupBox("📝 Enter Report Text")
        input_layout = QVBoxLayout()
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText(
            "Paste your HP Police IRBn/Bn report here...\n\n"
            "Example:\n"
            "Name of IRBn/Bn: 1st HPAP BN Junga, Shimla\n"
            "1. Reserves Deployed: Yes\n"
            "2. Districts where force deployed: Shimla, Kangra\n"
            "..."
        )
        self.input_text.setFont(QFont("Courier New", 10))
        self.input_text.setMinimumHeight(300)
        input_layout.addWidget(self.input_text)
        
        # Options
        options_layout = QHBoxLayout()
        
        ai_mode_label = QLabel("AI Mode:")
        options_layout.addWidget(ai_mode_label)
        
        self.ai_mode_combo = QComboBox()
        self.ai_mode_combo.addItems(["fast", "accurate", "llm"])
        self.ai_mode_combo.setCurrentText(settings.AI_MODE)
        self.ai_mode_combo.setToolTip(
            "Fast: Regex + Typo Dictionary\n"
            "Accurate: spaCy NER + BERT (Recommended)\n"
            "LLM: Ollama (Requires Ollama installed)"
        )
        options_layout.addWidget(self.ai_mode_combo)
        
        self.ai_status_label = QLabel("")
        self.ai_status_label.setStyleSheet("color: gray; font-size: 10px;")
        options_layout.addWidget(self.ai_status_label)
        
        options_layout.addStretch()
        
        self.process_btn = QPushButton("⚡ Process Report")
        self.process_btn.setMinimumHeight(40)
        self.process_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:disabled { background-color: #94a3b8; }
        """)
        self.process_btn.clicked.connect(self.process_report)
        options_layout.addWidget(self.process_btn)
        
        input_layout.addLayout(options_layout)
        input_group.setLayout(input_layout)
        left_layout.addWidget(input_group)
        
        # Sample button
        sample_btn = QPushButton("📄 Load Sample")
        sample_btn.clicked.connect(self.load_sample)
        left_layout.addWidget(sample_btn)
        
        # Right panel - Results
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Stats
        stats_group = QGroupBox("📈 Results")
        stats_layout = QHBoxLayout()
        
        self.fields_label = QLabel("Fields: -")
        self.confidence_label = QLabel("Confidence: -")
        self.time_label = QLabel("Time: -")
        self.format_label = QLabel("Format: -")
        
        for label in [self.fields_label, self.confidence_label, 
                      self.time_label, self.format_label]:
            label.setStyleSheet("font-weight: bold;")
            stats_layout.addWidget(label)
        
        stats_group.setLayout(stats_layout)
        right_layout.addWidget(stats_group)
        
        # Results table
        results_group = QGroupBox("📋 Extracted Fields")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Field", "Value", "Confidence"])
        self.results_table.setColumnWidth(0, 200)
        self.results_table.setColumnWidth(1, 400)
        self.results_table.setColumnWidth(2, 120)
        results_layout.addWidget(self.results_table)
        
        results_group.setLayout(results_layout)
        right_layout.addWidget(results_group)
        
        # Corrections panel
        self.corrections_group = QGroupBox("✨ AI Text Corrections")
        self.corrections_layout = QVBoxLayout()
        self.corrections_group.setLayout(self.corrections_layout)
        right_layout.addWidget(self.corrections_group)
        
        # Export buttons
        export_layout = QHBoxLayout()
        
        pdf_btn = QPushButton("📄 Export PDF")
        pdf_btn.clicked.connect(self.export_pdf)
        export_layout.addWidget(pdf_btn)
        
        excel_btn = QPushButton("📊 Export Excel")
        excel_btn.clicked.connect(self.export_excel)
        export_layout.addWidget(excel_btn)
        
        csv_btn = QPushButton("📋 Export CSV")
        csv_btn.clicked.connect(self.export_csv)
        export_layout.addWidget(csv_btn)
        
        json_btn = QPushButton("📦 Export JSON")
        json_btn.clicked.connect(self.export_json)
        export_layout.addWidget(json_btn)
        
        export_layout.addStretch()
        
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self.clear_results)
        export_layout.addWidget(clear_btn)
        
        right_layout.addLayout(export_layout)
        
        # Add panels to main layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
        return widget
    
    def create_batch_tab(self) -> QWidget:
        """Create the batch processing tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Logo header
        logo_label = QLabel()
        logo_path = get_asset_path("Himachal_Pradesh_Police_Logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(200, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)
        
        # Instructions
        info_label = QLabel(
            "Paste multiple reports below. Reports can be separated by:\n"
            "• Numbered format (1., 2., 3.)\n"
            "• Double newlines\n"
            "Click 'Process All' when ready."
        )
        info_label.setStyleSheet("color: #7f8c8d; padding: 10px;")
        layout.addWidget(info_label)
        
        # Batch input text area
        batch_group = QGroupBox("Batch Input")
        batch_layout = QVBoxLayout()
        
        self.batch_input = QTextEdit()
        self.batch_input.setPlaceholderText(
            "Name of IRBn/Bn: 1st HPAP BN Junga\n"
            "1. Reserves Deployed: Shimla: 25\n"
            "...\n"
            "\n"
            "Name of IRBn/Bn: 2nd HPAP BN\n"
            "1. Reserves Deployed: Kangra: 30\n"
            "..."
        )
        self.batch_input.setMinimumHeight(300)
        batch_layout.addWidget(self.batch_input)
        
        batch_group.setLayout(batch_layout)
        layout.addWidget(batch_group)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.batch_process_btn = QPushButton("📚 Process All")
        self.batch_process_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.batch_process_btn.clicked.connect(self.process_batch)
        controls_layout.addWidget(self.batch_process_btn)
        
        clear_batch_btn = QPushButton("🗑️ Clear")
        clear_batch_btn.clicked.connect(self.batch_input.clear)
        controls_layout.addWidget(clear_batch_btn)
        
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Progress
        self.batch_progress = QProgressBar()
        self.batch_progress.setVisible(False)
        layout.addWidget(self.batch_progress)
        
        # Results
        results_group = QGroupBox("Batch Results")
        results_layout = QVBoxLayout()
        
        self.batch_results_table = QTableWidget()
        self.batch_results_table.setColumnCount(5)
        self.batch_results_table.setHorizontalHeaderLabels(["#", "Unit Name", "Districts", "Confidence", "Status"])
        self.batch_results_table.setMinimumHeight(200)
        results_layout.addWidget(self.batch_results_table)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        return widget
    
    def process_batch(self):
        """Process multiple reports."""
        text = self.batch_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Warning", "Please enter reports to process")
            return
        
        from app.services.extractor import extraction_service
        reports = extraction_service.split_reports(text)
        
        if len(reports) < 2:
            QMessageBox.warning(self, "Warning", "Please enter at least 2 reports to batch process")
            return
        
        self.batch_process_btn.setEnabled(False)
        self.batch_process_btn.setText("Processing...")
        self.batch_progress.setVisible(True)
        self.batch_progress.setMaximum(len(reports))
        self.batch_progress.setValue(0)
        
        # Process each report
        self.batch_results = []
        self.batch_results_table.setRowCount(0)
        
        for i, report_text in enumerate(reports):
            try:
                from app.services.extractor import extraction_service
                extracted, confidences, proc_time, corrections = extraction_service.extract(report_text, False)
                
                avg_conf = sum(confidences.values()) / len(confidences) if confidences else 0
                
                row = self.batch_results_table.rowCount()
                self.batch_results_table.insertRow(row)
                self.batch_results_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.batch_results_table.setItem(row, 1, QTableWidgetItem(extracted.get("unit_name", "-")[:30]))
                self.batch_results_table.setItem(row, 2, QTableWidgetItem(extracted.get("districts", "-")[:20]))
                self.batch_results_table.setItem(row, 3, QTableWidgetItem(f"{avg_conf*100:.1f}%"))
                self.batch_results_table.setItem(row, 4, QTableWidgetItem("✓ Success"))
                self.batch_results_table.item(row, 4).setBackground(QColor(144, 238, 144))
                
                self.batch_results.append({
                    "extracted": extracted,
                    "confidences": confidences,
                    "corrections": corrections
                })
                
            except Exception as e:
                row = self.batch_results_table.rowCount()
                self.batch_results_table.insertRow(row)
                self.batch_results_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.batch_results_table.setItem(row, 1, QTableWidgetItem("-"))
                self.batch_results_table.setItem(row, 2, QTableWidgetItem("-"))
                self.batch_results_table.setItem(row, 3, QTableWidgetItem("-"))
                self.batch_results_table.setItem(row, 4, QTableWidgetItem(f"✗ Error: {str(e)[:20]}"))
                self.batch_results_table.item(row, 4).setBackground(QColor(255, 182, 193))
            
            self.batch_progress.setValue(i + 1)
        
        self.batch_process_btn.setEnabled(True)
        self.batch_process_btn.setText("📚 Process All")
        self.status_bar.showMessage(f"Batch processing complete: {len(reports)} reports")
        
        # Save all to database if auto-save enabled
        if settings.AUTO_SAVE_ENABLED and self.batch_results:
            for i, result in enumerate(self.batch_results):
                try:
                    report_id = f"batch_{get_reports_count() + 1}_{i+1}"
                    extracted = result["extracted"]
                    confidences = result["confidences"]
                    report_data = {
                        "id": report_id,
                        "unit_name": extracted.get("unit_name", ""),
                        "reserves_deployed": extracted.get("reserves_deployed", ""),
                        "districts": extracted.get("districts", ""),
                        "stay_arrangement": extracted.get("stay_arrangement", ""),
                        "messing": extracted.get("messing", ""),
                        "co_interaction_date": extracted.get("co_interaction_date", ""),
                        "disciplinary_issues": extracted.get("disciplinary_issues", ""),
                        "reserves_detained": extracted.get("reserves_detained", ""),
                        "training": extracted.get("training", ""),
                        "welfare": extracted.get("welfare", ""),
                        "reserves_available": extracted.get("reserves_available", ""),
                        "issues_for_phq": extracted.get("issues_for_phq", ""),
                        "confidence_scores": confidences,
                        "detected_format": "batch",
                        "raw_input": reports[i][:2000],
                        "processing_time": 0,
                        "created_at": datetime.now()
                    }
                    save_report(report_data)
                except Exception as e:
                    print(f"Batch save error: {e}")
            
            QMessageBox.information(self, "Saved", f"Saved {len(self.batch_results)} reports to database")
    
    def create_templates_tab(self) -> QWidget:
        """Create the templates tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Logo header
        logo_label = QLabel()
        logo_path = get_asset_path("Himachal_Pradesh_Police_Logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(200, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)
        
        # Instructions
        info_label = QLabel("Select a template to use or create your own.")
        info_label.setStyleSheet("color: #7f8c8d; padding: 10px;")
        layout.addWidget(info_label)
        
        # Templates list
        templates_group = QGroupBox("Available Templates")
        templates_layout = QVBoxLayout()
        
        self.templates_list = QTableWidget()
        self.templates_list.setColumnCount(3)
        self.templates_list.setHorizontalHeaderLabels(["Name", "Description", "Fields"])
        self.templates_list.setMinimumHeight(250)
        templates_layout.addWidget(self.templates_list)
        
        # Load templates
        self.load_templates()
        
        templates_group.setLayout(templates_layout)
        layout.addWidget(templates_group)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        use_template_btn = QPushButton("📝 Use Selected")
        use_template_btn.clicked.connect(self.use_selected_template)
        controls_layout.addWidget(use_template_btn)
        
        new_template_btn = QPushButton("➕ New Template")
        new_template_btn.clicked.connect(self.create_new_template)
        controls_layout.addWidget(new_template_btn)
        
        edit_template_btn = QPushButton("✏️ Edit")
        edit_template_btn.clicked.connect(self.edit_selected_template)
        controls_layout.addWidget(edit_template_btn)
        
        delete_template_btn = QPushButton("🗑️ Delete")
        delete_template_btn.clicked.connect(self.delete_selected_template)
        controls_layout.addWidget(delete_template_btn)
        
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Preview
        preview_group = QGroupBox("Template Preview")
        preview_layout = QVBoxLayout()
        
        self.template_preview = QTextEdit()
        self.template_preview.setReadOnly(True)
        self.template_preview.setMaximumHeight(150)
        preview_layout.addWidget(self.template_preview)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        return widget
    
    def load_templates(self):
        """Load templates from file."""
        # Default templates
        default_templates = [
            {
                "id": "standard_daily",
                "name": "Daily IRBn Report (Standard)",
                "description": "Standard daily report format for IRBn/Bn",
                "content": """Name of IRBn/Bn: [UNIT NAME]

1. Reserves Deployed: [DETAILS]
2. Districts where force deployed: [DISTRICTS]
3. Stay Arrangement/Bathrooms: [QUALITY]
4. Messing Arrangements: [RATING]
5. CO's last Interaction with SP: [DD.MM.YYYY]
6. Disciplinary Issues: [NIL/DETAILS]
7. Reserves Detained: [NIL/DETAILS]
8. Training: [NIL/DETAILS]
9. Welfare Initiative in Last 24 Hrs: [NIL/DETAILS]
10. Reserves Available in Bn: [NUMBER]
11. Issue for AP&T/PHQ: [NIL/DETAILS]"""
            },
            {
                "id": "special_deployment",
                "name": "Special Deployment Report",
                "description": "For special duty deployments",
                "content": """Name of IRBn/Bn: [UNIT NAME]
Deployment Type: [SPECIAL DUTY]

1. Reserves Deployed: [DETAILS]
2. Districts where force deployed: [DISTRICTS]
3. Stay Arrangement: [ACCOMMODATION]
4. Messing Arrangements: [RATING]
5. CO's last Interaction with SP: [DD.MM.YYYY]
6. Disciplinary Issues: [NIL/DETAILS]
7. Special Equipment: [LIST]
8. Training: [NIL/DETAILS]
9. Welfare: [NIL/DETAILS]
10. Reserves Available: [NUMBER]
11. Issues: [NIL/DETAILS]"""
            },
            {
                "id": "emergency_reserve",
                "name": "Emergency Reserve Report",
                "description": "Emergency reserve deployment",
                "content": """Name of IRBn/Bn: [UNIT NAME]
Emergency Type: [URGENT]

1. Reserves Deployed: [NUMBER + DETAILS]
2. Deployment Area: [DISTRICT]
3. Stay Arrangement: [STATUS]
4. Messing: [STATUS]
5. CO's last Interaction: [DD.MM.YYYY]
6. Disciplinary Issues: [NIL]
7. Reserves Detained: [NUMBER]
8. Training: [NIL]
9. Welfare: [NIL]
10. Available Reserves: [NUMBER]
11. Issues: [NIL]"""
            }
        ]
        
        self.templates = default_templates
        self.templates_list.setRowCount(len(default_templates))
        
        for i, template in enumerate(default_templates):
            self.templates_list.setItem(i, 0, QTableWidgetItem(template["name"]))
            self.templates_list.setItem(i, 1, QTableWidgetItem(template["description"]))
            self.templates_list.setItem(i, 2, QTableWidgetItem("12"))
    
    def use_selected_template(self):
        """Use selected template."""
        current_row = self.templates_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a template")
            return
        
        template = self.templates[current_row]
        
        # Switch to process tab and fill in template
        self.tabs.setCurrentIndex(0)
        self.input_text.setPlainText(template["content"])
        self.status_bar.showMessage(f"Template '{template['name']}' loaded")
    
    def create_new_template(self):
        """Create a new template."""
        dialog = TemplateDialog(self, None)
        if dialog.exec_():
            QMessageBox.information(self, "Success", "Template created!")
    
    def edit_selected_template(self):
        """Edit selected template."""
        current_row = self.templates_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a template to edit")
            return
        
        template = self.templates[current_row]
        dialog = TemplateDialog(self, template)
        if dialog.exec_():
            QMessageBox.information(self, "Success", "Template updated!")
    
    def delete_selected_template(self):
        """Delete selected template."""
        current_row = self.templates_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a template to delete")
            return
        
        reply = QMessageBox.question(
            self, "Confirm", "Delete this template?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self.templates[current_row]
            self.load_templates()
            QMessageBox.information(self, "Success", "Template deleted")
    
    def create_analytics_tab(self) -> QWidget:
        """Create the analytics tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Logo header
        logo_label = QLabel()
        logo_path = get_asset_path("Himachal_Pradesh_Police_Logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(200, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)
        
        # Summary stats
        stats_group = QGroupBox("📊 Summary Statistics")
        stats_layout = QHBoxLayout()
        
        self.total_reports_label = QLabel("Total Reports: 0")
        self.avg_confidence_label = QLabel("Avg Confidence: 0%")
        self.high_conf_label = QLabel("High Confidence: 0")
        
        for label in [self.total_reports_label, self.avg_confidence_label, 
                      self.high_conf_label]:
            label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
            stats_layout.addWidget(label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Search and Filter
        search_group = QGroupBox("🔍 Search & Filter")
        search_layout = QVBoxLayout()
        
        # Search bar
        search_bar_layout = QHBoxLayout()
        search_bar_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by unit name, district, keywords...")
        self.search_input.textChanged.connect(self.on_search_changed)
        search_bar_layout.addWidget(self.search_input)
        
        clear_search_btn = QPushButton("Clear")
        clear_search_btn.clicked.connect(self.clear_search)
        search_bar_layout.addWidget(clear_search_btn)
        
        search_layout.addLayout(search_bar_layout)
        
        # Filters
        filters_layout = QHBoxLayout()
        
        filters_layout.addWidget(QLabel("District:"))
        self.district_filter = QLineEdit()
        self.district_filter.setPlaceholderText("e.g., Shimla")
        self.district_filter.textChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.district_filter)
        
        filters_layout.addWidget(QLabel("Min Confidence:"))
        self.confidence_filter = QComboBox()
        self.confidence_filter.addItems(["All", "90%+", "70%+", "50%+"])
        self.confidence_filter.currentTextChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.confidence_filter)
        
        apply_filter_btn = QPushButton("Apply Filters")
        apply_filter_btn.clicked.connect(self.apply_filters)
        filters_layout.addWidget(apply_filter_btn)
        
        filters_layout.addStretch()
        
        search_layout.addLayout(filters_layout)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_analytics)
        layout.addWidget(refresh_btn)
        
        # Reports table
        reports_group = QGroupBox("📋 Reports")
        reports_layout = QVBoxLayout()
        
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(7)
        self.reports_table.setHorizontalHeaderLabels([
            "ID", "Unit Name", "Districts", "Format", "Confidence", "Date", "Actions"
        ])
        self.reports_table.setMinimumHeight(350)
        reports_layout.addWidget(self.reports_table)
        
        reports_group.setLayout(reports_layout)
        layout.addWidget(reports_group)
        
        # Delete button
        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.clicked.connect(self.delete_selected_report)
        layout.addWidget(delete_btn)
        
        # Load initial data
        QTimer.singleShot(100, self.load_analytics)
        
        return widget
    
    def on_search_changed(self, text):
        """Handle search input changes."""
        if len(text) >= 2:
            self.perform_search(text)
        elif len(text) == 0:
            self.load_analytics()
    
    def perform_search(self, keyword: str):
        """Search reports by keyword."""
        from app.database import search_reports_simple
        
        try:
            results = search_reports_simple(keyword)
            self.display_reports(results)
            self.status_bar.showMessage(f"Found {len(results)} reports matching '{keyword}'")
        except Exception as e:
            print(f"Search error: {e}")
    
    def clear_search(self):
        """Clear search and reload all reports."""
        self.search_input.clear()
        self.district_filter.clear()
        self.confidence_filter.setCurrentIndex(0)
        self.load_analytics()
    
    def apply_filters(self):
        """Apply filters to reports."""
        from app.database import filter_reports_simple
        from datetime import datetime
        
        district = self.district_filter.text().strip() or None
        conf_text = self.confidence_filter.currentText()
        
        min_conf = None
        if conf_text == "90%+":
            min_conf = 0.9
        elif conf_text == "70%+":
            min_conf = 0.7
        elif conf_text == "50%+":
            min_conf = 0.5
        
        try:
            results = filter_reports_simple(
                district=district,
                min_confidence=min_conf
            )
            self.display_reports(results)
            self.status_bar.showMessage(f"Filtered: {len(results)} reports")
        except Exception as e:
            print(f"Filter error: {e}")
    
    def process_report(self):
        """Process the input text."""
        text = self.input_text.toPlainText().strip()
        
        if not text:
            QMessageBox.warning(self, "Warning", "Please enter report text")
            return
        
        self.process_btn.setEnabled(False)
        self.process_btn.setText("Processing...")
        self.status_bar.showMessage("Processing report...")
        
        ai_mode = self.ai_mode_combo.currentText()
        
        self.process_worker = ProcessWorker(text, ai_mode)
        self.process_worker.finished.connect(self.on_process_finished)
        self.process_worker.error.connect(self.on_process_error)
        self.process_worker.start()
        
        mode_desc = AI_MODE_INFO.get(ai_mode, ("", ""))[0]
        self.status_bar.showMessage(f"Processing in {mode_desc} mode...")
    
    def on_process_finished(self, extracted, confidences, proc_time, corrections):
        """Handle processing completion."""
        self.current_result = extracted
        self.current_confidences = confidences
        
        # Auto-save to database (if enabled)
        if settings.AUTO_SAVE_ENABLED:
            try:
                report_id = f"report_{get_reports_count() + 1}"
                report_data = {
                    "id": report_id,
                    "unit_name": extracted.get("unit_name", ""),
                    "reserves_deployed": extracted.get("reserves_deployed", ""),
                    "districts": extracted.get("districts", ""),
                    "stay_arrangement": extracted.get("stay_arrangement", ""),
                    "messing": extracted.get("messing", ""),
                    "co_interaction_date": extracted.get("co_interaction_date", ""),
                    "disciplinary_issues": extracted.get("disciplinary_issues", ""),
                    "reserves_detained": extracted.get("reserves_detained", ""),
                    "training": extracted.get("training", ""),
                    "welfare": extracted.get("welfare", ""),
                    "reserves_available": extracted.get("reserves_available", ""),
                    "issues_for_phq": extracted.get("issues_for_phq", ""),
                    "confidence_scores": confidences,
                    "detected_format": "v2",
                    "raw_input": self.input_text.toPlainText()[:2000],
                    "processing_time": proc_time,
                    "created_at": datetime.now()
                }
                save_report(report_data)
                self.status_bar.showMessage("Report processed and saved ✓", 3000)
            except Exception as e:
                print(f"Save error: {e}")
        else:
            self.status_bar.showMessage(f"Report processed in {proc_time:.3f}s", 3000)
        
        # Update stats
        filled = sum(1 for v in extracted.values() if v and v != "Nil")
        avg_conf = sum(confidences.values()) / len(confidences) if confidences else 0
        validation = extraction_service.validate_structure(self.input_text.toPlainText())
        
        self.fields_label.setText(f"Fields: {filled}/12")
        self.confidence_label.setText(f"Confidence: {avg_conf*100:.1f}%")
        self.time_label.setText(f"Time: {proc_time:.3f}s")
        self.format_label.setText(f"Mode: {self.ai_mode_combo.currentText().upper()}")
        
        # Update results table
        self.results_table.setRowCount(0)
        
        field_names = {
            "unit_name": "Name of IRBn/Bn",
            "reserves_deployed": "Reserves Deployed",
            "districts": "Districts",
            "stay_arrangement": "Stay Arrangement",
            "messing": "Messing",
            "co_interaction_date": "CO Interaction Date",
            "disciplinary_issues": "Disciplinary Issues",
            "reserves_detained": "Reserves Detained",
            "training": "Training",
            "welfare": "Welfare",
            "reserves_available": "Reserves Available",
            "issues_for_phq": "Issues for PHQ"
        }
        
        for field_key, display_name in field_names.items():
            value = extracted.get(field_key, "")
            conf = confidences.get(field_key, 0)
            
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            self.results_table.setItem(row, 0, QTableWidgetItem(display_name))
            self.results_table.setItem(row, 1, QTableWidgetItem(value or "-"))
            
            conf_item = QTableWidgetItem(f"{conf*100:.0f}%")
            if conf >= 0.7:
                conf_item.setBackground(QColor(144, 238, 144))  # Green
            elif conf >= 0.5:
                conf_item.setBackground(QColor(255, 230, 153))  # Yellow
            else:
                conf_item.setBackground(QColor(255, 182, 193))  # Red
            self.results_table.setItem(row, 2, conf_item)
        
        # Store corrections
        self.current_corrections = corrections
        self.pending_corrections = {i: corr for i, corr in enumerate(corrections)}
        
        # Show corrections
        self.display_corrections()
        
        self.process_btn.setEnabled(True)
        self.process_btn.setText("⚡ Process Report")
        self.status_bar.showMessage(f"Report processed in {proc_time:.3f}s")
    
    def display_corrections(self):
        """Display text corrections panel."""
        if not hasattr(self, 'corrections_group'):
            return
        
        # Clear existing correction items
        while self.corrections_layout.count():
            item = self.corrections_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.pending_corrections:
            no_corr_label = QLabel("✓ No corrections needed - all text looks good!")
            no_corr_label.setStyleSheet("color: green; font-weight: bold; padding: 10px;")
            self.corrections_layout.addWidget(no_corr_label)
            return
        
        # Add header
        header = QLabel(f"✨ AI Text Corrections ({len(self.pending_corrections)} available)")
        header.setStyleSheet("font-weight: bold; font-size: 14px; color: #f39c12;")
        self.corrections_layout.addWidget(header)
        
        # Add each correction
        for idx, corr_data in list(self.pending_corrections.items()):
            corr_widget = QWidget()
            corr_layout = QHBoxLayout(corr_widget)
            corr_layout.setContentsMargins(5, 5, 5, 5)
            
            field_label = QLabel(f"<b>{corr_data['field_name']}</b>")
            field_label.setMinimumWidth(150)
            
            orig_label = QLabel(f"<span style='color: #e74c3c;'>{corr_data['original'][:50]}</span>")
            if len(corr_data['original']) > 50:
                orig_label.setText(orig_label.text() + "...")
            
            arrow_label = QLabel("→")
            arrow_label.setStyleSheet("color: #7f8c8d; font-size: 14px;")
            
            corrected_label = QLabel(f"<span style='color: #27ae60; font-weight: bold;'>{corr_data['corrected'][:50]}</span>")
            if len(corr_data['corrected']) > 50:
                corrected_label.setText(corrected_label.text() + "...")
            
            type_label = QLabel(f"<span style='color: #3498db; font-size: 11px;'>{corr_data['type']}</span>")
            
            apply_btn = QPushButton("✓")
            apply_btn.setToolTip("Apply this correction")
            apply_btn.setFixedWidth(40)
            apply_btn.clicked.connect(lambda checked, i=idx, c=corr_data: self.apply_correction(i, c))
            
            dismiss_btn = QPushButton("✗")
            dismiss_btn.setToolTip("Dismiss this correction")
            dismiss_btn.setFixedWidth(40)
            dismiss_btn.clicked.connect(lambda checked, i=idx: self.dismiss_correction(i))
            
            corr_layout.addWidget(field_label)
            corr_layout.addWidget(orig_label)
            corr_layout.addWidget(arrow_label)
            corr_layout.addWidget(corrected_label)
            corr_layout.addWidget(type_label)
            corr_layout.addStretch()
            corr_layout.addWidget(apply_btn)
            corr_layout.addWidget(dismiss_btn)
            
            corr_widget.setStyleSheet("background: rgba(243, 156, 18, 0.1); border-radius: 5px; padding: 5px; margin: 2px 0;")
            self.corrections_layout.addWidget(corr_widget)
        
        # Add Apply All button
        apply_all_btn = QPushButton("✨ Apply All Corrections")
        apply_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        apply_all_btn.clicked.connect(self.apply_all_corrections)
        self.corrections_layout.addWidget(apply_all_btn)
    
    def apply_correction(self, index, corr_data):
        """Apply a single correction."""
        field_key = corr_data['field_key']
        corrected_value = corr_data['corrected']
        
        if self.current_result and field_key in self.current_result:
            self.current_result[field_key] = corrected_value
            
            field_names = {
                "unit_name": "Name of IRBn/Bn",
                "reserves_deployed": "Reserves Deployed",
                "districts": "Districts",
                "stay_arrangement": "Stay Arrangement",
                "messing": "Messing",
                "co_interaction_date": "CO Interaction Date",
                "disciplinary_issues": "Disciplinary Issues",
                "reserves_detained": "Reserves Detained",
                "training": "Training",
                "welfare": "Welfare",
                "reserves_available": "Reserves Available",
                "issues_for_phq": "Issues for PHQ"
            }
            
            display_name = field_names.get(field_key, field_key)
            
            for row in range(self.results_table.rowCount()):
                if self.results_table.item(row, 0).text() == display_name:
                    self.results_table.setItem(row, 1, QTableWidgetItem(corrected_value))
                    break
        
        if index in self.pending_corrections:
            del self.pending_corrections[index]
        
        self.display_corrections()
        self.status_bar.showMessage(f"Applied correction for {corr_data['field_name']}")
    
    def dismiss_correction(self, index):
        """Dismiss a correction."""
        if index in self.pending_corrections:
            del self.pending_corrections[index]
        self.display_corrections()
        self.status_bar.showMessage("Correction dismissed")
    
    def apply_all_corrections(self):
        """Apply all pending corrections."""
        for corr_data in list(self.pending_corrections.values()):
            field_key = corr_data['field_key']
            corrected_value = corr_data['corrected']
            
            if self.current_result and field_key in self.current_result:
                self.current_result[field_key] = corrected_value
        
        field_names = {
            "unit_name": "Name of IRBn/Bn",
            "reserves_deployed": "Reserves Deployed",
            "districts": "Districts",
            "stay_arrangement": "Stay Arrangement",
            "messing": "Messing",
            "co_interaction_date": "CO Interaction Date",
            "disciplinary_issues": "Disciplinary Issues",
            "reserves_detained": "Reserves Detained",
            "training": "Training",
            "welfare": "Welfare",
            "reserves_available": "Reserves Available",
            "issues_for_phq": "Issues for PHQ"
        }
        
        for field_key, display_name in field_names.items():
            if field_key in self.current_result:
                for row in range(self.results_table.rowCount()):
                    if self.results_table.item(row, 0).text() == display_name:
                        self.results_table.setItem(row, 1, QTableWidgetItem(self.current_result[field_key]))
                        break
        
        self.pending_corrections.clear()
        self.display_corrections()
        self.status_bar.showMessage("All corrections applied")
    
    def on_process_error(self, error_msg):
        """Handle processing error."""
        QMessageBox.critical(self, "Error", f"Processing failed: {error_msg}")
        self.process_btn.setEnabled(True)
        self.process_btn.setText("⚡ Process Report")
        self.status_bar.showMessage("Processing failed")
    
    def export_pdf(self):
        """Export to PDF."""
        if not self.current_result:
            QMessageBox.warning(self, "Warning", "No report to export. Process a report first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", f"HP_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            "PDF Files (*.pdf)"
        )
        
        if file_path:
            try:
                report_dict = {**self.current_result, "processing_time": 0}
                pdf_data = pdf_service.export_pdf(report_dict, self.current_confidences)
                
                with open(file_path, 'wb') as f:
                    f.write(pdf_data)
                
                QMessageBox.information(self, "Success", f"PDF saved to:\n{file_path}")
                self.status_bar.showMessage(f"PDF exported: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")
    
    def export_excel(self):
        """Export to Excel."""
        if not self.current_result:
            QMessageBox.warning(self, "Warning", "No report to export. Process a report first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel", f"HP_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                excel_data = export_service.export_excel(self.current_result, self.current_confidences)
                
                with open(file_path, 'wb') as f:
                    f.write(excel_data)
                
                QMessageBox.information(self, "Success", f"Excel saved to:\n{file_path}")
                self.status_bar.showMessage(f"Excel exported: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")
    
    def export_csv(self):
        """Export to CSV."""
        if not self.current_result:
            QMessageBox.warning(self, "Warning", "No report to export. Process a report first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", f"HP_Report_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                csv_data = export_service.export_csv(self.current_result)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(csv_data)
                
                QMessageBox.information(self, "Success", f"CSV saved to:\n{file_path}")
                self.status_bar.showMessage(f"CSV exported: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")
    
    def export_json(self):
        """Export to JSON."""
        if not self.current_result:
            QMessageBox.warning(self, "Warning", "No report to export. Process a report first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save JSON", f"HP_Report_{datetime.now().strftime('%Y%m%d')}.json",
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                import json
                data = {
                    "report": self.current_result,
                    "confidence_scores": {k: round(v, 3) for k, v in self.current_confidences.items()},
                    "exported_at": datetime.now().isoformat()
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(self, "Success", f"JSON saved to:\n{file_path}")
                self.status_bar.showMessage(f"JSON exported: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")
    
    def load_sample(self):
        """Load sample report text."""
        sample = """Name of IRBn/Bn: 1st HPAP BN Junga, Shimla

1. Reserves Deployed: Yes
2. Districts where force deployed: Shimla, Kangra
3. Stay Arrangement/Bathrooms: Good
4. Messing: Good
5. CO's last Interaction with SP: 05.04.2026
6. Disciplinary Issues: Nil
7. Reserves Detained: Nil
8. Training: Nil
9. Welfare: Nil
10. Reserves Available: Yes
11. Issue for PHQ: Nil"""
        
        self.input_text.setPlainText(sample)
    
    def clear_input(self):
        """Clear the input text."""
        self.input_text.clear()
        self.status_bar.showMessage("Input cleared")
    
    def clear_results(self):
        """Clear the results."""
        self.current_result = None
        self.current_confidences = None
        self.results_table.setRowCount(0)
        self.fields_label.setText("Fields: -")
        self.confidence_label.setText("Confidence: -")
        self.time_label.setText("Time: -")
        self.format_label.setText("Format: -")
        self.status_bar.showMessage("Results cleared")
    
    def load_analytics(self):
        """Load analytics data."""
        try:
            reports = get_all_reports(limit=100)
            total = get_reports_count()
            
            self.total_reports_label.setText(f"Total Reports: {total}")
            
            if reports:
                confidences = []
                high_count = 0
                
                for r in reports:
                    if r.confidence_scores:
                        avg = sum(r.confidence_scores.values()) / len(r.confidence_scores)
                        confidences.append(avg)
                        if avg >= 0.7:
                            high_count += 1
                
                if confidences:
                    avg_conf = sum(confidences) / len(confidences)
                    self.avg_confidence_label.setText(f"Avg Confidence: {avg_conf*100:.1f}%")
                
                self.high_conf_label.setText(f"High Confidence: {high_count}")
            
            # Update table
            self.reports_table.setRowCount(0)
            
            for r in reports:
                row = self.reports_table.rowCount()
                self.reports_table.insertRow(row)
                
                avg_conf = 0
                if r.confidence_scores:
                    avg_conf = sum(r.confidence_scores.values()) / len(r.confidence_scores)
                
                date_str = r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "-"
                
                self.reports_table.setItem(row, 0, QTableWidgetItem(r.id or ""))
                self.reports_table.setItem(row, 1, QTableWidgetItem(r.unit_name or "-"))
                self.reports_table.setItem(row, 2, QTableWidgetItem(r.districts or "-"))
                self.reports_table.setItem(row, 3, QTableWidgetItem(
                    (r.detected_format or "?").upper()
                ))
                
                conf_item = QTableWidgetItem(f"{avg_conf*100:.0f}%")
                if avg_conf >= 0.7:
                    conf_item.setBackground(QColor(144, 238, 144))
                elif avg_conf >= 0.5:
                    conf_item.setBackground(QColor(255, 230, 153))
                self.reports_table.setItem(row, 4, conf_item)
                
                self.reports_table.setItem(row, 5, QTableWidgetItem(date_str))
                
                # Actions column
                view_btn = QPushButton("👁")
                view_btn.setFixedWidth(40)
                view_btn.clicked.connect(lambda checked, rid=r.id: self.view_report(rid))
                self.reports_table.setCellWidget(row, 6, view_btn)
            
            self.status_bar.showMessage(f"Loaded {total} reports")
            
        except Exception as e:
            print(f"Analytics load error: {e}")
    
    def view_report(self, report_id):
        """View a specific report."""
        from app.database import get_report, SessionLocal
        
        db = SessionLocal()
        try:
            report = db.query(get_report(db, report_id).__class__).filter_by(id=report_id).first()
            if report:
                # Switch to process tab and show details
                self.tabs.setCurrentIndex(0)
                self.input_text.setPlainText(report.raw_input or "No raw input")
                self.status_bar.showMessage(f"Viewing report: {report_id}")
        finally:
            db.close()
    
    def delete_selected_report(self):
        """Delete the selected report."""
        current_row = self.reports_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a report to delete")
            return
        
        report_id = self.reports_table.item(current_row, 0).text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete report '{report_id}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                db_delete_report(report_id)
                self.load_analytics()
                QMessageBox.information(self, "Success", "Report deleted")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete failed: {e}")
    
    def show_admin_dialog(self):
        """Show admin settings dialog."""
        dialog = AdminDialog(self)
        dialog.exec_()
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About",
            f"<h2>{APP_TITLE}</h2>"
            f"<p>Version {APP_VERSION}</p>"
            f"<p>Process IRBn/Bn Reports | Extract Data | Export PDF</p>"
            f"<p>Built with PyQt5</p>"
        )


class AdminDialog(QDialog):
    """Admin settings dialog."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Admin Settings")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Password
        password_label = QLabel("Enter Admin Password:")
        layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        
        self.verify_btn = QPushButton("Verify")
        self.verify_btn.clicked.connect(self.verify_password)
        layout.addWidget(self.verify_btn)
        
        # Settings (initially hidden)
        self.settings_widget = QWidget()
        settings_layout = QVBoxLayout(self.settings_widget)
        
        # Webhook
        webhook_group = QGroupBox("Webhook Configuration")
        webhook_layout = QVBoxLayout()
        self.webhook_input = QLineEdit()
        self.webhook_input.setPlaceholderText("https://your-webhook.com/endpoint (optional)")
        webhook_layout.addWidget(self.webhook_input)
        webhook_group.setLayout(webhook_layout)
        settings_layout.addWidget(webhook_group)
        
        # AI default
        ai_group = QGroupBox("Default Settings")
        ai_layout = QVBoxLayout()
        self.ai_default_checkbox = QCheckBox("Enable AI Enhancement by default")
        self.ai_default_checkbox.setChecked(settings.AI_ENABLED)
        ai_layout.addWidget(self.ai_default_checkbox)
        
        self.auto_save_checkbox = QCheckBox("Auto-save after processing")
        self.auto_save_checkbox.setChecked(settings.AUTO_SAVE_ENABLED)
        ai_layout.addWidget(self.auto_save_checkbox)
        
        ai_group.setLayout(ai_layout)
        settings_layout.addWidget(ai_group)
        
        # Database info
        db_group = QGroupBox("Database")
        db_layout = QVBoxLayout()
        db_layout.addWidget(QLabel("Database: phq_reports.db (SQLite)"))
        db_layout.addWidget(QLabel("Location: Same folder as application"))
        db_group.setLayout(db_layout)
        settings_layout.addWidget(db_group)
        
        layout.addWidget(self.settings_widget)
        self.settings_widget.hide()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
    
    def verify_password(self):
        """Verify the admin password."""
        if self.password_input.text() == ADMIN_PASSWORD:
            self.settings_widget.show()
            self.password_input.setEnabled(False)
            self.verify_btn.setEnabled(False)
            self.verify_btn.setText("✓ Verified")
            
            # Add save button
            save_btn = QPushButton("Save Settings")
            save_btn.clicked.connect(self.save_settings)
            self.layout().insertWidget(6, save_btn)
        else:
            QMessageBox.warning(self, "Invalid Password", "Incorrect password")
    
    def save_settings(self):
        """Save admin settings."""
        settings.AI_ENABLED = self.ai_default_checkbox.isChecked()
        settings.AUTO_SAVE_ENABLED = self.auto_save_checkbox.isChecked()
        QMessageBox.information(self, "Success", "Settings saved!")
        self.close()


class TemplateDialog(QDialog):
    """Dialog for creating/editing templates."""
    
    def __init__(self, parent, template=None):
        super().__init__(parent)
        self.template = template
        self.setWindowTitle("Template Editor" if template else "New Template")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit()
        if template:
            self.name_input.setText(template.get("name", ""))
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_input = QLineEdit()
        if template:
            self.desc_input.setText(template.get("description", ""))
        desc_layout.addWidget(self.desc_input)
        layout.addLayout(desc_layout)
        
        # Content
        content_label = QLabel("Content:")
        layout.addWidget(content_label)
        
        self.content_input = QTextEdit()
        if template:
            self.content_input.setPlainText(template.get("content", ""))
        else:
            self.content_input.setPlaceholderText(
                "Name of IRBn/Bn: ...\n"
                "1. Reserves Deployed: ...\n"
                "..."
            )
        layout.addWidget(self.content_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def save(self):
        """Save the template."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a template name")
            return
        
        content = self.content_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Warning", "Please enter template content")
            return
        
        # For now, just close - in full implementation would save to file
        self.close()


def run_app():
    """Run the application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application icon
    icon_path = get_asset_path("Himachal_Pradesh_Police_Logo.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_app()