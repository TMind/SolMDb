import ipywidgets as widgets

class EnhancedSelectMultiple:
    def __init__(self, *args, **kwargs):
        # Extract options from kwargs
        options = kwargs.pop('options', [])
        self._original_options = sorted(options, key=lambda x: x.lower())  # Sort options alphabetically

        # Extract layout from kwargs to apply consistent styling
        layout = kwargs.pop('layout', widgets.Layout())

        # Create the SelectMultiple widget with all available options and settings
        self.select_widget = widgets.SelectMultiple(
            options=self._original_options,
            layout=widgets.Layout(width='100%', height='150px', flex='1 1 auto', overflow='visible'),  # Set consistent height and prevent scrollbars
            **kwargs  # Pass all kwargs to the original SelectMultiple widget
        )

        # Create the search bar widget with a matching width to the SelectMultiple widget
        self.search_widget = widgets.Text(
            placeholder='Search options...',
            description='',
            layout=widgets.Layout(width='100%')  # Use the same width as SelectMultiple widget
        )

        # Observe changes in the search bar
        self.search_widget.observe(self.update_options, names='value')

        # Create a toggle button for this selection        
        self.toggle_button = widgets.ToggleButton(
            value=kwargs.pop('toggle_default', False),
            disabled=kwargs.pop('toggle_disable', False),
            description=kwargs.pop('toggle_description', ''),
            layout=widgets.Layout(width='100%', height='30px', margin='0px', padding='0px', box_sizing='border-box'),
            button_style='',
            style={'padding': '0px', 'margin': '0px'}
        )

        # Combine the toggle button, search bar, and the SelectMultiple widget in a VBox
        self.container = widgets.VBox([self.toggle_button, self.search_widget, self.select_widget], layout=layout)

    @property
    def options(self):
        return self._original_options

    @options.setter
    def options(self, new_options):
        #logging.info(f"Setting new options: {new_options}")
        self._original_options = sorted(new_options, key=lambda x: x.lower())
        # Directly set options to avoid redundant setter call
        self.select_widget.options = self._original_options
        self.select_widget.value = ()  # Reset selection to avoid invalid values

    @property
    def value(self):
        return self.select_widget.value

    @value.setter
    def value(self, new_value):
        self.select_widget.value = new_value       

    def update_options(self, change):
        search_value = change['new'].lower()
        
        if search_value == '':
            # If the search bar is empty, show all options including an empty option
            filtered_options = self._original_options        
        else:
            # Filter options based on the search value
            filtered_options = [name for name in self._original_options if search_value in name.lower()]        
        # Ensure the filtered options are displayed properly
        self.select_widget.options = filtered_options
        self.select_widget.value = ()  # Reset selection to avoid invalid values

    def update_options_from_db(self, new_options):
        """
        Update the options after the database becomes available.
        """
        self.options = new_options
        self._original_options = new_options       

    def get_widget(self):
        """
        Returns the main container widget that can be used directly in the UI.
        """
        return self.container

import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class VBoxManager:
    def __init__(self):
        self.main_vbox = widgets.VBox()  # Main container holding all VBoxes
        self.vboxes = {}  # Map grid_identifier -> VBox
        self.empty_vboxes = []  # List of empty VBoxes for reuse

    def has_widget(self, filter_row_index):
        """
        Check if a widget exists for a specific filter row index.

        Args:
            filter_row_index (int): The index of the filter row.

        Returns:
            bool: True if a widget exists for the index, False otherwise.
        """
        return filter_row_index in self.vboxes

    def add_widget(self, widget, index):
        """
        Add a widget to a VBox associated with a specific filter row index.

        Args:
            widget (Widget): The widget to add.
            index (int): The index of the filter row.
        """
    
        index = int(index)
        # If widget is not already a VBox, wrap it in a VBox
        if not isinstance(widget, widgets.VBox):
            widget = widgets.VBox([widget])
            #logging.info(f"Widget at index {index} encapsulated in a new VBox.")
            
        if index in self.vboxes:
            # Skip if the widget is already in the VBox
            logging.info(f"Skipping widget for index: {index}")
            return
            vbox = self.vboxes[index]
            vbox.children = (widget,)
            logging.info(f"Updated existing VBox at index {index}")
        elif self.empty_vboxes:
            # Reuse an empty VBox
            #logging.info(f"Adding widget for index: {index}")
            vbox = self.empty_vboxes.pop()
            vbox.children = (widget,)
            self.vboxes[index] = vbox
            #logging.info(f"Reused an empty VBox for index {index}")
        else:
            # Create a new VBox and add it to the layout
            #logging.info(f"Adding widget for index: {index}")
            vbox = widgets.VBox([widget])
            self.vboxes[index] = vbox
            #logging.info(f"Created a new VBox for index {index}")

        self._update_layout()

    def remove_widget(self, filter_row_index):
        """
        Remove the widget from the VBox associated with a filter row index.

        Args:
            filter_row_index (list[int]): The indices of the filter rows to remove.
        """
        logging.info(f"Removing widgets for indices: {filter_row_index}")
        if not isinstance(filter_row_index, list):
            filter_row_index = [filter_row_index]
        
        for index in filter_row_index:
            if index not in self.vboxes:
                raise ValueError(f"No VBox found for filter_row_index: {index}")

            vbox = self.vboxes[index]
            # Add an "Empty" label to the VBox
            vbox.children = (widgets.Label("Empty"),)
            self.empty_vboxes.append(vbox)  # Mark it as empty
            del self.vboxes[index]
            logging.info(f"Removed VBox at index {index} and marked it as empty.")

        self._update_layout()

    def reset(self):
        """
        Clear all VBoxes and reset the layout.
        """
        logging.info("Resetting VBoxManager...")
        self.vboxes.clear()
        self.empty_vboxes.clear()
        self.main_vbox.children = ()
        #self.logging.info_state()

    def get_vbox(self, filter_row_index):
        """
        Retrieve the VBox associated with a specific filter row index.

        Args:
            filter_row_index (int): The index of the filter row.

        Returns:
            VBox: The associated VBox.
        """
        if filter_row_index not in self.vboxes:
            raise ValueError(f"No VBox found for filter_row_index: {filter_row_index}")
        logging.info(f"Retrieved VBox for filter_row_index: {filter_row_index}")
        return self.vboxes[filter_row_index]

    def get_main_vbox(self):
        """
        Retrieve the main VBox managed by this class.

        Returns:
            VBox: The main VBox container.
        """
        return self.main_vbox

    def get_state(self):
        """
        Retrieve the current state of the VBoxManager.

        Returns:
            dict: A dictionary mapping grid identifiers to their VBoxes.
        """
        state = {index: {"vbox": vbox} for index, vbox in self.vboxes.items()}
        logging.info(f"Current VBoxManager state: {state}")
        return state

    def _update_layout(self):
        """
        Update the layout of the main VBox to ensure non-empty VBoxes appear in the order of their indices.
        """
        # Sort vboxes by index to ensure proper order
        sorted_indices = sorted(self.vboxes.keys())
        sorted_vboxes = [self.vboxes[index] for index in sorted_indices]

        # Combine sorted non-empty VBoxes with placeholders for empty slots
        self.main_vbox.children = tuple(sorted_vboxes + self.empty_vboxes)
        logging.info("Updated main VBox layout with widgets sorted by index.")
        #self.logging.info_state()



    def print_state(self):
        """
        logging.info the current indices and states of the managed VBoxes,
        including the indices of active and empty VBoxes.
        """
        logging.info("VBoxManager State:")
        logging.info("------------------")
        logging.info("Active VBoxes:")
        for index in sorted(self.vboxes.keys()):
            logging.info(f"  - Index: {index}, VBox: {self.vboxes[index]}")

        logging.info("\nEmpty VBoxes:")
        for empty_vbox in self.empty_vboxes:
            logging.info(f"  - VBox: {empty_vbox}")

        logging.info("\nMain VBox Layout:")
        for i, vbox in enumerate(self.main_vbox.children):
            if vbox in self.vboxes.values():
                logging.info(f"  - Position {i}: Active VBox (Index: {list(self.vboxes.keys())[list(self.vboxes.values()).index(vbox)]})")
            elif vbox in self.empty_vboxes:
                logging.info(f"  - Position {i}: Empty VBox")
            else:
                logging.info(f"  - Position {i}: Unknown VBox (not managed)")