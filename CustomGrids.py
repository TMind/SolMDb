import copy
import pandas as pd
try:
    import qgridnext as qgrid
except ImportError:
    import qgrid 
import ipywidgets as widgets
from IPython.display import display, HTML
from collections import OrderedDict

from DataSelectionManager import DataSelectionManager
from GlobalVariables import global_vars as gv
from GlobalVariables import rotate_suffix, GLOBAL_COLUMN_ORDER
from CustomCss import CSSManager
from MongoDB.DatabaseManager import DatabaseManager

# Inject custom CSS
style = """
<style>
    .custom-select-multiple option:checked {
        background-color: lightgreen !important;
        color: black !important;
    }
    .custom-select-multiple option.active {
        background-color: lightgreen !important;
    }
</style>
"""
display(HTML(style))

class TemplateGrid:

    def __init__(self):
        self.setup_widgets()  # Initialize and setup widgets for dynamic column selection        
        self.df = self.create_initial_dataframe()
        self.css_manager = CSSManager()        
        self.qgrid_filter = self.create_filter_qgrid()
        
    def create_filter_qgrid(self):
        
        column_definitions = copy.deepcopy(gv.all_column_definitions)
        
        # Set column widths
        for column in column_definitions.keys():            
            if column in gv.rotated_column_definitions.keys() : continue
            column_definitions[column]['width'] = len(column) * 11

        column_definitions['index'] = { 'width': 25 }
        column_definitions['Template Name'] = { 'width': 125 }
        column_definitions['type']['width'] = 50
        column_definitions['Name']['width'] = 200 
        
        
        
        # Create the qgrid widget
        qgrid_filter = qgrid.show_grid(self.df, column_definitions=column_definitions,
                                       grid_options={'forceFitColumns': False, 'filterable': False, 'sortable': False, 'editable' : True, 'defaultColumnWidth': 75, 'enableColumnReorder': True, 'minVisibleRows' : 15}, show_toolbar=True)
        qgrid_filter.layout = widgets.Layout(height='auto') 
        custom_css_class = self.css_manager.create_and_inject_css('Template', rotate_suffix)       
        self.css_manager.apply_css_to_widget(qgrid_filter,custom_css_class)
        
        # Binding the grid events
        qgrid_filter.on('row_added', self.grid_filter_on_row_added)
        qgrid_filter.on('row_removed', self.grid_filter_on_row_removed)
        qgrid_filter.on('cell_edited', self.grid_filter_on_cell_edit)
        qgrid_filter.on('selection_changed', self.on_row_selected)
        return qgrid_filter

    def setup_widgets(self):
        # Define column groups for selection
                
        cm_tags = gv.cm_manager.cm_tags or []
        
        self.column_groups = {
            'Base Data': ['Name', 'type', 'faction', 'forgebornId', 'cardTitles', 'FB2', 'FB3', 'FB4', 'Creatures', 'Spells', 'Exalt', 'Sum'],
            'Deck Data': ['registeredDate', 'UpdatedAt', 'pExpiry', 'digital', 'cardSetNo', 'tags', 'Betrayers', 'SolBinds'],
            'Fusion Data': ['Deck A', 'Deck B', 'CreatedAt', 'faction', 'crossFaction'],
            'Deck Stats': ['elo', 'level', 'xp', 'deckRank', 'deckScore'],
            'Fusion Stats' : ['CreatedAt', 'id' ],
            'Listing': ['price', 'owner'] ,
            'Statistical Data': ['A1', 'H1', 'A2', 'H2', 'A3', 'H3'],
            'CM Tags': cm_tags,            
            'Creatures': ['Beast', 'Dinosaur', 'Dragon', 'Elemental', 'Mage', 'Plant', 'BanishRobot', 'Scientist', 'BanishSpirit', 'Warrior', 'Zombie'],
            'Spells': ['Spell', 'Exalts'],             
            'De/Buffs' : ['Stat Buff', 'Attack Buff', 'Health Buff', 'Stat Debuff', 'Attack Debuff', 'Health Debuff'],
            'Utility' : ['Activate', 'Ready', 'Upgrade', 'Slay', 'Deploy', 'Reanimate'],
            'Effects' : ['Removal', 'Silence', 'Face Burn', 'FB Creature'],
            'Damage' : ['Destruction Others', 'Destruction Self', 'Self Damage' ],            
            'Keywords' : ['Breakthrough', 'Breakthrough Giver', 'Aggressive', 'Aggressive Giver', 'Defender', 'Defender Giver', 'Stealth', 'Stealth Giver', 'Armor', 'Armor Giver'],
            'Combos' : [
                'Free', 'BEAST Combo', 'DINOSAUR Combo', 'DRAGON Combo', 'ELEMENTAL Combo', 'MAGE Combo', 'PLANT Combo',
                'ROBOT Combo', 'SCIENTIST Combo', 'SPIRIT Combo', 'BANISH SPIRIT', 'WARRIOR Combo', 'ZOMBIE Combo',
                'MINION Combo', 'EXALT Combo', 'SPELL Combo', 'DEPLOY Combo', 'ARMOR Combo', 'ACTIVATE Combo',
                'DESTRUCTION Combo', 'DESTROY Combo', 'HEALING Combo', 'MOVEMENT Combo','REPLACE Combo',
                'READY Combo', 'REANIMATE Combo', 'SELFDAMAGE Combo','UPGRADE Combo', 'INCREASED A Combo' ],
            'Custom': ['White Fang', 'Last Winter', 'Spicy', 'Cool', 'Fun', 'Annoying']
        }

        # Widget to select column groups with label on top
        self.group_selector = widgets.SelectMultiple(
            options=list(self.column_groups.keys()), 
            description="", 
            layout=widgets.Layout(height='250px')
        )
        group_selector_label = widgets.Label('Groups:')
        group_selector_box = widgets.VBox([group_selector_label, self.group_selector])

        # Widget to display columns of the selected group with label on top
        self.columns_display = widgets.SelectMultiple(
            options=[], 
            description="", 
            layout=widgets.Layout(height='250px')
        )

        # Widget to select extensions with label on top
        self.extension_selector = widgets.SelectMultiple(
            options=['Tag', 'Synergy', 'Combo'], 
            description="", 
            layout=widgets.Layout(height='auto')
        )
        extension_selector_label = widgets.Label('Column Extensions:')
        extension_selector_box = widgets.VBox([extension_selector_label, self.extension_selector])        
        
        # Apply the custom CSS class to the widget
        self.columns_display.add_class('custom-select-multiple')

        columns_display_label = widgets.Label('Columns:')
        columns_display_box = widgets.VBox([columns_display_label, self.columns_display])

        # Apply button to apply the current selection state
        self.apply_button = widgets.Button(description="Apply Selection")
        self.apply_button.on_click(self.apply_selection)

        # Toggle button to select/deselect all columns
        self.select_all_button = widgets.Button(description="Select All")
        self.select_all_button.on_click(self.toggle_select_all)
        
        # Save and Restore buttons
        self.save_button = widgets.Button(description='Save')
        self.save_button.on_click(self.save_template_grid)

        self.restore_button = widgets.Button(description='Restore')
        self.restore_button.on_click(self.restore_template_grid)

        button_box_label = widgets.Label('Actions:')
        button_box = widgets.VBox([button_box_label, self.select_all_button, self.apply_button, self.save_button, self.restore_button])

        # Layout widgets horizontally
        self.control_ui = widgets.HBox([
            group_selector_box, 
            columns_display_box,
            widgets.VBox([extension_selector_box,button_box])
        ])

        # Observe changes in columns_display to update the button text
        self.columns_display.observe(self.update_select_all_button, 'value')

        # Observe changes in group selector to update columns display
        self.group_selector.observe(self.update_columns_display, 'value')
        
        # Observe changes in extension selector to update columns display
        self.extension_selector.observe(self.update_columns_display, 'value')

    def save_template_grid(self, _):
        """Save the current state of the template grid to MongoDB."""
        
        # Convert DataFrame to a list of dictionaries
        df = self.qgrid_filter.get_changed_df()
        data = df.to_dict(orient='records')

        try:
            # Insert the new data
            #global_vars.myDB.upsert({'name': 'TemplateGrid', 'data': data})
            myDB = gv.myDB or DatabaseManager(gv.username)
            myDB.upsert(
                collection_name='User Data',  # Assuming 'TemplateGrid' is the collection name
                identifier={'name': 'TemplateGrid'},  # Identifier for the document
                data={'data': data}  # The data to be upserted
            )
            #print("Template grid saved to MongoDB.")
        except Exception as e:
            print(f"An error occurred while saving the template grid: {e}")
            
    def restore_template_grid(self, _):
        """Restore the previously saved state of the template grid from MongoDB."""
        try:
            # Retrieve the data from MongoDB
            data = gv.myDB.find_one('User Data', {'name': 'TemplateGrid'})
            if not data:
                with gv.out_debug:
                    print("No data found in MongoDB.")
                return
            
            # Extract the data records
            data_records = data.get('data', [])
            #print("Data retrieved from MongoDB:")
            #print(data_records)

            if data_records:
                # Remove the '_id' field from each record if present
                for record in data_records:
                    if '_id' in record:
                        del record['_id']

                # Convert the list of dictionaries back to a DataFrame
                df = pd.DataFrame(data_records)
                
                # Check the restored DataFrame
                #print("Restored DataFrame:")
                #print(df)

                # Set the DataFrame to the qgrid widget
                self.qgrid_filter.df = df
                self.qgrid_filter.change_selection(rows=[0])  # Re-select the first row
                #print("Template grid restored from MongoDB.")
            else:
                with gv.out_debug:
                    print("No data records found to restore.")  
        except Exception as e:
            print(f"An error occurred while restoring the template grid: {e}")
            
    def apply_selection(self, _):
        """Apply the current column selection to the template grid."""
        # Get the currently selected row in the template grid
        selected_indices = self.qgrid_filter.get_selected_rows()
        
        if selected_indices:
            selected_index = selected_indices[0]  # Assuming single selection

            # Get the DataFrame from the grid and update the values in the selected row
            df = self.qgrid_filter.get_changed_df()
            
            # Apply the current selection and non-selection from columns_display
            for column in self.columns_display.options:
                df.at[selected_index, column] = column in self.columns_display.value
            
            # Update the DataFrame in the grid
            self.qgrid_filter.df = df
            
            # Mimic an event-like dictionary for the update_columns_display call
            event_like = {'new': self.group_selector.value}
            
            # Ensure the column selection reflects the updated state
            self.update_columns_display(event_like)
            
            # Re-select the edited row in the template grid
            self.qgrid_filter.change_selection(rows=[selected_index])
            
            self.update_data_selection_sets(event_like, self.qgrid_filter)
            

    def update_select_all_button(self, change):
        """Update the text of the select all button based on the selection."""
        if set(self.columns_display.options) == set(self.columns_display.value):
            self.select_all_button.description = "Deselect All"
        else:
            self.select_all_button.description = "Select All"

    def toggle_select_all(self, button):
        """Toggle the selection of all columns in the columns_display widget and update the button text."""
        if set(self.columns_display.options) == set(self.columns_display.value):
            # If all are selected, deselect all
            self.columns_display.value = ()
            button.description = "Select All"
        else:
            # Otherwise, select all
            self.columns_display.value = tuple(self.columns_display.options)
            button.description = "Deselect All"

        # Do not apply the selection to the template grid here. Just update the UI.
        # The actual changes will be applied when the apply_button is clicked.
            
    def get_ui(self):
        # Display widgets and the qgrid together
        ui = widgets.VBox([self.control_ui, self.qgrid_filter])
        return ui

    def update_visible_columns(self, change):
        selected_groups = self.group_selector.value
        columns_to_toggle = [col for group in selected_groups for col in self.column_groups[group]]
        # Adjust the visible columns based on the selected groups
        self.qgrid_filter.column_options = {col: {'visible': True} for col in columns_to_toggle}


    def create_initial_dataframe(self):
        rows = []

        for template_name, template_set in gv.data_selection_sets.items():
            row = template_set.copy()
            row['Template Name'] = template_name
            rows.append(row)

        template_df = pd.DataFrame(rows)
        
        # Align columns to match the GLOBAL_COLUMN_ORDER        
        aligned_columns = ['Template Name'] + [col for col in GLOBAL_COLUMN_ORDER if  col in template_df.columns and col != 'Template Name']
        #template_df = template_df[columns]
        template_df = template_df.reindex(columns=aligned_columns)
        template_df = template_df.infer_objects()

        bool_columns = template_df.columns.difference(['Template Name', 'type'])
        template_df[bool_columns] = template_df[bool_columns].fillna(False).astype(bool)
        
        return template_df

    def update_columns_display(self, event):
        """Update the column display based on the selected groups."""
        #selected_groups = event['new']
        selected_groups = self.group_selector.value
        
        #print(f"Selected groups: {selected_groups}")
        if selected_groups:
            all_columns = []
            for group in selected_groups:
                if group in self.column_groups:
                    all_columns.extend(self.column_groups[group])
                else:
                    print(f"Warning: Group '{group}' not found in column groups.")
            
            # Remove duplicates while preserving the order using OrderedDict            
            unique_columns = [col for col in GLOBAL_COLUMN_ORDER if col in list(OrderedDict.fromkeys(all_columns))]
            
            # Get the order of columns as they appear in the selected row
            selected_indices = self.qgrid_filter.get_selected_rows()

            if selected_indices:
                selected_index = selected_indices[0] if isinstance(selected_indices, list) else selected_indices
            
                if 0 <= selected_index < len(self.qgrid_filter.df):
                    selected_row = self.qgrid_filter.df.iloc[selected_index]
                    
                    additional_columns = []
                    for extension in self.extension_selector.value:            
                        additional_columns.append([f"{selected_column} {extension}" for selected_column in self.columns_display.value if f"{selected_column} {extension}" in self.qgrid_filter.df.columns])
                        
                    # Maintain the order of columns as they appear in the selected row
                    ordered_columns = [col for col in selected_row.index if col in unique_columns]
                    ordered_columns.extend(additional_columns)
                    self.columns_display.options = ordered_columns

                    # Update the active columns based on the selected row
                    valid_active_columns = [col for col in ordered_columns if selected_row[col] == True]
                    self.columns_display.value = tuple(valid_active_columns)
                    
                    # Update the color of the selected options
                    self.update_columns_option_colors(valid_active_columns)
                else:
                    self.columns_display.value = ()
            else:
                self.columns_display.value = ()
        else:
            self.columns_display.options = []
            self.columns_display.value = ()

    def update_group_selector_based_on_active_columns(self, active_columns):
        """Updates the group selector based on the active columns in the selected row."""
        active_groups = []
        for group, group_columns in self.column_groups.items():
            if any(col in active_columns for col in group_columns):
                active_groups.append(group)
        
        # Update the group selector to reflect the active groups
        self.group_selector.value = tuple(active_groups)

    def update_columns_option_colors(self, active_columns):
        """Update the color of the options based on whether they are active."""
        options_html = []
        for option in self.columns_display.options:
            if option in active_columns:
                options_html.append(f"<option class='active-column'>{option}</option>")
            else:
                options_html.append(f"<option>{option}</option>")

        # Update the HTML widget value to reflect the new colors
        self.columns_display.value = tuple(active_columns)

    def grid_filter_on_row_removed(self, event, widget):
        if 0 in event['indices']:
            df = self.create_initial_dataframe()
            widget.df = pd.concat([df, widget.get_changed_df()], ignore_index=True)
            event['indices'].remove(0)        
        
        self.update_data_selection_sets(event, widget)

    def grid_filter_on_row_added(self, event, widget):
        new_row_index = event['index']
        df = widget.get_changed_df()
        
        for column in df.columns:
            if column != 'Template Name':
                df.at[new_row_index, column] = False
                df.at[new_row_index, 'Template Name'] = 'New Template'
            widget.df = df

            self.update_data_selection_sets(event, widget)
            

    def grid_filter_on_cell_edit(self, event, widget):    
        row_index, column_index = event['index'], event['column']        
        #print(f"Cell edit event: {event}")
        
        # Get the current grid's DataFrame
        df = widget.get_changed_df()
        
        # Update the DataFrame with the new value
        df.loc[row_index, column_index] = event['new']
        widget.df = df
        
        # Ensure the group and column selection widgets are updated
        #self.update_columns_display({'new': self.group_selector.value})
        self.update_group_selector_based_on_active_columns(df.columns[df.loc[row_index] == True])
        
        #print(f"Selected row index: {row_index}, column index: {column_index}")
        # Re-select the edited row in the template grid
        self.qgrid_filter.change_selection([row_index])
        
        # Update the data selection sets to reflect the new values
        self.update_data_selection_sets(event, widget)
        
    def on_row_selected(self, event, qgrid_widget):
        try:
            selected_indices = event['new']
            #print(f"Selected indices: {selected_indices}")
            #print(f"DataFrame index: {qgrid_widget.df.index.tolist()}")

            if selected_indices is None or len(selected_indices) == 0:
                if gv.out_debug:
                    with gv.out_debug:
                        print("No row is selected.")
                return

            selected_index = selected_indices[0] if isinstance(selected_indices, list) else selected_indices

            if not (0 <= selected_index < len(qgrid_widget.df)):
                if gv.out_debug:
                    with gv.out_debug:
                        print(f"Invalid index selected: {selected_index}. DataFrame length: {len(qgrid_widget.df)}")
                return

            selected_row = qgrid_widget.df.iloc[selected_index]
            #print(f"Selected row data: {selected_row}")

            # Identify all active columns directly from the selected row
            active_columns = [col for col in selected_row.index if selected_row[col] == True]
            #print(f"Active columns: {active_columns}")

            # Update the group selector based on the active columns
            self.update_group_selector_based_on_active_columns(active_columns)

        except KeyError as ke:
            print(f"KeyError accessing DataFrame: {ke}")
        except IndexError as ie:
            print(f"IndexError: Selected index {selected_index} is out of range.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def update_data_selection_sets(self, event, widget):
        print(f"UpdateDatatSelectionSets called with {event}")
        template_df = self.qgrid_filter.get_changed_df()
        gv.data_selection_sets = {template_df.loc[template]['Template Name']: template_df.loc[template].index[template_df.loc[template] == True].tolist() for template in template_df.index}
        
        DataSelectionManager.update_data(event, widget)
        if gv.out_debug:
            with gv.out_debug:
                print(f"Data selection sets updated: {gv.data_selection_sets}")
            
            
class ActionToolbar:
    def __init__(self, button_configs=None):
        """
        Initialize the floating toolbar with a list of buttons.
        
        :param buttons: List of ipywidgets buttons to include in the toolbar.
        """
        if button_configs is None:
            # Default buttons if none are provided
            button_configs = {
                "Authenticate": {"description": "Login", "button_style": 'info'},
                "Solbind": {"description": "Solbind", "button_style": 'danger'},
                "Rename": {"description": "Rename", "button_style": 'warning'},
                "Export": {"description": "Export", "button_style": 'info'}
            }
        
        self.buttons = {}
        
        # Initialize buttons based on provided or default configurations
        for name, config in button_configs.items():
            self.buttons[name] = widgets.Button(description=config.get("description", name), button_style=config.get("button_style", ''))

        # Create a horizontal box (HBox) to hold the buttons
        self.toolbar = widgets.HBox(list(self.buttons.values()))
        
        # Create a custom widget container with floating style
        self.action_toolbar = widgets.Box([self.toolbar], layout=widgets.Layout(width='auto'))
        
    def add_button(self, button_name, description, button_style='', callback_function=None):
        """
        Adds a button to the toolbar.
        
        :param button_name: The name of the button (used as the key in the dictionary).
        :param description: The text displayed on the button.
        :param button_style: Optional style for the button (e.g., 'info', 'danger', etc.).
        :param callback_function: Optional callback function to attach to the button.
        """
        if button_name not in self.buttons:
            # Create the new button
            new_button = widgets.Button(description=description, button_style=button_style)
            self.buttons[button_name] = new_button
            
            # Assign the callback function if provided
            if callback_function:
                new_button.on_click(callback_function)
            
            # Update the toolbar layout
            self.toolbar.children = list(self.buttons.values())
        else:
            raise ValueError(f"Button '{button_name}' already exists in the toolbar.")

    def assign_callback(self, button_name, callback_function):
        """
        Assigns a callback function to a button in the toolbar.
        
        :param button_name: The name of the button (string) to assign the callback to.
        :param callback_function: The function to call when the button is clicked.
        """
        if button_name in self.buttons:
            self.buttons[button_name].on_click(callback_function)
        else:
            raise ValueError(f"Button {button_name} not found in the toolbar.")
        
    def get_ui(self):
        """Return the action toolbar UI."""
        return self.action_toolbar