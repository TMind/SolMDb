import logging
import ipywidgets as widgets
from IPython.display import display

# === Logger Registry Functions ===

# A global dictionary to store registered loggers.
registered_loggers = {}

def register_logger(module_name, logger):
    """
    Registers a logger for a given module.
    
    Args:
        module_name (str): Typically __name__ of the module.
        logger (logging.Logger): The logger instance to register.
    """
    registered_loggers[module_name] = logger
    # Optional: print a message (or log it) when a logger is registered.
    print(f"Registered logger for {module_name}")

def get_registered_loggers():
    """
    Returns a copy of the dictionary of registered loggers.
    
    Returns:
        dict: Mapping of module names to logger objects.
    """
    return dict(registered_loggers)


# === Debug Widget Functions ===

def handle_debug_toggle(change, module_name=None):
    """
    Handles changes from a ToggleButtons widget to set the logging level.
    
    Args:
        change (dict): A change event from a widget.
        module_name (str, optional): The module whose logger will be updated.
                                     If None, the root logger is updated.
    """
    new_value = change['new']
    # Map textual representation to logging levels:
    logging_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    if new_value in logging_levels:
        level = logging_levels[new_value]
        if module_name:
            # If a module name is provided, update that logger.
            logging.getLogger(module_name).setLevel(level)
            print(f"Logger level for module '{module_name}' set to {new_value}")
        else:
            # Otherwise, update the global (root) logger.
            logging.getLogger().setLevel(level)
            print(f"Global logger level set to {new_value}")
    else:
        print(f"Unknown logger level: {new_value}")

def create_debug_widget(module_name=None):
    """
    Creates a ToggleButtons widget to select a logging level.
    
    Args:
        module_name (str, optional): Name of the module (e.g. __name__). If provided,
                                     this widget’s changes will update that module's logger.
    
    Returns:
        widgets.ToggleButtons: The debug toggle widget.
    """
    debug_toggle = widgets.ToggleButtons(
        value='CRITICAL',
        options=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        description='Debug',
        disabled=False,
        button_style='info',  # 'success', 'info', 'warning', 'danger' or ''
        tooltip='Set level of logging messages',
        icon='check'
    )
    # Use a lambda to pass along the module name (if any).
    debug_toggle.observe(lambda change: handle_debug_toggle(change, module_name=module_name),
                           names='value')
    return debug_toggle


# === Debug Tab Assembly ===

def get_debug_tab():
    """
    Creates and returns a VBox widget that contains:
      - A debug toggle widget for the global (root) logger.
      - A debug toggle widget for each registered module.
    
    Returns:
        widgets.VBox: The assembled debug tab widget.
    """
    # Create the global logger widget.
    global_widget = create_debug_widget()
    global_label = widgets.Label(value="Global Logger")
    global_box = widgets.VBox([global_label, global_widget])
    
    # Retrieve registered loggers.
    reg_loggers = get_registered_loggers()
    # Sort the logger names (you can adjust this filter if needed)
    module_names = sorted(reg_loggers.keys(), key=str.lower)
    
    # Create a debug widget for each registered module.
    module_debug_widgets = []
    for module_name in module_names:
        label = widgets.Label(value=module_name)
        mod_widget = create_debug_widget(module_name=module_name)
        module_debug_widgets.append(widgets.VBox([label, mod_widget]))
    
    # Assemble all widgets in a vertical box.
    debug_tab = widgets.VBox([global_box] + module_debug_widgets)
    return debug_tab


# === For Testing/Standalone Use ===
if __name__ == "__main__":
    # Optionally, register a couple of loggers manually for testing.
    # In your application, each module should call register_logger(__name__, logger).
    test_logger1 = logging.getLogger("ModuleA")
    test_logger1.setLevel(logging.WARNING)
    register_logger("ModuleA", test_logger1)

    test_logger2 = logging.getLogger("ModuleB")
    test_logger2.setLevel(logging.WARNING)
    register_logger("ModuleB", test_logger2)

    dt = get_debug_tab()
    display(dt)