import ipywidgets as widgets

class EnhancedSelectMultiple(widgets.VBox):
    def __init__(self, *args, **kwargs):
        # Extract options from kwargs
        options = kwargs.pop('options', [])
        super().__setattr__('_original_options', sorted(options, key=lambda x: x.lower()))  # Sort options alphabetically

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
        super().__init__([self.toggle_button, self.search_widget, self.select_widget], layout=layout, *args)

        # Mark initialization as complete
        super().__setattr__('_initialized', True)

    @property
    def options(self):
        return self._original_options

    @options.setter
    def options(self, new_options):
        print(f"Setting new options: {new_options}")
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

    def __getattr__(self, name):
        # Only delegate attribute access if select_widget is already set
        if name in ['_original_options', 'select_widget', 'search_widget', 'toggle_button'] or name not in self.__dict__:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return getattr(self.select_widget, name)

    def __setattr__(self, name, value):
        # During initialization, avoid delegation until select_widget is set
        if '_initialized' not in self.__dict__ or name in ['_original_options', 'select_widget', 'search_widget', 'toggle_button']:
            super().__setattr__(name, value)
        else:
            setattr(self.select_widget, name, value)
