import tkinter as tk
from tkinter import ttk, messagebox
import threading
from main import TempFileFinder
import os
import logging
import gc
from queue import Queue
import time
from datetime import datetime
import sys

# Add logging initialization
logging.basicConfig(
    filename='temp_file_finder.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    matplotlib_available = True
except ImportError:
    matplotlib_available = False
    logging.warning("Matplotlib not available. Statistics charts will be disabled.")

# Import system tray module if available
try:
    from system_tray import get_system_tray
    SYSTEM_TRAY_AVAILABLE = True
except ImportError:
    SYSTEM_TRAY_AVAILABLE = False
    logging.warning("System tray module not available. System tray icon will be disabled.")

# Colors for clean and futuristic theme
class FuturisticTheme:
    # Main backgrounds
    DARK_BG = "#0F1624"      # Deep space blue background
    LIGHT_BG = "#1A2332"     # Lighter space blue for contrast
    
    # Accent colors
    ACCENT = "#64FFDA"       # Bright teal accent - main brand color
    ACCENT_HOVER = "#00E5FF" # Cyan for hover states
    ACCENT_ALT = "#4D69FF"   # Electric blue for secondary accents
    
    # Text colors
    TEXT = "#F2F5FF"         # Soft white text for better eye comfort
    TEXT_MUTED = "#B3C5EF"   # Soft blue-gray for secondary text
    
    # Status colors
    SUCCESS = "#00E676"      # Vibrant green for success messages
    WARNING = "#FFEA00"      # Bright yellow for warnings
    ERROR = "#FF5252"        # Coral red for errors
    
    # UI elements
    BORDER = "#2E3A50"       # Subtle border with blue undertones
    CARD_BG = "#141F35"      # Slightly lighter than main bg for cards
    GRADIENT_START = "#0F1624" # For gradient effects - matches DARK_BG
    GRADIENT_END = "#253555"   # Gradient end - royal blue tone

# Add a fallback implementation for TempFileFinder if it's not working
class FallbackTempFileFinder:
    def __init__(self):
        self.excluded_dirs = []
        self.scanning = False
        self.total_size = 0
    
    def reset_stats(self):
        self.total_size = 0
    
    def format_size(self, size_bytes):
        """Format file size in a human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def add_excluded_dir(self, directory):
        if directory not in self.excluded_dirs:
            self.excluded_dirs.append(directory)
    
    def remove_excluded_dir(self, directory):
        if directory in self.excluded_dirs:
            self.excluded_dirs.remove(directory)
    
    def get_system_temp_dirs(self):
        import tempfile
        return [tempfile.gettempdir()]
    
    def get_available_drives(self):
        return ["C:/"]
    
    def scan_for_temp_files(self, directory, callback=None):
        """Dummy scan implementation"""
        import random
        import time
        
        result = []
        for i in range(10):
            size = random.randint(1000, 10000000)
            self.total_size += size
            
            file_info = {
                'path': f"{directory}/dummy_file_{i}.tmp",
                'size': size,
                'size_formatted': self.format_size(size),
                'age': f"{random.randint(1, 30)} days",
                'age_days': random.randint(1, 30)
            }
            
            if callback:
                callback(file_info)
            
            time.sleep(0.1)  # Add small delay
            result.append(file_info)
            
        return result
    
    def get_stats_summary(self):
        """Return dummy stats"""
        return {
            'total_size': self.format_size(self.total_size),
            'file_stats': {
                'by_type': {
                    'temp': f"{self.total_size / 2:.1f} MB",
                    'log': f"{self.total_size / 4:.1f} MB",
                    'cache': f"{self.total_size / 4:.1f} MB"
                },
                'by_age': {
                    'recent': f"{self.total_size / 3:.1f} MB",
                    'week': f"{self.total_size / 3:.1f} MB",
                    'month': f"{self.total_size / 3:.1f} MB"
                },
                'by_size': {
                    'small': f"{self.total_size / 5:.1f} MB",
                    'medium': f"{self.total_size / 5:.1f} MB",
                    'large': f"{self.total_size * 3/5:.1f} MB"
                }
            }
        }
    
    def set_min_file_age(self, days):
        pass
    
    def get_file_info(self, file_path):
        """Return dummy file info"""
        import random
        size = random.randint(1000, 10000000)
        return {
            'path': file_path,
            'size': size,
            'size_formatted': self.format_size(size),
            'age': f"{random.randint(1, 30)} days",
            'age_days': random.randint(1, 30)
        }

class TempFileCleanerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CleanX - Advanced System Cleaner")
        # Make window smaller but still functional
        self.root.geometry("1000x650")
        self.root.minsize(800, 600)  # Set minimum window size
        self.root.configure(bg=FuturisticTheme.DARK_BG)
        
        # Add window icon - you would need to create this file
        try:
            self.root.iconbitmap("assets/cleaner_icon.ico")
        except:
            pass  # If icon file doesn't exist, just continue
        
        # Add drop shadow effect to window on Windows if possible
        if os.name == 'nt':
            try:
                self.root.attributes('-alpha', 0.95)  # Slight transparency for modern look
            except:
                pass

        # Configure row and column weights for proper resizing
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Apply futuristic theme
        self.apply_theme()
        
        # Add debug-level logging to console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logging.getLogger().addHandler(console_handler)
        
        # Initialize the scanner without fallback
        try:
            self.temp_finder = TempFileFinder()
            logging.info("TempFileFinder initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize TempFileFinder: {e}")
            messagebox.showerror("Error", "Failed to initialize scanner. Please check logs.")
            raise  # Re-raise the exception instead of using fallback
        
        self.temp_files = []
        # Cache for filtered results to improve performance
        self.filtered_cache = {}
        
        # Set debug mode to False for production
        self.debug_mode = False  # Changed from True to False
        
        self.setup_ui()
        
        # Setup debugging if enabled
        if self.debug_mode:
            self.setup_debug_logging()
        
        # Initialize system tray if available
        self.system_tray = None
        self.init_system_tray()
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def apply_theme(self):
        # Set the window icon and configure the root window
        self.root.configure(background=FuturisticTheme.DARK_BG)
        
        # Try to use a modern font if available
        preferred_fonts = ['Segoe UI', 'Roboto', 'SF Pro Display', 'Arial', 'Helvetica']
        available_font = None
        for font in preferred_fonts:
            try:
                tk.font.Font(family=font, size=10)  # Test if font is available
                available_font = font
                break
            except:
                continue
        
        if not available_font:
            available_font = 'TkDefaultFont'  # Fallback to default
    
        # Create a custom theme
        style = ttk.Style()
        style.theme_create("futuristic", parent="alt", settings={
            # Notebook (Tabs)
            "TNotebook": {"configure": {
                "background": FuturisticTheme.DARK_BG, 
                "tabmargins": [2, 5, 2, 0],
                "borderwidth": 0,
                "tabposition": 'n'
            }},
            "TNotebook.Tab": {
            "configure": {
                "background": FuturisticTheme.LIGHT_BG,
                "foreground": FuturisticTheme.TEXT,
                "padding": [15, 6],
                "font": (available_font, 10, 'bold'),
                "borderwidth": 0
            },
            "map": {
                "background": [("selected", FuturisticTheme.ACCENT)],
                "foreground": [("selected", FuturisticTheme.TEXT)],
                "expand": [("selected", [1, 1, 1, 0])]
            }
        },
        # Frames
        "TFrame": {"configure": {"background": FuturisticTheme.DARK_BG}},
        "TLabelframe": {
            "configure": {
                "background": FuturisticTheme.CARD_BG,
                "foreground": FuturisticTheme.TEXT,
                "borderwidth": 1,
                "relief": "solid",
                "bordercolor": FuturisticTheme.BORDER
            }
        },
        "TLabelframe.Label": {
            "configure": {
                "background": FuturisticTheme.CARD_BG,
                "foreground": FuturisticTheme.ACCENT,
                "font": (available_font, 10, 'bold')
            }
        },
        # Buttons
        "TButton": {
            "configure": {
                "background": FuturisticTheme.ACCENT,
                "foreground": FuturisticTheme.DARK_BG,  # Dark text on light button for contrast
                "padding": [12, 6],
                "font": (available_font, 9, 'bold'),
                "borderwidth": 0,
                "relief": "flat"
            },
            "map": {
                "background": [("active", FuturisticTheme.ACCENT_HOVER)],
                "foreground": [("active", FuturisticTheme.DARK_BG)],
                "relief": [("pressed", "flat")]
            }
        },
        # Labels
        "TLabel": {
            "configure": {
                "background": FuturisticTheme.DARK_BG,
                "foreground": FuturisticTheme.TEXT,
                "font": (available_font, 9)
            }
        },
        # Radio buttons
        "TRadiobutton": {
            "configure": {
                "background": FuturisticTheme.CARD_BG,
                "foreground": FuturisticTheme.TEXT,
                "font": (available_font, 9)
            },
            "map": {
                "indicatorcolor": [("selected", FuturisticTheme.ACCENT)]
            }
        },
        # Checkboxes
        "TCheckbutton": {
            "configure": {
                "background": FuturisticTheme.CARD_BG,
                "foreground": FuturisticTheme.TEXT,
                "font": (available_font, 9)
            },
            "map": {
                "indicatorcolor": [("selected", FuturisticTheme.ACCENT)]
            }
        },
        # Dropdown menus
        "TCombobox": {
            "configure": {
                "fieldbackground": FuturisticTheme.LIGHT_BG,
                "background": FuturisticTheme.ACCENT_ALT,
                "foreground": FuturisticTheme.TEXT,
                "selectbackground": FuturisticTheme.ACCENT,
                "selectforeground": FuturisticTheme.DARK_BG,
                "padding": 5,
                "arrowsize": 15
            }
        },
        # Text entry fields
        "TEntry": {
            "configure": {
                "fieldbackground": FuturisticTheme.LIGHT_BG,
                "foreground": FuturisticTheme.TEXT,
                "borderwidth": 1,
                "padding": 5
            }
        },
        # Tree views (lists)
        "Treeview": {
            "configure": {
                "background": FuturisticTheme.CARD_BG,
                "foreground": FuturisticTheme.TEXT,
                "rowheight": 28,  # Slightly taller rows
                "borderwidth": 0,
                "font": (available_font, 9),
                "fieldbackground": FuturisticTheme.CARD_BG
            },
            "map": {
                "background": [("selected", FuturisticTheme.ACCENT_ALT)],
                "foreground": [("selected", FuturisticTheme.TEXT)]
            }
        },
        # Tree view headers
        "Treeview.Heading": {
            "configure": {
                "background": FuturisticTheme.LIGHT_BG,
                "foreground": FuturisticTheme.ACCENT,
                "relief": "flat",
                "borderwidth": 0,
                "font": (available_font, 9, 'bold')
            }
        },
        # Scrollbars
        "Vertical.TScrollbar": {
            "configure": {
                "background": FuturisticTheme.CARD_BG,
                "troughcolor": FuturisticTheme.DARK_BG,
                "borderwidth": 0,
                "arrowcolor": FuturisticTheme.ACCENT
            },
            "map": {
                "background": [("active", FuturisticTheme.ACCENT_ALT)]
            }
        },
        "Horizontal.TScrollbar": {
            "configure": {
                "background": FuturisticTheme.CARD_BG,
                "troughcolor": FuturisticTheme.DARK_BG,
                "borderwidth": 0,
                "arrowcolor": FuturisticTheme.ACCENT
            },
            "map": {
                "background": [("active", FuturisticTheme.ACCENT_ALT)]
            }
        }
    })
    
    style.theme_use("futuristic")
    
    # Additional style configurations for specific widgets
    style.configure("Success.TButton", 
                    background=FuturisticTheme.SUCCESS, 
                    foreground=FuturisticTheme.DARK_BG)
    style.map("Success.TButton", 
              background=[("active", FuturisticTheme.SUCCESS)],
              foreground=[("active", FuturisticTheme.DARK_BG)])
    
    style.configure("Warning.TButton", 
                    background=FuturisticTheme.WARNING, 
                    foreground=FuturisticTheme.DARK_BG)
    style.map("Warning.TButton", 
              background=[("active", FuturisticTheme.WARNING)],
              foreground=[("active", FuturisticTheme.DARK_BG)])
    
    style.configure("Error.TButton", 
                    background=FuturisticTheme.ERROR, 
                    foreground=FuturisticTheme.DARK_BG)
    style.map("Error.TButton", 
              background=[("active", FuturisticTheme.ERROR)],
              foreground=[("active", FuturisticTheme.DARK_BG)])
    
    # Secondary button style with border instead of fill
    style.configure("Secondary.TButton", 
                    background=FuturisticTheme.DARK_BG,
                    foreground=FuturisticTheme.ACCENT,
                    borderwidth=1,
                    bordercolor=FuturisticTheme.ACCENT,
                    relief="solid")
    style.map("Secondary.TButton",
              background=[("active", FuturisticTheme.ACCENT_ALT)],
              foreground=[("active", FuturisticTheme.TEXT)])
    
    # Card style for frame sections
    style.configure("Card.TFrame", 
                    background=FuturisticTheme.CARD_BG,
                    borderwidth=1,
                    relief="solid",
                    bordercolor=FuturisticTheme.BORDER)
    
    # Header label style
    style.configure("Header.TLabel",
                    font=(available_font, 12, 'bold'),
                    foreground=FuturisticTheme.ACCENT)
    
    # Subheader label style
    style.configure("Subheader.TLabel",
                    font=(available_font, 10, 'bold'),
                    foreground=FuturisticTheme.TEXT)
    
    # Status label styles
    style.configure("Success.TLabel", foreground=FuturisticTheme.SUCCESS)
    style.configure("Warning.TLabel", foreground=FuturisticTheme.WARNING)
    style.configure("Error.TLabel", foreground=FuturisticTheme.ERROR)
    
    # Configure listbox and other tk widgets
    self.root.option_add("*TCombobox*Listbox.background", FuturisticTheme.CARD_BG)
    self.root.option_add("*TCombobox*Listbox.foreground", FuturisticTheme.TEXT)
    self.root.option_add("*TCombobox*Listbox.selectBackground", FuturisticTheme.ACCENT)
    self.root.option_add("*TCombobox*Listbox.selectForeground", FuturisticTheme.DARK_BG)
    
    # Configure the main window
    self.root.configure(bg=FuturisticTheme.DARK_BG)
    
    # Add some padding to all widgets for better spacing
    for widget in ['TButton', 'TEntry', 'TLabel', 'TCheckbutton', 'TRadiobutton']:
        style.configure(widget, padding=3)
        
    def setup_ui(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Main scan tab
        self.scan_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(self.scan_frame, text="File Scanner")

        # Duplicates tab
        self.duplicates_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(self.duplicates_frame, text="Duplicates")

        # Statistics tab
        self.stats_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(self.stats_frame, text="Statistics")

        # Settings tab
        self.settings_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(self.settings_frame, text="Settings")

        try:
            # Setup tabs one by one
            logging.info("Setting up scan tab...")
            self.setup_scan_tab()
            
            logging.info("Setting up duplicates tab...")
            self.setup_duplicates_tab()
            
            logging.info("Setting up stats tab...")
            self.setup_stats_tab()
            
            logging.info("Setting up settings tab...")
            self.setup_settings_tab()
        except Exception as e:
            logging.error(f"Error setting up tabs: {e}")
            messagebox.showerror("Setup Error", f"Error setting up tabs: {e}")
        
        # Add status bar at the bottom
        self.status_bar = ttk.Frame(self.root, relief=tk.SUNKEN, padding=(2, 0))
        self.status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.status_text = tk.StringVar(value="Ready")
        ttk.Label(self.status_bar, textvariable=self.status_text, 
                  font=('Segoe UI', 8), foreground=FuturisticTheme.TEXT_MUTED).pack(side=tk.LEFT, padx=5)
        
        # Version and credits
        ttk.Label(self.status_bar, text="v1.0.0  |  Ultra Temp Cleaner", 
                  font=('Segoe UI', 8), foreground=FuturisticTheme.TEXT_MUTED).pack(side=tk.RIGHT, padx=5)
        
        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # Create menu bar
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        # Add Help menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about_dialog)

        # Add a Debug menu in debug mode
        if self.debug_mode:
            debug_menu = tk.Menu(menu_bar, tearoff=0)
            menu_bar.add_cascade(label="Debug", menu=debug_menu)
            debug_menu.add_command(label="Test UI Elements", command=self.test_ui_elements)
            debug_menu.add_command(label="Test Radio Buttons", command=self.test_radio_buttons)
            debug_menu.add_command(label="Manual Radio Button Test", command=self.manual_test_radio)
            debug_menu.add_command(label="Test Buttons", command=self.test_buttons)
            debug_menu.add_command(label="Run Simple Test Scan", command=self.simple_test_scan)
            debug_menu.add_command(label="Clear Cache", command=self.clear_cache)
            debug_menu.add_command(label="Save Bug Report", command=self.save_bug_report)

    def setup_scan_tab(self):
        # Create a more compact layout
        top_frame = ttk.Frame(self.scan_frame)
        top_frame.pack(fill=tk.X, expand=False, pady=(0, 5))
        
        # Left control panel
        control_panel = ttk.LabelFrame(top_frame, text="Scan Controls", padding="5")
        control_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Scan location with more compact layout
        location_frame = ttk.Frame(control_panel)
        location_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(location_frame, text="Location:", width=8).pack(side=tk.LEFT)
        
        # Create even more direct buttons with separate scan methods for each
        self.scan_location_var = tk.StringVar(value="temp")
        
        # Create a frame for the location buttons
        button_group = ttk.Frame(location_frame)
        button_group.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Create styled buttons for direct scanning
        self.temp_button = ttk.Button(
            button_group, 
            text="Temp Dirs", 
            command=self.scan_temp_dirs,  # Direct command to scan temp directories
            width=12,
            style="Active.TButton"  # Start with this active
        )
        self.temp_button.pack(side=tk.LEFT, padx=2)
        
        self.all_button = ttk.Button(
            button_group, 
            text="All Drives", 
            command=self.scan_all_drives,  # Direct command to scan all drives
            width=12,
            style="Inactive.TButton"
        )
        self.all_button.pack(side=tk.LEFT, padx=2)
        
        # Buttons in their own row for compactness
        button_frame = ttk.Frame(control_panel)
        button_frame.pack(fill=tk.X, pady=2)
        
        # Create scan button with direct command binding
        self.scan_button = ttk.Button(button_frame, text="⚡ Scan")
        self.scan_button.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.scan_button.config(command=self.start_scan)
        
        # Create stop button with direct command binding
        self.stop_button = ttk.Button(button_frame, text="⏹ Stop", 
                                    style="Error.TButton", state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.stop_button.config(command=self.stop_scan)
        
        # Right filter panel
        filter_panel = ttk.LabelFrame(top_frame, text="Filters", padding="5")
        filter_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # More compact filter layout in a grid
        filter_grid = ttk.Frame(filter_panel)
        filter_grid.pack(fill=tk.BOTH, expand=True)
        
        # File type filter (row 0)
        ttk.Label(filter_grid, text="Type:").grid(row=0, column=0, padx=2, pady=2, sticky=tk.W)
        self.file_type_var = tk.StringVar(value="all")
        ttk.Combobox(filter_grid, textvariable=self.file_type_var, width=8,
                    values=['all', 'temp', 'cache', 'logs']).grid(row=0, column=1, padx=2, pady=2)

        # Age filter
        ttk.Label(filter_grid, text="Age:").grid(row=0, column=2, padx=2, pady=2, sticky=tk.W)
        self.age_filter_var = tk.StringVar(value="all")
        ttk.Combobox(filter_grid, textvariable=self.age_filter_var, width=8,
                    values=['all', 'recent', 'week', 'month', 'old']).grid(row=0, column=3, padx=2, pady=2)
        
        # Size filter (row 1)
        ttk.Label(filter_grid, text="Size:").grid(row=1, column=0, padx=2, pady=2, sticky=tk.W)
        self.size_filter_var = tk.StringVar(value="all")
        ttk.Combobox(filter_grid, textvariable=self.size_filter_var, width=8,
                    values=['all', 'small', 'medium', 'large', 'huge']).grid(row=1, column=1, padx=2, pady=2)

        # Apply filter button - this was missing!
        self.apply_filter_btn = ttk.Button(filter_grid, text="Apply")
        self.apply_filter_btn.grid(row=1, column=2, columnspan=2, padx=2, pady=2, sticky=(tk.W, tk.E))
        self.apply_filter_btn.config(command=self.apply_filters)
        
        # Progress indicator beneath the controls
        progress_frame = ttk.Frame(self.scan_frame, padding=(0, 5))
        progress_frame.pack(fill=tk.X, expand=False)
        
        self.progress_var = tk.StringVar(value="Ready to scan")
        ttk.Label(progress_frame, textvariable=self.progress_var, 
                 foreground=FuturisticTheme.TEXT_MUTED, width=40).pack(side=tk.LEFT)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode="indeterminate", length=150)
        self.progress_bar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.total_size_var = tk.StringVar(value="Total: 0 B")
        ttk.Label(progress_frame, textvariable=self.total_size_var,
                 foreground=FuturisticTheme.SUCCESS, width=15).pack(side=tk.RIGHT)
        
        # Results section
        results_frame = ttk.LabelFrame(self.scan_frame, text="Scan Results", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Toolbar above the tree view
        toolbar = ttk.Frame(results_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # Search capability
        ttk.Label(toolbar, text="Search:").pack(side=tk.LEFT, padx=2)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.on_search_change)
        ttk.Entry(toolbar, textvariable=self.search_var, width=20).pack(side=tk.LEFT, padx=2)
        
        # Action buttons on right
        ttk.Button(toolbar, text="🔍 Select Matching", 
                   command=self.select_matching).pack(side=tk.RIGHT, padx=2)
        ttk.Button(toolbar, text="✓ Select All", 
                   command=self.select_all).pack(side=tk.RIGHT, padx=2)
        ttk.Button(toolbar, text="✗ Deselect All", 
                   command=self.deselect_all).pack(side=tk.RIGHT, padx=2)
        
        # Tree with results
        tree_container = ttk.Frame(results_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        # Configure columns more efficiently
        self.tree = ttk.Treeview(tree_container, columns=('size', 'age', 'path'), 
                                show='headings', selectmode='extended')
        self.tree.heading('size', text='Size', command=lambda: self.treeview_sort_column('size', False))
        self.tree.heading('age', text='Age', command=lambda: self.treeview_sort_column('age', False))
        self.tree.heading('path', text='Path', command=lambda: self.treeview_sort_column('path', False))
        
        # Optimize column widths
        self.tree.column('size', width=80, minwidth=60)
        self.tree.column('age', width=80, minwidth=60)
        self.tree.column('path', width=400, minwidth=200)
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        x_scrollbar = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        
        # Pack tree and scrollbars
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X, before=tree_container)
        
        self.tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)

        # Action buttons at the bottom
        action_frame = ttk.Frame(self.scan_frame)
        action_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(action_frame, text="🗑️ Delete Selected", 
                  command=self.delete_selected, style="Error.TButton").pack(side=tk.LEFT)
        
        # Add quick stats
        self.quick_stats_var = tk.StringVar(value="0 items selected (0 B)")
        ttk.Label(action_frame, textvariable=self.quick_stats_var,
                 foreground=FuturisticTheme.TEXT_MUTED).pack(side=tk.RIGHT)
        
        # Bind selection event to update stats
        self.tree.bind("<<TreeviewSelect>>", self.update_selection_stats)
        
        # Add the test button for debugging if needed
        if self.debug_mode:
            debug_frame = ttk.Frame(self.scan_frame)
            debug_frame.pack(fill=tk.X, pady=5)
            
            debug_btn = ttk.Button(debug_frame, text="Debug", 
                                  command=lambda: self.debug_button_click("Debug"))
            debug_btn.pack(side=tk.LEFT, padx=5)
            
            # Add a direct test for radio buttons
            radio_test_btn = ttk.Button(debug_frame, text="Test Radio Buttons", 
                                      command=self.test_radio_buttons)
            radio_test_btn.pack(side=tk.LEFT, padx=5)

    def setup_duplicates_tab(self):
        """Setup the duplicates tab for finding and managing duplicate files"""
        # Top control panel
        control_frame = ttk.Frame(self.duplicates_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        # Scan button
        scan_frame = ttk.LabelFrame(control_frame, text="Duplicate Finder", padding="5")
        scan_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Label(scan_frame, text="Find duplicate files based on content").pack(side=tk.LEFT, padx=5)
        
        self.find_dupes_button = ttk.Button(
            scan_frame, 
            text="🔍 Find Duplicates",
            command=self.find_duplicate_files
        )
        self.find_dupes_button.pack(side=tk.RIGHT, padx=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(control_frame, text="Options", padding="5")
        options_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # Options for duplicate scanning
        self.exclude_system_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Exclude system directories",
            variable=self.exclude_system_var
        ).pack(anchor=tk.W, padx=5)
        
        self.skip_small_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Skip small files (<10 KB)",
            variable=self.skip_small_var
        ).pack(anchor=tk.W, padx=5)
        
        # Progress indicator
        progress_frame = ttk.Frame(self.duplicates_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.dupe_progress_var = tk.StringVar(value="Ready to scan for duplicates")
        ttk.Label(progress_frame, textvariable=self.dupe_progress_var, 
                foreground=FuturisticTheme.TEXT_MUTED, width=40).pack(side=tk.LEFT)
        
        self.dupe_progress_bar = ttk.Progressbar(progress_frame, mode="indeterminate", length=150)
        self.dupe_progress_bar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.dupe_total_size_var = tk.StringVar(value="Duplicate size: 0 B")
        ttk.Label(progress_frame, textvariable=self.dupe_total_size_var,
                foreground=FuturisticTheme.SUCCESS, width=20).pack(side=tk.RIGHT)
        
        # Results pane with treeview
        results_frame = ttk.LabelFrame(self.duplicates_frame, text="Duplicate Files", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create duplicate groups tree
        tree_container = ttk.Frame(results_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        # Two-level tree with groups
        self.dupes_tree = ttk.Treeview(
            tree_container,
            columns=('size', 'count', 'path'),
            show='tree headings',
            selectmode='extended'
        )
        
        # Configure columns
        self.dupes_tree.heading('size', text='Size', command=lambda: self.treeview_sort_column(self.dupes_tree, 'size', False))
        self.dupes_tree.heading('count', text='Count', command=lambda: self.treeview_sort_column(self.dupes_tree, 'count', False))
        self.dupes_tree.heading('path', text='Path', command=lambda: self.treeview_sort_column(self.dupes_tree, 'path', False))
        
        self.dupes_tree.column('size', width=100, minwidth=80)
        self.dupes_tree.column('count', width=60, minwidth=40)
        self.dupes_tree.column('path', width=400, minwidth=200)
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.dupes_tree.yview)
        x_scrollbar = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.dupes_tree.xview)
        
        self.dupes_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X, before=tree_container)
        
        self.dupes_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Action buttons
        action_frame = ttk.Frame(self.duplicates_frame)
        action_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            action_frame,
            text="Delete Selected Duplicates",
            command=self.delete_selected_duplicates,
            style="Error.TButton"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            action_frame,
            text="Select All Duplicates",
            command=self.select_all_duplicates
        ).pack(side=tk.LEFT, padx=5)
        
        # Quick stats
        self.dupes_stats_var = tk.StringVar(value="0 items selected (0 B)")
        ttk.Label(action_frame, textvariable=self.dupes_stats_var,
                foreground=FuturisticTheme.TEXT_MUTED).pack(side=tk.RIGHT, padx=5)
        
        # Bind events
        self.dupes_tree.bind("<<TreeviewSelect>>", self.update_duplicate_selection_stats)
        self.dupes_tree.bind("<Double-1>", self.on_duplicate_double_click)
    
    def find_duplicate_files(self):
        """Find duplicate files in the scanned results"""
        if not hasattr(self, 'temp_files') or not self.temp_files:
            messagebox.showwarning("No Files", "No files have been scanned yet. Please run a scan first.")
            return
        
        # Update UI
        self.find_dupes_button.configure(state='disabled')
        self.dupe_progress_var.set("Finding duplicate files...")
        self.dupe_progress_bar.start(10)
        
        # Clear existing results
        for item in self.dupes_tree.get_children():
            self.dupes_tree.delete(item)
        
        # Apply filters
        filtered_files = self.temp_files.copy()
        
        # Filter out system directories if selected
        if self.exclude_system_var.get():
            system_dirs = [
                os.environ.get('WINDIR', 'C:\\Windows').lower(),
                os.environ.get('SYSTEMROOT', 'C:\\Windows').lower(),
                'c:\\program files',
                'c:\\program files (x86)'
            ]
            filtered_files = [f for f in filtered_files if not any(
                f['path'].lower().startswith(sdir) for sdir in system_dirs
            )]
        
        # Filter out small files if selected
        if self.skip_small_var.get():
            filtered_files = [f for f in filtered_files if f['size'] >= 10 * 1024]  # 10 KB
        
        # Start duplicate finding thread
        threading.Thread(
            target=self._find_duplicates_thread,
            args=(filtered_files,),
            daemon=True
        ).start()
    
    def _find_duplicates_thread(self, files):
        """Background thread for finding duplicates"""
        try:
            # Update progress
            self.root.after(0, lambda: self.dupe_progress_var.set(f"Processing {len(files)} files..."))
            
            # Find duplicates
            duplicate_results = self.temp_finder.find_duplicate_files(files)
            
            # Update UI with results
            self.root.after(0, lambda: self._display_duplicate_results(duplicate_results))
            
        except Exception as e:
            logging.error(f"Error finding duplicates: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error finding duplicates: {str(e)}"))
        finally:
            # Reset UI
            self.root.after(0, lambda: self.find_dupes_button.configure(state='normal'))
            self.root.after(0, lambda: self.dupe_progress_bar.stop())
    
    def _display_duplicate_results(self, results):
        """Display duplicate file results in the tree view"""
        self.dupe_progress_var.set("Processing results...")
        
        # Update total size
        total_duplicates = results.get('total_duplicates', 0)
        total_size = results.get('total_size_formatted', '0 B')
        self.dupe_total_size_var.set(f"Duplicates: {total_size}")
        
        # Get groups
        groups = results.get('groups', [])
        
        if not groups:
            self.dupe_progress_var.set("No duplicate files found")
            return
        
        # Add groups to tree
        for i, group in enumerate(groups):
            # Create group node
            group_id = f"group_{i}"
            original = group['original']
            count = group['count']
            size = group['size_formatted']
            
            # Display truncated original path
            path = original['path']
            if len(path) > 60:
                display_path = "..." + path[-57:]
            else:
                display_path = path
            
            # Insert group
            self.dupes_tree.insert(
                '', 'end', group_id,
                values=(size, count, display_path),
                open=False  # Collapsed by default
            )
            
            # Add original file as first child
            self.dupes_tree.insert(
                group_id, 'end',
                values=("(original)", "", original['path']),
                tags=('original',)
            )
            
            # Add duplicate files
            for dupe in group['duplicates']:
                self.dupes_tree.insert(
                    group_id, 'end',
                    values=(dupe['size_formatted'], "", dupe['path']),
                    tags=('duplicate',)
                )
        
        # Configure tag styles
        self.dupes_tree.tag_configure('original', foreground=FuturisticTheme.SUCCESS)
        self.dupes_tree.tag_configure('duplicate', foreground=FuturisticTheme.WARNING)
        
        # Update status
        self.dupe_progress_var.set(f"Found {total_duplicates} duplicate files in {len(groups)} groups")
    
    def update_duplicate_selection_stats(self, event=None):
        """Update stats based on selected duplicate files"""
        selection = self.dupes_tree.selection()
        if not selection:
            self.dupes_stats_var.set("0 items selected (0 B)")
            return
        
        # Count only duplicate files, not group headers or originals
        duplicate_count = 0
        total_size = 0
        
        for item in selection:
            values = self.dupes_tree.item(item, 'values')
            tags = self.dupes_tree.item(item, 'tags')
            
            # Skip group headers and originals
            if not values or not values[0] or values[0] == "(original)" or 'original' in tags:
                continue
            
            duplicate_count += 1
            
            # Parse size if available
            if values[0] and values[0] not in ["(original)", ""]:
                size_str = values[0]
                try:
                    parts = size_str.split()
                    if len(parts) == 2:
                        value, unit = float(parts[0]), parts[1]
                        multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
                        total_size += value * multipliers.get(unit, 0)
                except:
                    pass
        
        # Format total size
        formatted_size = self.temp_finder.format_size(total_size)
        self.dupes_stats_var.set(f"{duplicate_count} duplicates selected ({formatted_size})")
    
    def select_all_duplicates(self):
        """Select all duplicate files but not originals"""
        # First deselect everything
        self.dupes_tree.selection_remove(self.dupes_tree.selection())
        
        # Select all items with duplicate tag
        for group_id in self.dupes_tree.get_children():
            for item_id in self.dupes_tree.get_children(group_id):
                tags = self.dupes_tree.item(item_id, 'tags')
                if 'duplicate' in tags:
                    self.dupes_tree.selection_add(item_id)
        
        # Update stats
        self.update_duplicate_selection_stats()
    
    def delete_selected_duplicates(self):
        """Delete selected duplicate files"""
        selection = self.dupes_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "No duplicate files selected for deletion.")
            return
        
        # Filter out group headers and original files
        duplicate_items = []
        for item in selection:
            tags = self.dupes_tree.item(item, 'tags')
            if 'duplicate' in tags:
                duplicate_items.append(item)
        
        if not duplicate_items:
            messagebox.showwarning("No Duplicates", "No duplicate files selected. Only duplicate files can be deleted (not originals).")
            return
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {len(duplicate_items)} duplicate files?"):
            return
        
        # Delete the files
        deleted_count = 0
        total_size = 0
        
        for item in duplicate_items:
            values = self.dupes_tree.item(item, 'values')
            if values and len(values) >= 3:
                file_path = values[2]
                
                # Get size before deletion
                if values[0]:
                    try:
                        parts = values[0].split()
                        if len(parts) == 2:
                            value, unit = float(parts[0]), parts[1]
                            multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
                            size = value * multipliers.get(unit, 0)
                        else:
                            size = 0
                    except:
                        size = 0
                else:
                    size = 0
                
                # Delete the file
                if self.temp_finder.delete_file(file_path):
                    # Remove from tree view
                    self.dupes_tree.delete(item)
                    deleted_count += 1
                    total_size += size
        
        # Show result
        if deleted_count > 0:
            formatted_size = self.temp_finder.format_size(total_size)
            messagebox.showinfo("Deletion Complete", f"Successfully deleted {deleted_count} duplicate files ({formatted_size}).")
            
            # Update stats
            self.dupe_total_size_var.set(f"Duplicates: {self.temp_finder.format_size(self.temp_finder.duplicate_size - total_size)}")
        else:
            messagebox.showwarning("Deletion Failed", "No files were deleted.")
    
    def on_duplicate_double_click(self, event):
        """Handle double click on a duplicate file (opens containing folder)"""
        item = self.dupes_tree.identify('item', event.x, event.y)
        if not item:
            return
        
        values = self.dupes_tree.item(item, 'values')
        if values and len(values) >= 3 and values[2]:
            file_path = values[2]
            self.open_containing_folder(file_path)
    
    def open_containing_folder(self, file_path):
        """Open the folder containing the specified file"""
        try:
            folder_path = os.path.dirname(file_path)
            if os.path.exists(folder_path):
                if os.name == 'nt':  # Windows
                    os.startfile(folder_path)
                elif os.name == 'posix':  # macOS or Linux
                    import subprocess
                    if sys.platform == 'darwin':  # macOS
                        subprocess.Popen(['open', folder_path])
                    else:  # Linux
                        subprocess.Popen(['xdg-open', folder_path])
        except Exception as e:
            logging.error(f"Error opening folder {folder_path}: {e}")
            messagebox.showerror("Error", f"Could not open folder: {str(e)}")
            
    def show_duplicates(self, duplicate_results):
        """Show duplicate results in the duplicates tab (called from system tray)"""
        # Switch to duplicates tab
        self.notebook.select(1)  # Index of duplicates tab
        
        # Display the results
        self._display_duplicate_results(duplicate_results)

    def setup_stats_tab(self):
        # Create a dashboard-like header
        header_frame = ttk.Frame(self.stats_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header_frame, text="Storage Dashboard", 
                 font=('Segoe UI', 14, 'bold'), 
                 foreground=FuturisticTheme.ACCENT).pack(side=tk.LEFT, padx=5)
        
        # Display total in a more prominent way
        self.total_stats_var = tk.StringVar(value="Total: 0 B")
        ttk.Label(header_frame, textvariable=self.total_stats_var, 
                 font=('Segoe UI', 14, 'bold'),
                 foreground=FuturisticTheme.SUCCESS).pack(side=tk.RIGHT, padx=5)
        
        # Divider
        ttk.Separator(self.stats_frame, orient='horizontal').pack(fill=tk.X, pady=5)
        
        # More compact two-panel layout
        panel_frame = ttk.Frame(self.stats_frame)
        panel_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Statistics and breakdown
        left_panel = ttk.LabelFrame(panel_frame, text="Data Analysis", padding=5)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Better organized stats view with headers
        stats_notebook = ttk.Notebook(left_panel)
        stats_notebook.pack(fill=tk.BOTH, expand=True)
        
        # By type tab
        type_frame = ttk.Frame(stats_notebook)
        stats_notebook.add(type_frame, text="By Type")
        self.type_tree = self.create_stats_tree(type_frame)
        
        # By age tab
        age_frame = ttk.Frame(stats_notebook)
        stats_notebook.add(age_frame, text="By Age")
        self.age_tree = self.create_stats_tree(age_frame)
        
        # By size tab
        size_frame = ttk.Frame(stats_notebook)
        stats_notebook.add(size_frame, text="By Size")
        self.size_tree = self.create_stats_tree(size_frame)
        
        # Right panel - Visualization
        right_panel = ttk.LabelFrame(panel_frame, text="Visual Analysis", padding=5)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Chart selector with more modern toggle buttons
        chart_selector = ttk.Frame(right_panel)
        chart_selector.pack(fill=tk.X, pady=5)
        
        self.chart_type_var = tk.StringVar(value="type")
        
        # Create toggle-like radio buttons in a button bar
        for value, text, tooltip in [
            ("type", "Types", "File distribution by extension type"),
            ("age", "Age", "File distribution by age categories"),
            ("size", "Size", "File distribution by size categories")
        ]:
            rb = ttk.Radiobutton(chart_selector, text=text, value=value, 
                               variable=self.chart_type_var, command=self.update_chart)
            rb.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
            self.create_tooltip(rb, tooltip)
        
        # Chart frame with border
        chart_frame = ttk.Frame(right_panel, style="Chart.TFrame")
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        if matplotlib_available:
            self.fig = Figure(figsize=(5, 4), facecolor=FuturisticTheme.LIGHT_BG)
            self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Add an export button for the chart
            export_frame = ttk.Frame(right_panel)
            export_frame.pack(fill=tk.X)
            ttk.Button(export_frame, text="Export Chart", 
                      command=self.export_chart).pack(side=tk.RIGHT)
        else:
            ttk.Label(chart_frame, 
                     text="Charts unavailable - matplotlib not installed",
                     foreground=FuturisticTheme.WARNING).pack(pady=20)

    def create_stats_tree(self, parent):
        """Helper to create consistent stats trees"""
        tree = ttk.Treeview(parent, columns=('category', 'value', 'percent'), 
                            show='headings', height=12)
        tree.heading('category', text='Category')
        tree.heading('value', text='Size')
        tree.heading('percent', text='%')
        tree.column('category', width=150)
        tree.column('value', width=100)
        tree.column('percent', width=50)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        return tree

    def export_chart(self):
        """Export the current chart as an image"""
        if not matplotlib_available:
            return
        
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")]
            )
            if filename:
                self.fig.savefig(filename, dpi=150, bbox_inches='tight')
                self.status_text.set(f"Chart exported to {filename}")
        except Exception as e:
            logging.error(f"Error exporting chart: {e}")
            messagebox.showerror("Export Error", f"Could not export chart: {e}")

    def create_tooltip(self, widget, text):
        """Create a simple tooltip for a widget"""
        tooltip_label = None
        
        def enter(event):
            nonlocal tooltip_label
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            tooltip_label = tk.Toplevel(widget)
            tooltip_label.wm_overrideredirect(True)
            tooltip_label.wm_geometry(f"+{x}+{y}")
            
            label = ttk.Label(tooltip_label, text=text, background=FuturisticTheme.ACCENT,
                             foreground=FuturisticTheme.TEXT, padding=5)
            label.pack()
            
        def leave(event):
            nonlocal tooltip_label
            if tooltip_label:
                tooltip_label.destroy()
                tooltip_label = None
        
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def setup_settings_tab(self):
        # Minimum file age setting
        age_frame = ttk.LabelFrame(self.settings_frame, text="Minimum File Age", padding="5")
        age_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)

        self.min_age_var = tk.IntVar(value=0)
        ttk.Label(age_frame, text="Days:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(age_frame, textvariable=self.min_age_var, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Button(age_frame, text="Apply", 
                   command=lambda: self.temp_finder.set_min_file_age(self.min_age_var.get())
                   ).pack(side=tk.LEFT, padx=5)

        # Excluded directories
        exclude_frame = ttk.LabelFrame(self.settings_frame, text="Excluded Directories", 
                                     padding="5")
        exclude_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)

        self.excluded_dirs_list = tk.Listbox(exclude_frame, height=5)
        self.excluded_dirs_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(exclude_frame)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Button(btn_frame, text="Add", command=self.add_excluded_dir).pack(pady=2)
        ttk.Button(btn_frame, text="Remove", command=self.remove_excluded_dir).pack(pady=2)

        # Initialize excluded directories list from TempFileFinder
        for excluded_dir in self.temp_finder.excluded_dirs:
            self.excluded_dirs_list.insert(tk.END, excluded_dir)

        # Add a dark mode toggle
        dark_mode_frame = ttk.LabelFrame(self.settings_frame, text="Appearance", padding="5")
        dark_mode_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)

        self.dark_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dark_mode_frame, text="Enable Dark Mode", 
                       variable=self.dark_mode_var, command=self.toggle_dark_mode).pack(padx=5, anchor=tk.W)

        # System tray settings
        if SYSTEM_TRAY_AVAILABLE:
            tray_frame = ttk.LabelFrame(self.settings_frame, text="System Tray", padding="5")
            tray_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
            
            self.minimize_to_tray_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                tray_frame, 
                text="Minimize to system tray when closed",
                variable=self.minimize_to_tray_var
            ).pack(padx=5, anchor=tk.W)
            
            self.start_in_tray_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(
                tray_frame, 
                text="Start minimized to system tray",
                variable=self.start_in_tray_var
            ).pack(padx=5, anchor=tk.W)
            
            ttk.Button(
                tray_frame,
                text="Minimize to Tray Now",
                command=self.hide
            ).pack(padx=5, pady=5, anchor=tk.W)

    def toggle_dark_mode(self):
        if self.dark_mode_var.get():
            self.apply_theme()  # Apply dark theme
        else:
            self.apply_light_theme()  # Apply light theme

    def apply_light_theme(self):
        # Create a light theme
        style = ttk.Style()
        style.theme_create("light", parent="alt", settings={
            "TNotebook": {"configure": {"background": "#FFFFFF", "tabmargins": [2, 5, 2, 0]}},
                "TNotebook.Tab": {
                "configure": {
                    "background": "#F0F0F0",
                    "foreground": "#000000",
                    "padding": [10, 4],
                    "font": ('Segoe UI', 10, 'bold')
                },
                "map": {
                    "background": [("selected", "#D0D0D0")],
                    "foreground": [("selected", "#000000")],
                    "expand": [("selected", [1, 1, 1, 0])]
                }
            },
            "TFrame": {"configure": {"background": "#FFFFFF"}},
            "TLabelframe": {
                "configure": {
                    "background": "#F0F0F0",
                    "foreground": "#000000",
                    "borderwidth": 1,
                    "relief": "groove"
                }
            },
            "TLabelframe.Label": {
                "configure": {
                    "background": "#F0F0F0",
                    "foreground": "#000000",
                    "font": ('Segoe UI', 10, 'bold')
                }
            },
            "TButton": {
                "configure": {
                    "background": "#D0D0D0",
                    "foreground": "#000000",
                    "padding": [10, 5],
                    "font": ('Segoe UI', 9, 'bold')
                },
                "map": {
                    "background": [("active", "#C0C0C0")],
                    "foreground": [("active", "#000000")]
                }
            },
            "TLabel": {
                "configure": {
                    "background": "#FFFFFF",
                    "foreground": "#000000",
                    "font": ('Segoe UI', 9)
                }
            },
            "TRadiobutton": {
                "configure": {
                    "background": "#F0F0F0",
                    "foreground": "#000000",
                    "font": ('Segoe UI', 9)
                }
            },
            "TCheckbutton": {
                "configure": {
                    "background": "#F0F0F0",
                    "foreground": "#000000",
                    "font": ('Segoe UI', 9)
                }
            },
            "TCombobox": {
                "configure": {
                    "fieldbackground": "#FFFFFF",
                    "background": "#D0D0D0",
                    "foreground": "#000000",
                    "selectbackground": "#D0D0D0",
                    "selectforeground": "#000000"
                }
            },
            "TEntry": {
                "configure": {
                    "fieldbackground": "#FFFFFF",
                    "foreground": "#000000",
                    "borderwidth": 1
                }
            },
            "Treeview": {
                "configure": {
                    "background": "#FFFFFF",
                    "foreground": "#000000",
                    "rowheight": 25,
                    "borderwidth": 0,
                    "font": ('Segoe UI', 9)
                },
                "map": {
                    "background": [("selected", "#D0D0D0")],
                    "foreground": [("selected", "#000000")]
                }
            },
            "Treeview.Heading": {
                "configure": {
                    "background": "#D0D0D0",
                    "foreground": "#000000",
                    "relief": "flat",
                    "borderwidth": 0,
                    "font": ('Segoe UI', 9, 'bold')
                }
            }
        })
        
        style.theme_use("light")

    def ensure_ui_response(self):
        """Force UI to process pending events and ensure responsiveness"""
        try:
            self.root.update_idletasks()
            self.root.update()
        except Exception as e:
            logging.error(f"Error updating UI: {e}")

    def start_scan(self):
        """Start scanning based on current location selection"""
        logging.info("Start scan button clicked")
        
        # Get current location directly from the variable
        location = self.scan_location_var.get()
        logging.info(f"Starting scan with location: {location}")
        
        # Call the appropriate scanning method
        self.do_scan(location)

    def update_progress(self, file_info):
        self.root.after(0, lambda: self._update_progress_ui(file_info))

    def _update_progress_ui(self, file_info):
        self.progress_var.set(f"Scanning: {os.path.basename(file_info['path'])}")
        self.total_size_var.set(f"Total: {self.temp_finder.format_size(self.temp_finder.total_size)}")
        
        if self.matches_filter(file_info, 
                             self.file_type_var.get(),
                             self.age_filter_var.get(),
                             self.size_filter_var.get()):
            self.tree.insert('', 'end', values=(
                file_info['size_formatted'],
                file_info['age'],
                file_info['path']
            ))

    def stop_scan(self):
        self.temp_finder.scanning = False
        self.progress_var.set("Scan stopped.")
        self.progress_bar.stop()
        self.scan_button.configure(state='normal')
        self.stop_button.configure(state='disabled')

    def finish_scan(self):
        self.progress_var.set("Scan complete.")
        self.progress_bar.stop()
        self.scan_button.configure(state='normal')
        self.stop_button.configure(state='disabled')
        self.update_stats()

    def delete_selected(self):
        """Delete selected files with improved handling"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "No files selected for deletion.")
            return

        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete the selected files?"):
            # First check if any protected files are selected
            protected_files = []
            for item in selected_items:
                values = self.tree.item(item, 'values')
                if values and len(values) >= 3:
                    file_path = values[2]
                    if self._is_protected_path(file_path):
                        protected_files.append(file_path)
            
            # If we have protected files, offer to restart as admin directly
            if protected_files and os.name == 'nt':
                if messagebox.askyesno(
                    "Administrator Rights Required", 
                    f"Some files require administrator privileges to delete. Examples:\n\n{protected_files[0]}\n\nWould you like to restart the application with administrator privileges?"
                ):
                    self.restart_as_admin()
                    return
            
            # Normal deletion process
            deleted_count = 0
            deletion_errors = 0
            failed_files = []
            
            # Show progress dialog
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Deleting Files")
            progress_window.geometry("400x150")
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            progress_label = ttk.Label(progress_window, text="Deleting files...")
            progress_label.pack(pady=10)
            
            progress_bar = ttk.Progressbar(progress_window, mode='determinate', 
                                         maximum=len(selected_items))
            progress_bar.pack(fill=tk.X, padx=10)
            
            status_label = ttk.Label(progress_window, text="")
            status_label.pack(pady=5)
            
            # Add option to attempt administrator rights during deletion
            admin_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(
                progress_window, 
                text="Use administrator privileges (for system files)", 
                variable=admin_var
            ).pack(pady=5)
            
            # Process files one by one with better error handling
            for i, item in enumerate(selected_items):
                try:
                    values = self.tree.item(item, 'values')
                    if values and len(values) >= 3:
                        file_path = values[2]
                        file_name = os.path.basename(file_path)
                        
                        # Update progress display
                        progress_label.config(text=f"Deleting: {file_name}")
                        status_label.config(text=f"Processing file {i+1} of {len(selected_items)}")
                        progress_window.update()
                        
                        logging.info(f"Attempting to delete: {file_path}")
                        
                        # Check file existence
                        if not os.path.exists(file_path):
                            logging.warning(f"File not found: {file_path}")
                            status_label.config(text=f"File not found: {file_name}")
                            progress_window.update()
                            time.sleep(0.5)
                            deletion_errors += 1
                            failed_files.append(f"{file_path} (Not found)")
                            continue
                        
                        # If admin mode is checked, try to use the elevated delete method
                        if admin_var.get() and os.name == 'nt' and self._is_protected_path(file_path):
                            try:
                                # Handle system file deletion with psexec or similar tool if available
                                import subprocess
                                # Use del command with elevated cmd
                                cmd = f'powershell.exe -Command "Start-Process cmd -ArgumentList \'/c del /f /q \"{file_path}\"\'  -Verb RunAs"'
                                subprocess.run(cmd, shell=True, timeout=5)
                                
                                # Check if deletion was successful
                                if not os.path.exists(file_path):
                                    success = True
                                else:
                                    success = False
                            except Exception as e:
                                logging.error(f"Error using elevated deletion: {e}")
                                success = False
                        else:
                            # Regular deletion method
                            if hasattr(self.temp_finder, 'delete_file'):
                                success = self.temp_finder.delete_file(file_path)
                            else:
                                # Fallback to our implementation
                                success = self._direct_delete_file(file_path)
                        
                        if success or not os.path.exists(file_path):
                            self.tree.delete(item)
                            deleted_count += 1
                            status_label.config(text=f"Successfully deleted: {file_name}")
                        else:
                            deletion_errors += 1
                            failed_files.append(file_path)
                            status_label.config(text=f"Failed to delete: {file_name}")
                        
                    progress_bar['value'] = i + 1
                    progress_window.update()
                    time.sleep(0.1)  # Short delay for UI responsiveness
                    
                except Exception as e:
                    logging.error(f"Error during deletion: {e}")
                    deletion_errors += 1
                    failed_files.append(f"{file_path if 'file_path' in locals() else 'Unknown'} ({str(e)})")
                    status_label.config(text=f"Error: {str(e)}")
                    progress_window.update()
            
            # Add a "Run as admin" button if there were failures
            if deletion_errors > 0 and os.name == 'nt':
                ttk.Button(
                    progress_window,
                    text="Restart as Administrator",
                    command=lambda: [progress_window.destroy(), self.restart_as_admin()]
                ).pack(pady=10)
            
            # Update the final status
            if deleted_count > 0:
                status_label.config(text=f"Completed: {deleted_count} files deleted successfully")
            else:
                status_label.config(text="No files were deleted successfully")
            
            # Update stats after deletion
            self.update_stats()
            
            # Don't auto-close if there were errors
            if deletion_errors == 0:
                self.root.after(1000, progress_window.destroy)
            
            # Show detailed results in a separate message
            if deletion_errors > 0:
                error_message = f"Successfully deleted {deleted_count} files.\n"
                error_message += f"{deletion_errors} files could not be deleted.\n\n"
                error_message += "Failed files:\n"
                error_message += "\n".join(failed_files[:5])
                if len(failed_files) > 5:
                    error_message += f"\n\n... and {len(failed_files) - 5} more"
                
                messagebox.showwarning("Delete Results", error_message)
            else:
                messagebox.showinfo("Delete Complete", f"Successfully deleted {deleted_count} files")

    def _direct_delete_file(self, file_path):
        """More direct file deletion method with better error handling"""
        try:
            logging.info(f"Direct delete attempt: {file_path}")
            
            # Check if it's a directory or file and handle accordingly
            if os.path.isdir(file_path):
                if not os.listdir(file_path):  # Only delete if empty
                    os.rmdir(file_path)
                    logging.info(f"Directory removed: {file_path}")
                    return True
                else:
                    # Try to remove with shutil for non-empty directories
                    try:
                        import shutil
                        shutil.rmtree(file_path)
                        logging.info(f"Directory tree removed: {file_path}")
                        return True
                    except Exception as e:
                        logging.error(f"Failed to remove directory tree: {e}")
                        return False
            else:
                # For files, try to ensure the file isn't read-only first
                try:
                    if os.name == 'nt':  # Windows
                        import stat
                        if not os.access(file_path, os.W_OK):
                            os.chmod(file_path, stat.S_IWRITE)
                            logging.info(f"Changed file permissions to writable: {file_path}")
                except Exception as e:
                    logging.warning(f"Failed to modify file permissions: {e}")
                
                # Now try to delete the file
                os.remove(file_path)
                logging.info(f"File removed: {file_path}")
                return True
                
        except PermissionError:
            logging.error(f"Permission denied: {file_path}")
            # If permission is denied, offer to restart as admin
            if os.name == 'nt' and messagebox.askyesno(
                "Administrator Rights Required", 
                f"Permission denied when trying to delete:\n{file_path}\n\nWould you like to restart the application with administrator privileges?"
            ):
                self.restart_as_admin()
            return False
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            return False
        except OSError as e:
            logging.error(f"OS error deleting {file_path}: {e}")
            # If access is denied, offer to restart as admin
            if os.name == 'nt' and "Access is denied" in str(e) and messagebox.askyesno(
                "Administrator Rights Required", 
                f"Access denied when trying to delete:\n{file_path}\n\nWould you like to restart the application with administrator privileges?"
            ):
                self.restart_as_admin()
            return False
        except Exception as e:
            logging.error(f"Unexpected error deleting {file_path}: {e}")
            return False

    def restart_as_admin(self):
        """Restart the application with administrator privileges"""
        if os.name == 'nt':  # Windows only
            try:
                import ctypes, sys
                
                # Check if already running as admin
                if ctypes.windll.shell32.IsUserAnAdmin():
                    messagebox.showinfo("Information", "Already running with administrator privileges.")
                    return
                
                # Create a simple script to show success message after restart
                import tempfile
                restart_script = tempfile.NamedTemporaryFile(suffix='.py', delete=False)
                with open(restart_script.name, 'w') as f:
                    f.write("""
import os, sys, tkinter as tk
from tkinter import messagebox

messagebox.showinfo("Elevated Privileges", "Application restarted with administrator privileges.")

# Start the main application
os.execv(sys.executable, [sys.executable] + sys.argv)
""")
                
                # Use ShellExecute to trigger UAC prompt
                script_path = os.path.abspath(sys.argv[0])
                logging.info(f"Restarting with admin privileges: {script_path}")
                
                # Use a direct method to start as admin
                ctypes.windll.shell32.ShellExecuteW(
                    None, 
                    "runas", 
                    sys.executable, 
                    f'"{restart_script.name}" "{script_path}"', 
                    None, 
                    1
                )
                
                # Close current instance
                self.root.destroy()
                sys.exit(0)
            except Exception as e:
                logging.error(f"Failed to restart with admin privileges: {e}")
                messagebox.showerror("Error", f"Failed to restart with admin privileges: {e}")

    def update_stats(self):
        stats = self.temp_finder.get_stats_summary()
        
        self.type_tree.delete(*self.type_tree.get_children())
        self.age_tree.delete(*self.age_tree.get_children())
        self.size_tree.delete(*self.size_tree.get_children())
        
        self.type_tree.insert('', 'end', values=('Total Size', stats['total_size']))
        self.age_tree.insert('', 'end', values=('Total Size', stats['total_size']))
        self.size_tree.insert('', 'end', values=('Total Size', stats['total_size']))
        
        for category, data in stats['file_stats'].items():
            self.type_tree.insert('', 'end', values=(category.title(), data['size'], f"{data['percent']:.1f}%"))
            self.age_tree.insert('', 'end', values=(category.title(), data['size'], f"{data['percent']:.1f}%"))
            self.size_tree.insert('', 'end', values=(category.title(), data['size'], f"{data['percent']:.1f}%"))

        self.update_chart()

    def update_chart(self):
        stats = self.temp_finder.get_stats_summary()
        chart_type = self.chart_type_var.get()
        
        if chart_type == "type":
            self.update_pie_chart(stats, "by_type")
        elif chart_type == "age":
            self.update_pie_chart(stats, "by_age")
        elif chart_type == "size":
            self.update_pie_chart(stats, "by_size")

    def update_pie_chart(self, stats, data_key="by_type"):
        if not matplotlib_available:
            return
        
        try:
            self.fig.clear()
            # Set figure facecolor to match theme
            self.fig.patch.set_facecolor(FuturisticTheme.LIGHT_BG)
            
            ax = self.fig.add_subplot(111)
            # Set axes facecolor to match theme
            ax.set_facecolor(FuturisticTheme.LIGHT_BG)
            
            # Text color for labels
            ax.xaxis.label.set_color(FuturisticTheme.TEXT)
            ax.yaxis.label.set_color(FuturisticTheme.TEXT)
            ax.tick_params(axis='x', colors=FuturisticTheme.TEXT)
            ax.tick_params(axis='y', colors=FuturisticTheme.TEXT)
            
            sizes = []
            labels = []
            for key, size_str in stats['file_stats'][data_key].items():
                # Convert size strings back to numbers for the chart
                for unit_mult, unit in [(1, 'B'), (1024, 'KB'), (1024**2, 'MB'), 
                                       (1024**3, 'GB'), (1024**4, 'TB')]:
                    if unit in size_str:
                        try:
                            size_val = float(size_str.split()[0]) * unit_mult
                            if size_val > 0:  # Only include non-zero values
                                sizes.append(size_val)
                                labels.append(f"{key}\n{size_str}")
                            break
                        except (ValueError, IndexError):
                            pass
            
            if not sizes or sum(sizes) == 0:
                ax.text(0.5, 0.5, "No data to display", 
                        horizontalalignment='center', verticalalignment='center',
                        color=FuturisticTheme.TEXT_MUTED)
                ax.axis('off')
            else:
                # Use a modern color palette
                colors = ['#7B68EE', '#5D5FEF', '#4B7BE5', '#3498db', '#2ecc71', 
                         '#f1c40f', '#e67e22', '#e74c3c', '#9b59b6', '#34495e']
                
                # Create the pie chart with shadow and explosion effect
                wedges, texts, autotexts = ax.pie(
                    sizes, 
                    labels=labels, 
                    autopct='%1.1f%%',
                    shadow=True,
                    startangle=90,
                    explode=[0.05] * len(sizes),  # Slight explosion effect
                    colors=colors[:len(sizes)]
                )
                
                # Style the text
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
            
            ax.axis('equal')
            
            self.canvas.draw()
        except Exception as e:
            logging.error(f"Error updating pie chart: {e}")

    def apply_filters(self):
        logging.info("Apply filters button clicked")
        try:
            file_type = self.file_type_var.get()
            age = self.age_filter_var.get()
            size = self.size_filter_var.get()

            # Update status for user feedback
            self.status_text.set(f"Filtering results...")
            self.root.update_idletasks()

            # Use a cache to store filtered results for the current filter settings
            cache_key = (file_type, age, size)
            if cache_key in self.filtered_cache:
                filtered_files = self.filtered_cache[cache_key]
            else:
                filtered_files = self.filter_files(self.temp_files, file_type, age, size)
                self.filtered_cache[cache_key] = filtered_files

            # Clear the tree with visual feedback
            self.tree.delete(*self.tree.get_children())
            
            # Update tree in batches to keep UI responsive
            self.update_tree_view(filtered_files)
            
            # Update status with results
            self.status_text.set(f"Showing {len(filtered_files)} filtered results")
            
        except Exception as e:
            logging.error(f"Error applying filters: {e}")
            messagebox.showerror("Filter Error", f"Error applying filters: {str(e)}")

    def filter_files(self, files, file_type, age, size):
        filtered = []
        for file_info in files:
            if self.matches_filter(file_info, file_type, age, size):
                filtered.append(file_info)
        return filtered

    def matches_filter(self, file_info, file_type, age, size):
        if file_type != 'all':
            if file_type == 'temp' and not any(pattern in file_info['path'].lower() 
                                             for pattern in ['.tmp', '.temp']):
                return False
            if file_type == 'cache' and '.cache' not in file_info['path'].lower():
                return False
            if file_type == 'logs' and '.log' not in file_info['path'].lower():
                return False

        if age != 'all':
            age_days = file_info['age_days']
            if age == 'recent' and age_days >= 7:
                return False
            if age == 'week' and (age_days < 7 or age_days >= 30):
                return False
            if age == 'month' and (age_days < 30 or age_days >= 90):
                return False
            if age == 'old' and age_days < 90:
                return False

        if size != 'all':
            file_size_mb = file_info['size'] / (1024 * 1024)
            if size == 'small' and file_size_mb >= 1:
                return False
            if size == 'medium' and (file_size_mb < 1 or file_size_mb >= 10):
                return False
            if size == 'large' and (file_size_mb < 10 or file_size_mb >= 100):
                return False
            if size == 'huge' and file_size_mb < 100:
                return False

        return True

    def add_excluded_dir(self):
        new_dir = messagebox.askstring("Add Excluded Directory", "Enter the directory path:")
        if new_dir:
            self.temp_finder.add_excluded_dir(new_dir)
            self.excluded_dirs_list.insert(tk.END, new_dir)

    def remove_excluded_dir(self):
        selected_index = self.excluded_dirs_list.curselection()
        if selected_index:
            removed_dir = self.excluded_dirs_list.get(selected_index[0])
            self.temp_finder.remove_excluded_dir(removed_dir)
            self.excluded_dirs_list.delete(selected_index[0])

    def treeview_sort_column(self, column, descending):
        data = [(self.tree.set(child, column), child) for child in self.tree.get_children('')]
        
        # Custom sort for size column
        if column == 'size':
            # Extract numeric values and units for proper sorting
            def size_to_bytes(size_str):
                try:
                    parts = size_str.split()
                    if len(parts) != 2:
                        return 0
                    value, unit = float(parts[0]), parts[1]
                    multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
                    return value * multipliers.get(unit, 0)
                except (ValueError, IndexError):
                    return 0
                
            data.sort(key=lambda x: size_to_bytes(x[0]), reverse=descending)
        # Custom sort for age column
        elif column == 'age':
            # Extract values for proper sorting based on time
            def age_to_days(age_str):
                try:
                    if "hour" in age_str:
                        return float(age_str.split()[0]) / 24 if age_str != "Less than an hour" else 0
                    elif "day" in age_str:
                        return float(age_str.split()[0])
                    elif "week" in age_str:
                        return float(age_str.split()[0]) * 7
                    elif "month" in age_str:
                        return float(age_str.split()[0]) * 30
                    elif "year" in age_str:
                        return float(age_str.split()[0]) * 365
                    return 0
                except (ValueError, IndexError):
                    return 0
                
            data.sort(key=lambda x: age_to_days(x[0]), reverse=descending)
        else:
            data.sort(reverse=descending)
        
        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)
        self.tree.heading(column, command=lambda: self.treeview_sort_column(column, not descending))

    def select_all(self):
        self.tree.selection_set(self.tree.get_children())

    def deselect_all(self):
        self.tree.selection_remove(self.tree.get_children())

    def on_tab_change(self, event):
        """Handle tab change events"""
        tab_index = self.notebook.index(self.notebook.select())
        
        # Update UI elements based on active tab
        if tab_index == 0:  # Scanner tab
            self.status_text.set("Scanner: Ready to clean temporary files")
        elif tab_index == 1:  # Statistics tab
            # Update statistics when switching to the stats tab
            self.update_stats()
            self.status_text.set("Statistics: File breakdown analysis")
        elif tab_index == 2:  # Settings tab
            self.status_text.set("Settings: Configure application behavior")

    def on_search_change(self, *args):
        """Filter the tree view when search text changes"""
        search_text = self.search_var.get().lower()
        if not search_text:
            # If search is empty, restore all items or apply current filters
            self.apply_filters()
            return
        
        # Hide all items first
        children = self.tree.get_children()
        for child in children:
            self.tree.detach(child)
        
        # Show only matching items
        for file_info in self.temp_files:
            if search_text in file_info['path'].lower():
                if self.matches_filter(file_info, 
                                      self.file_type_var.get(),
                                      self.age_filter_var.get(),
                                      self.size_filter_var.get()):
                    self.tree.insert('', 'end', values=(
                        file_info['size_formatted'],
                        file_info['age'],
                        file_info['path']
                    ))
        
        # Update status
        self.status_text.set(f"Found {len(self.tree.get_children())} items matching '{search_text}'")

    def select_matching(self):
        """Select all items that match the current search"""
        search_text = self.search_var.get().lower()
        if not search_text:
            return
        
        children = self.tree.get_children()
        selection = []
        
        for child in children:
            values = self.tree.item(child, 'values')
            path = values[2]
            if search_text in path.lower():
                selection.append(child)
        
        if selection:
            self.tree.selection_set(selection)
            self.update_selection_stats()

    def update_selection_stats(self, event=None):
        """Update the quick stats based on selection"""
        selection = self.tree.selection()
        if not selection:
            self.quick_stats_var.set("0 items selected (0 B)")
            return
        
        # Calculate total size of selected files
        total_size = 0
        for item in selection:
            values = self.tree.item(item, 'values')
            size_str = values[0]
            
            # Parse the size string
            try:
                parts = size_str.split()
                if len(parts) == 2:
                    value, unit = float(parts[0]), parts[1]
                    multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
                    total_size += value * multipliers.get(unit, 0)
            except:
                pass
        
        # Format the total size
        formatted_size = self.temp_finder.format_size(total_size)
        self.quick_stats_var.set(f"{len(selection)} items selected ({formatted_size})")

    def fade_out_tree(self):
        """Visually fade out tree view before clearing"""
        # Save current selection
        self.tree.selection_remove(self.tree.selection())
        
        # Clear the tree
        self.tree.delete(*self.tree.get_children())
        
        # Reset search and filters
        self.search_var.set("")
        self.quick_stats_var.set("0 items selected (0 B)")
        
        # Optional: could add actual fade effect with canvas or opacity if supported

    def pulse_button(self, button, color):
        """Create a visual pulse effect on a button"""
        try:
            # Store original style
            original_style = button.cget("style") or "TButton"
            
            # Create a unique pulse style name
            pulse_style = f"Pulse{original_style}"
            
            # Configure the pulse style
            style = ttk.Style()
            style.configure(pulse_style, background=color)
            
            # Apply pulse style
            button.configure(style=pulse_style)
            
            # Reset after delay
            self.root.after(200, lambda: button.configure(style=original_style))
        except Exception as e:
            logging.warning(f"Pulse effect failed (non-critical): {e}")
            # Continue with scan even if pulse fails

    def show_about_dialog(self):
        messagebox.showinfo("About Ultra Temp Cleaner", 
                            "Ultra Temp Cleaner v1.0.0\n\nA futuristic tool to clean temporary files and optimize your system.\n\nDeveloped by Your Name.")

    def scan_directory(self, directory):
        """Scan a directory with proper error handling and progress updates"""
        try:
            # Check if directory exists and is accessible
            if not os.path.exists(directory):
                logging.warning(f"Directory not found: {directory}")
                return [], 0
            
            if not os.path.isdir(directory):
                logging.warning(f"Not a directory: {directory}")
                return [], 0
            
            scanned_files = []
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(directory, onerror=self._handle_walk_error):
                # Skip excluded directories
                dirs[:] = [d for d in dirs if os.path.join(root, d) not in self.temp_finder.excluded_dirs]
                
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        file_info = self.temp_finder.get_file_info(file_path)
                        if file_info:
                            scanned_files.append(file_info)
                            total_size += file_info['size']
                            file_count += 1
                            
                            # Update progress more frequently for feedback
                            if file_count % 50 == 0:
                                # Use root.after to safely update from thread
                                self.root.after(0, lambda p=file_path: 
                                    self.progress_var.set(f"Scanning: {os.path.basename(p)}"))
                                
                    except Exception as e:
                        logging.error(f"Error processing file {file}: {e}")
                        continue
                    
            return scanned_files, total_size
        
        except Exception as e:
            logging.error(f"Error scanning directory {directory}: {e}")
            return [], 0

    def _handle_walk_error(self, error):
        """Handle errors during directory walk"""
        logging.error(f"Directory walk error: {error}")

    def clear_cache(self):
        """Clear the results cache to free memory"""
        self.filtered_cache.clear()
        self.temp_files.clear()
        gc.collect()  # Force garbage collection

    def update_tree_view(self, items, batch_size=1000):
        """Update tree view in batches to prevent UI freezing"""
        self.tree.delete(*self.tree.get_children())
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            for item in batch:
                self.tree.insert('', 'end', values=(
                    item['size_formatted'],
                    item['age'],
                    item['path']
                ))
            self.root.update_idletasks()  # Allow UI to update

    def setup_debug_logging(self):
        """Setup additional debug logging for UI events"""
        def trace_event(event_name):
            def callback(*args):
                logging.debug(f"UI Event: {event_name} triggered with args: {args}")
                return True
            return callback
        
        # Trace key UI events - only bind if the button exists
        if hasattr(self, 'scan_button'):
            self.scan_button.bind("<Button-1>", trace_event("scan_button_click"), add="+")
        
        if hasattr(self, 'stop_button'):
            self.stop_button.bind("<Button-1>", trace_event("stop_button_click"), add="+")
        
        if hasattr(self, 'apply_filter_btn'):
            self.apply_filter_btn.bind("<Button-1>", trace_event("apply_filter_click"), add="+")
        
        if hasattr(self, 'notebook'):
            self.notebook.bind("<<NotebookTabChanged>>", trace_event("tab_changed"), add="+")
        
        # Log this so we know we completed setup
        logging.info("Debug event logging setup completed")

    def test_ui_elements(self):
        """Test all UI elements to verify they are working correctly"""
        try:
            # Test basic UI functionality
            self.notebook.select(0)  # Switch to scan tab
            self.scan_location_var.set("temp")
            self.file_type_var.set("all")
            self.age_filter_var.set("all")
            self.size_filter_var.set("all")
            
            # Update status to confirm things are working
            self.status_text.set("UI test successful - interface is responding")
            messagebox.showinfo("UI Test", "UI elements test completed successfully")
            return True
        except Exception as e:
            logging.error(f"UI test failed: {e}")
            messagebox.showerror("UI Test Failed", f"Error: {str(e)}")
            return False

    def debug_button_click(self, btn_name):
        """Function to test if button clicks are working"""
        logging.info(f"Button '{btn_name}' clicked!")
        messagebox.showinfo("Button Clicked", f"The {btn_name} button was clicked successfully!")
        self.status_text.set(f"{btn_name} button works!")

    def simple_test_scan(self):
        """Simplified scan for testing button functionality"""
        logging.info("Running simple test scan")
        location = self.scan_location_var.get()
        logging.info(f"Current scan location setting: {location}")
        
        try:
            # Update UI state
            self.scan_button.configure(state='disabled')
            self.stop_button.configure(state='normal')
            self.progress_var.set(f"Test scan in progress ({location} mode)...")
            self.progress_bar.start(10)
            
            # Create some dummy data
            import random
            import time
            
            def dummy_scan():
                dummy_files = []
                for i in range(20):
                    if not hasattr(self, 'scanning') or not self.scanning:
                        break
                        
                    # Create dummy file info
                    size = random.randint(1000, 10000000)
                    dummy_info = {
                        'path': f"C:/temp/test_file_{i}.tmp",
                        'size': size,
                        'size_formatted': f"{size/1024:.1f} KB",
                        'age': f"{random.randint(1, 30)} days",
                        'age_days': random.randint(1, 30)
                    }
                    
                    dummy_files.append(dummy_info)
                    
                    # Use root.after to safely update from thread
                    self.root.after(0, lambda p=dummy_info['path']: 
                        self.progress_var.set(f"Scanning: {os.path.basename(p)}"))
                    time.sleep(0.2)  # Simulate scanning delay
                    
                # Update the main list safely
                self.root.after(0, lambda: setattr(self, 'temp_files', dummy_files))
                self.root.after(0, self.finish_scan)
            
            self.scanning = True
            threading.Thread(target=dummy_scan, daemon=True).start()
            
        except Exception as e:
            logging.error(f"Error in test scan: {e}")
            messagebox.showerror("Test Error", f"Error during test scan: {str(e)}")

    def test_all_buttons(self):
        """Comprehensive test of all buttons"""
        logging.info("Testing all buttons...")
        messagebox.showinfo("Button Test", "Now testing all buttons in the application.\n\nClick OK to continue.")
        
        try:
            # Test scan button
            self.scan_button.invoke()
            time.sleep(1)
            self.stop_button.invoke()
            
            # Test apply filter button
            self.apply_filter_btn.invoke()
            
            # Switch to settings tab and test buttons there
            self.notebook.select(2)  # Settings tab
            messagebox.showinfo("Test Successful", "Button test completed successfully!")
            
        except Exception as e:
            logging.error(f"Button test failed: {e}")
            messagebox.showerror("Test Failed", f"Button test failed: {e}")

    def save_bug_report(self):
        """Generate and save a bug report"""
        try:
            report = ["=== Ultra Temp Cleaner Bug Report ==="]
            report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"Python Version: {sys.version}")
            report.append(f"Platform: {sys.platform}")
            report.append(f"Matplotlib Available: {matplotlib_available}")
            
            # Get status of UI elements
            report.append("\n=== UI State ===")
            report.append(f"Current Tab: {self.notebook.index(self.notebook.select())}")
            report.append(f"Scan Button State: {self.scan_button.cget('state')}")
            report.append(f"Stop Button State: {self.stop_button.cget('state')}")
            
            # Get TempFileFinder stats
            report.append("\n=== Scanner State ===")
            report.append(f"Scanning: {getattr(self.temp_finder, 'scanning', False)}")
            report.append(f"Total Files Found: {len(self.temp_files)}")
            
            # Get last few log entries
            report.append("\n=== Recent Logs ===")
            try:
                with open('temp_file_finder.log', 'r') as f:
                    logs = f.readlines()
                    report.extend(logs[-20:])  # Last 20 log entries
            except:
                report.append("Could not read log file")
            
            # Save report
            with open('bug_report.txt', 'w') as f:
                f.write('\n'.join(report))
            
            messagebox.showinfo("Bug Report", "Bug report saved to bug_report.txt")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create bug report: {e}")

    def test_buttons(self):
        """Test and fix button functionality"""
        try:
            # Ensure all required buttons exist
            if not hasattr(self, 'scan_button'):
                messagebox.showerror("Missing Button", "Scan button not found!")
                return
            
            if not hasattr(self, 'apply_filter_btn'):
                messagebox.showerror("Missing Button", "Apply filter button not found!")
                return
            
            # Manually trigger commands to test
            messagebox.showinfo("Button Test", "Testing buttons... click OK to continue")
            
            # Try to trigger scan button command
            self.debug_button_click("Scan")
            self.scan_button.invoke()
            
            # Wait briefly then stop
            self.root.after(1000, lambda: self.stop_scan())
            
            messagebox.showinfo("Success", "Button tests completed successfully!")
            
        except Exception as e:
            logging.error(f"Button test failed: {e}")
            messagebox.showerror("Test Failed", f"Error testing buttons: {e}")

    def on_location_change(self, location):
        """Handle change in scan location radio button"""
        logging.info(f"Scan location changed to: {location}")
        # Ensure the StringVar is set correctly
        self.scan_location_var.set(location)
        # Update UI to reflect the change
        self.status_text.set(f"Ready to scan {location} directories")

    def test_radio_buttons(self):
        """Test if radio buttons are working correctly"""
        current_value = self.scan_location_var.get()
        logging.info(f"Current radio button value: {current_value}")
        
        # Toggle between values using the direct command
        new_value = "all" if current_value == "temp" else "temp"
        logging.info(f"Attempting to set radio button to: {new_value}")
        
        # Use our button-based method
        self.set_scan_location(new_value)
        
        # Get the actual value after setting
        after_value = self.scan_location_var.get()
        logging.info(f"Value after setting: {after_value}")
        
        # Show result to user
        success = after_value == new_value
        if success:
            messagebox.showinfo("Radio Button Test", 
                              f"Radio button change successful! Value: {after_value}")
        else:
            # Try the force method if normal setting failed
            forced_value = self.force_variable_update(self.scan_location_var, new_value)
            logging.info(f"Force-set value: {forced_value}")
            
            if forced_value == new_value:
                messagebox.showinfo("Radio Button Test", 
                                  f"Radio button required force-setting, but now works! Value: {forced_value}")
            else:
                messagebox.showerror("Radio Button Test", 
                                   f"Radio button change failed even with force-setting. Tried to set {new_value} but got {forced_value}")
        
        return success

    def set_scan_location(self, location):
        """Set the scan location and update button styles"""
        logging.info(f"Setting scan location to: {location}")
        self.scan_location_var.set(location)
        self.update_location_buttons(location)
        self.status_text.set(f"Ready to scan {location} directories")

    def update_location_buttons(self, active_location):
        """Update the appearance of location buttons based on selection"""
        # Create/update styles for the buttons
        style = ttk.Style()
        
        # Configure active and inactive styles
        if not style.lookup("Active.TButton", "background"):
            style.configure("Active.TButton", 
                           background=FuturisticTheme.ACCENT,
                           foreground=FuturisticTheme.TEXT)
            style.configure("Inactive.TButton", 
                           background=FuturisticTheme.LIGHT_BG,
                           foreground=FuturisticTheme.TEXT_MUTED)
        
        # Apply appropriate styles to buttons
        if active_location == "temp":
            self.temp_button.configure(style="Active.TButton")
            self.all_button.configure(style="Inactive.TButton")
        else:
            self.temp_button.configure(style="Inactive.TButton")
            self.all_button.configure(style="Active.TButton")
        
        logging.info(f"Updated location buttons. Active: {active_location}")

    def manual_test_radio(self):
        """Provide an enhanced manual test for the location buttons"""
        result_window = tk.Toplevel(self.root)
        result_window.title("Location Selection Test")
        result_window.geometry("400x400")
        result_window.transient(self.root)
        
        # Current value
        ttk.Label(result_window, text="Current location:").pack(pady=5)
        current_value = ttk.Label(result_window, text=self.scan_location_var.get(), font=('Segoe UI', 12, 'bold'))
        current_value.pack(pady=5)
        
        # Status message
        status_var = tk.StringVar(value="Ready to test")
        status = ttk.Label(result_window, textvariable=status_var, foreground=FuturisticTheme.ACCENT)
        status.pack(pady=5)
        
        # Force variable update
        def force_update(new_value):
            old_value = self.scan_location_var.get()
            forced_value = self.force_variable_update(self.scan_location_var, new_value)
            current_value.config(text=forced_value)
            status_var.set(f"Changed: {old_value} → {forced_value}")
        
        # Test buttons section
        ttk.Label(result_window, text="Direct Button Controls", font=('Segoe UI', 10, 'bold')).pack(pady=10)
        
        ttk.Button(
            result_window, 
            text="Scan Temp Directories", 
            command=self.scan_temp_dirs
        ).pack(pady=5, padx=20, fill=tk.X)
        
        ttk.Button(
            result_window, 
            text="Scan All Drives", 
            command=self.scan_all_drives
        ).pack(pady=5, padx=20, fill=tk.X)
        
        # Force update section
        ttk.Separator(result_window, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Label(result_window, text="Force Variable Update", font=('Segoe UI', 10, 'bold')).pack(pady=5)
        
        ttk.Button(
            result_window, 
            text="Force Set to 'temp'", 
            command=lambda: force_update("temp")
        ).pack(pady=5, padx=20, fill=tk.X)
        
        ttk.Button(
            result_window, 
            text="Force Set to 'all'", 
            command=lambda: force_update("all")
        ).pack(pady=5, padx=20, fill=tk.X)
        
        # Check and refresh
        ttk.Separator(result_window, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Label(result_window, text="Diagnostics", font=('Segoe UI', 10, 'bold')).pack(pady=5)
        
        ttk.Button(
            result_window, 
            text="Refresh Current Value", 
            command=lambda: [current_value.config(text=self.scan_location_var.get()), 
                             status_var.set("Value refreshed")]
        ).pack(pady=5, padx=20, fill=tk.X)
        
        ttk.Button(
            result_window, 
            text="Run Test Scan (Using Current Value)", 
            command=lambda: [self.do_scan(self.scan_location_var.get()), 
                             status_var.set(f"Starting scan with: {self.scan_location_var.get()}")]
        ).pack(pady=5, padx=20, fill=tk.X)

    def force_variable_update(self, var, value):
        """Force Tkinter to recognize a variable change by using trace callbacks"""
        # First, remove all traces
        for mode in ['w', 'r', 'u']:
            while True:
                try:
                    var.trace_vdelete(mode, var.trace_info()[0][1])
                except IndexError:
                    break
                except Exception as e:
                    logging.error(f"Error removing trace: {e}")
                    break
                
        # Set the value
        var.set(value)
        
        # Update the UI
        self.root.update_idletasks()
        
        # Return the current value as verification
        return var.get()

    def scan_temp_dirs(self):
        """Direct method to scan temp directories only"""
        logging.info("Starting scan of temp directories...")
        
        # Update buttons appearance
        self.update_location_buttons("temp")
        
        # Set the location variable explicitly
        self.scan_location_var.set("temp")
        
        # Start the scan with real temp directories
        self.do_scan("temp")

    def scan_all_drives(self):
        """Direct method to scan all drives"""
        logging.info("Starting scan of all drives...")
        
        # Update buttons appearance
        self.update_location_buttons("all")
        
        # Set the location variable explicitly
        self.scan_location_var.set("all")
        
        # Start the scan with all drives
        self.do_scan("all")

    def do_scan(self, location_type):
        """Core scanning function with explicit location parameter"""
        logging.info(f"Performing scan with location type: {location_type}")
        
        try:
            # First ensure UI is responsive
            self.ensure_ui_response()
            
            # Clear previous results and cache
            self.clear_cache()
            
            # Update UI state - skip pulse effect if it fails
            try:
                self.pulse_button(self.scan_button, FuturisticTheme.SUCCESS)
            except:
                pass
                
            self.fade_out_tree()
            
            # Update UI state
            self.scan_button.configure(state='disabled')
            self.stop_button.configure(state='normal')
            self.progress_var.set("Initializing scan...")
            self.progress_bar.start(10)
            
            # Update message based on location
            if location_type == "temp":
                self.status_text.set("Scanning temporary directories...")
            else:
                self.status_text.set("Scanning all drives (this may take a while)...")
            
            self.temp_finder.scanning = True
            self.temp_finder.reset_stats()
            
            def scan_thread():
                try:
                    temp_files = []
                    
                    if location_type == "temp":
                        temp_dirs = self.temp_finder.get_system_temp_dirs()
                        logging.info(f"Scanning temp directories: {temp_dirs}")
                        for temp_dir in temp_dirs:
                            if not self.temp_finder.scanning:
                                break
                            self.root.after(0, lambda dir=temp_dir: 
                                self.progress_var.set(f"Scanning: {dir}"))
                            files = self.temp_finder.scan_for_temp_files(temp_dir, self.update_progress)
                            if files:  # Only extend if files were found
                                temp_files.extend(files)
                    else:  # scan all drives
                        self.root.after(0, lambda: 
                            self.progress_var.set("Scanning all drives..."))
                        files = self.temp_finder.scan_for_temp_files(None, self.update_progress)
                        if files:  # Only extend if files were found
                            temp_files.extend(files)
                    
                    # Update the UI with results
                    self.root.after(0, lambda: setattr(self, 'temp_files', temp_files))
                    logging.info(f"Scan completed. Found {len(temp_files)} files.")
                    
                except Exception as e:
                    logging.error(f"Scan error: {e}")
                    self.root.after(0, lambda: 
                        messagebox.showerror("Error", f"Scan error: {str(e)}"))
                finally:
                    self.root.after(0, self.finish_scan)
            
            # Start the scan in a separate thread
            threading.Thread(target=scan_thread, daemon=True).start()
            
        except Exception as e:
            logging.error(f"Error in scan: {e}")
            messagebox.showerror("Scan Error", f"Error starting scan: {str(e)}")
            # Reset UI state in case of error
            self.scan_button.configure(state='normal')
            self.stop_button.configure(state='disabled')
            self.progress_bar.stop()

    def simple_test_scan_with_location(self, location_type):
        """Enhanced simplified scan that respects location type"""
        logging.info(f"Running simple test scan for location: {location_type}")
        
        try:
            # Update UI state
            self.scan_button.configure(state='disabled')
            self.stop_button.configure(state='normal')
            self.progress_var.set(f"Test scan in progress ({location_type} mode)...")
            self.progress_bar.start(10)
            
            # Create some dummy data
            import random
            import time
            
            def dummy_scan():
                dummy_files = []
                file_count = 20 if location_type == "temp" else 50  # More files for "all drives"
                
                for i in range(file_count):
                    if not hasattr(self, 'scanning') or not self.scanning:
                        break
                    
                    # Create different paths based on location type
                    if location_type == "temp":
                        path = f"C:/Windows/Temp/test_file_{i}.tmp"
                    else:
                        drive = ["C:", "D:", "E:"][random.randint(0, 2) % 3]  # Simulate different drives
                        path = f"{drive}/Users/test_file_{i}.tmp"
                    
                    # Create dummy file info
                    size = random.randint(1000, 10000000)
                    dummy_info = {
                        'path': path,
                        'size': size,
                        'size_formatted': f"{size/1024:.1f} KB",
                        'age': f"{random.randint(1, 30)} days",
                        'age_days': random.randint(1, 30)
                    }
                    
                    dummy_files.append(dummy_info)
                    
                    # Update UI
                    self.root.after(0, lambda p=dummy_info['path']: 
                        self.progress_var.set(f"Scanning: {os.path.basename(p)}"))
                    
                    # Simulate delay
                    time.sleep(0.1)
                
                # Update the main list safely
                self.root.after(0, lambda: setattr(self, 'temp_files', dummy_files))
                self.root.after(0, self.finish_scan)
            
            self.scanning = True
            threading.Thread(target=dummy_scan, daemon=True).start()
            
        except Exception as e:
            logging.error(f"Error in test scan: {e}")
            messagebox.showerror("Test Error", f"Error during test scan: {str(e)}")

    def _is_protected_path(self, path):
        """Check if a path likely requires admin privileges"""
        if not path or not os.name == 'nt':  # Only check on Windows
            return False
            
        try:
            path = path.lower()
            
            # Check common protected locations
            protected_locations = [
                os.environ.get('WINDIR', 'C:\\Windows').lower(),
                os.environ.get('SYSTEMROOT', 'C:\\Windows').lower(),
                'c:\\program files',
                'c:\\program files (x86)',
                'c:\\windows\\system32',
                'c:\\programdata'
            ]
            
            # Check for common system path patterns
            for loc in protected_locations:
                if path.startswith(loc):
                    return True
            
            # Check for write access
            if os.path.exists(path):
                try:
                    # Try to get file/folder write permission
                    if os.path.isdir(path):
                        test_file = os.path.join(path, '.temp_test_write')
                        with open(test_file, 'w') as f:
                            f.write('test')
                        os.remove(test_file)
                    else:
                        # For files, check if we can open it for writing
                        if not os.access(path, os.W_OK):
                            return True
                except (PermissionError, OSError):
                    return True
                    
            return False
        except Exception as e:
            logging.error(f"Error checking protected path {path}: {e}")
            return False  # Assume not protected if we can't check

    def init_system_tray(self):
        """Initialize the system tray icon if available"""
        if SYSTEM_TRAY_AVAILABLE:
            try:
                self.system_tray = get_system_tray(self)
                # Start tray icon in a separate thread
                threading.Thread(target=self._run_system_tray, daemon=True).start()
                logging.info("System tray icon initialized")
            except Exception as e:
                logging.error(f"Error initializing system tray: {e}")
                self.system_tray = None
    
    def _run_system_tray(self):
        """Run the system tray icon in a background thread"""
        if self.system_tray:
            try:
                self.system_tray.run()
            except Exception as e:
                logging.error(f"Error running system tray: {e}")
    
    def on_close(self):
        """Handle window close event"""
        # If system tray is active, minimize to tray instead of closing
        if self.system_tray and self.system_tray.is_running:
            self.hide()
        else:
            # Normal close
            self.exit()
    
    def hide(self):
        """Hide the window to system tray"""
        self.root.withdraw()
        
        # Notify user if first time
        if not hasattr(self, '_tray_notification_shown'):
            try:
                import pystray
                pystray.notify.icon = self.system_tray.icon
                pystray.notify.notification(
                    "Ultra Temp Cleaner Pro",
                    "Application minimized to system tray. Click the icon to restore."
                )
                self._tray_notification_shown = True
            except:
                pass
    
    def show(self):
        """Show the window from system tray"""
        self.root.deiconify()
        self.root.lift()
        
        # On Windows, force focus
        if os.name == 'nt':
            self.root.attributes('-topmost', True)
            self.root.update()
            self.root.attributes('-topmost', False)
    
    def exit(self):
        """Exit the application completely"""
        # Stop system tray if active
        if self.system_tray:
            try:
                self.system_tray.stop()
            except:
                pass
        
        # Destroy window and exit
        self.root.destroy()
        sys.exit(0)
    
    def show_results(self, files):
        """Show scan results (called from system tray)"""
        # Show the window
        self.show()
        
        # Switch to scanner tab
        self.notebook.select(0)  # Scanner tab
        
        # Update tree with results
        self.temp_files = files
        self.update_tree_view(files)
        
        # Update total size
        total_size = sum(f['size'] for f in files)
        self.total_size_var.set(f"Total: {self.temp_finder.format_size(total_size)}")
        
        # Update status
        self.status_text.set(f"Loaded {len(files)} files from system tray scan")

if __name__ == "__main__":
    root = tk.Tk()
    app = TempFileCleanerUI(root)
    
    # Check command line arguments for minimized mode
    if len(sys.argv) > 1 and "--minimized" in sys.argv and hasattr(app, 'hide'):
        # Start minimized to system tray if requested and available
        app.root.withdraw()
    
    root.mainloop()
