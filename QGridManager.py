from ast import Global
import datetime
from IPython.display import display
from icecream import ic

# Modules used by both classes
import qgrid
import pandas as pd
import ipywidgets as widgets

import GlobalVariables as gv

class QGridManager:
    EVENT_DF_STATUS_CHANGED = 'df_status_changed'

    def __init__(self):
        self.grids = {}  # Stores the grid widgets and their interactive components
        self.callbacks = {}  # Stores the event listeners for the grids
        self.relationships = {}  # Stores the relationships between the grids

    def register_callback(self, event_name, callback, identifier=None):
        if identifier is None:
            for identifier in self.grids:
                self.register_callback(event_name, callback, identifier)
        else:
            self._register_callback_for_identifier(identifier, event_name, callback)

    def _register_callback_for_identifier(self, identifier, event_name, callback):
        if identifier not in self.callbacks:
            self.callbacks[identifier] = {}
        if event_name not in self.callbacks[identifier]:
            self.callbacks[identifier][event_name] = []
        self.callbacks[identifier][event_name].append(callback)

    def trigger(self, event_name, *args, **kwargs):
        for identifier in self.callbacks:
            if event_name in self.callbacks[identifier]:
                for callback in self.callbacks[identifier][event_name]:
                    callback(*args, **kwargs)


    def add_grid(self, identifier, df, options={}, dependent_identifiers=[]):
        """Create a qgrid widget with interactive column selection."""
        grid_widget = qgrid.show_grid(df,
                                      column_options=options.get('col_options', {}),
                                      column_definitions=options.get('col_defs', {}),
                                      grid_options={'forceFitColumns': False, 'enableColumnReorder': True},
                                      show_toolbar=False)

        # Initialize an empty toggle DataFrame for column visibility
        toggle_df = pd.DataFrame(columns=['Visible'])  # No columns initially
        toggle_grid = qgrid.show_grid(toggle_df, 
                                      show_toolbar=False, 
                                      grid_options={'forceFitColumns': True,  'filterable': False, 'sortable' : False})  # Force the grid to fit the width of its container
        toggle_grid.layout = widgets.Layout(height='65px')  # Set the height of the toggle grid

        # Function to handle changes in toggle grid
        def on_toggle_change(event, qgrid_widget):
            #print(f'on_toggle_change triggered, event: {event}')
            # Get current toggle state
            toggled_df = toggle_grid.get_changed_df()
            visible_columns = [col for col in toggled_df.columns if toggled_df.loc['Visible', col]]            

            #print(f'on_toggle_change() : visible columns = {visible_columns}')
            # Use the filtered DataFrame to update the DataFrame in the main grid

            grid_info = self.grids[identifier]
            if grid_info:
                if not grid_info['df_versions']['changed'].empty: 
                    grid_widget.df = grid_info['df_versions']['changed'][visible_columns].copy()
                elif not grid_info['df_versions']['filtered'].empty:
                    grid_widget.df = grid_info['df_versions']['filtered'][visible_columns].copy()
                else:
                    grid_widget.df = grid_info['df_versions']['default'][visible_columns].copy()


            # Set Status of Change 
            grid_info['df_status']['current'] = 'filtered'
            grid_info['df_status']['last_set']['filtered'] = datetime.datetime.now()
            self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid_info['df_status'])

        def on_filter_change(event, qgrid_widget):
            # Get the changed Dataframe
            changed_df = grid_widget.get_changed_df()

            # Store the changed DataFrame
            self.grids[identifier]['df_versions']['changed'] = changed_df.copy()

            # Update the toggle grid 
            print(f'on_toggle_change() : Updating toggle grid for {identifier}' )
            self.update_toggle_df(changed_df, identifier)

            # Set Status of Change 
            grid_info = self.grids[identifier]
            grid_info['df_status']['current'] = 'changed'
            grid_info['df_status']['last_set']['changed'] = datetime.datetime.now()            
            self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid_info['df_status'])

            # Synchronize the dependent widgets
            #self.synchronize_widgets(identifier)
        
        # to the toggle grid
        toggle_grid.on('cell_edited', on_toggle_change)

        # Attach event handlers 
        grid_widget.on('filter_changed', on_filter_change)
        grid_widget.on('filter_changed', self.update_visible_columns)

        # Store grid info
        self.grids[identifier] = {
            'main_widget': grid_widget,
            'toggle_widget': toggle_grid,
            'df_versions': {
                'default': df.copy(),
                'filtered': df.copy(),
                'changed': df.copy()
            },
            'df_status': {
                'current': 'default',
                'last_set': {
                    'default': datetime.datetime.now(),
                    'filtered': None,
                    'changed': None
                }
            }
        }

        # Store the relationships 
        self.relationships[identifier] = dependent_identifiers
        return grid_widget, toggle_grid

    def get_default_data(self, identifier):
        """Get the 'default' version of the DataFrame for a specified qgrid widget."""
        grid_info = self.grids.get(identifier)
        if grid_info:
            return grid_info['df_versions']['default']
        else:
            return None

    def set_default_data(self, identifier, new_data):
        """Set the 'default' version of the DataFrame for a specified qgrid widget."""
        grid_info = self.grids.get(identifier)
        if grid_info:
            grid_info['df_versions']['default'] = new_data.copy()
            # Update the main widget's DataFrame
            grid_info['main_widget'].df = new_data
            toggle_df = pd.DataFrame([True] * len(new_data.columns), index=new_data.columns, columns=['Visible']).T
            grid_info['toggle_widget'].df = toggle_df
            
            # Set Status of Change 
            grid_info['df_status']['current'] = 'default'
            grid_info['df_status']['last_set']['default'] = datetime.datetime.now()
            self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid_info['df_status'])


    # Updating the DataFrame
    def update_data(self, identifier, new_data):
        """Update the data in a specified qgrid widget and adjust toggle grid accordingly."""
        grid_info = self.grids.get(identifier)
        if grid_info:
            # Update the filterd DataFrame
            #print(f'update_data() : Updating filtered data for {identifier}')
            grid_info['df_versions']['filtered'] = new_data.copy()
            # Update the main widget's DataFrame
            #print(f'update_data() : Updating main grid for {identifier}' )
            grid_info['main_widget'].df = new_data.copy()
            # Update the toggle widget , but keep the original setting 
            #print(f'update_data() : Updating toggle grid for {identifier}' )
            self.update_toggle_df(new_data, identifier)

            grid_info['df_status']['current'] = 'filtered'
            grid_info['df_status']['last_set']['filtered'] = datetime.datetime.now()
            self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid_info['df_status'])
            self.synchronize_widgets(identifier)
            

    def update_toggle_df(self, df, identifier):
        """
        Update the toggle DataFrame for a specific grid.

        Args:
            df (pandas.DataFrame): The new DataFrame containing the data.
            identifier (str): The identifier of the grid.

        Returns:
            None
        """
        grid_info = self.grids.get(identifier)
        if grid_info:
            # Create a new DataFrame with the same structure as the new data            
            new_toggle_df = pd.DataFrame({column: [True] for column in df.columns}, index=['Visible'])
            # Get the current toggle_df
            current_toggle_df = grid_info['toggle_widget'].get_changed_df()
            grid_info['toggle_widget'].df = new_toggle_df

            # Iterate over the columns of the current_toggle_df
            for column in current_toggle_df.columns:
                if column in new_toggle_df.columns:
                    # If the column exists in the new_toggle_df, copy the value
                    if 'Visible' in current_toggle_df.index:
                        grid_info['toggle_widget'].edit_cell('Visible', column, current_toggle_df.loc['Visible', column])                            
                else:
                    # If the column does not exist in the new_toggle_df, add it with the value False
                    new_toggle_df[column] = False
                    grid_info['toggle_widget'].edit_cell('Visible', column, False)

    # Visibility of columns / Dropping columns
    def update_visible_columns(self, event, widget):
        ic('Updating visible columns', widget)
        zero_width_columns = []   

        # Function to check if any value in the column is not an empty string with regards to the changed_df of the qgrid widget
        def check_column_values(column, changed_df):
            # Check if the column exists in the DataFrame
            if column in changed_df.columns:  return changed_df[column].ne('').any()      
            else:                             return False

        # Analyze changed DataFrame for updates
        changed_df = widget.get_changed_df()
        for column in changed_df.columns:  
            # Check if column values are not just empty strings
            if not check_column_values(column, changed_df):
                zero_width_columns.append(column)
                changed_df.drop(column, axis=1, inplace=True)

        # Update the toggle grid
        ic('Zero width columns', zero_width_columns)
        if len(zero_width_columns) > 0:            
            for grid_id, grid_info in self.grids.items():
                ic('Is it grid?', grid_id)
                if grid_info['main_widget'] == widget:
                    ic('It is grid' , grid_id)
                    toggle_grid = grid_info['toggle_widget']
                    for column in toggle_grid.df.columns:
                        ic('Checking',column)
                        toggle_grid.df[column] = column in changed_df.columns
                        ic(toggle_grid.df[column])
                    # Update the toggle widget
                    toggle_grid.df = toggle_grid.df    
            
            widget.df = changed_df

    def display_grid_with_controls(self, identifier):
        """Display the qgrid widget with its column selectors."""
        grid_info = self.grids.get(identifier)
        if grid_info:
            display(widgets.VBox([grid_info['toggle_widget'], grid_info['main_widget']]))


    # Updating dependent widgets 

    def synchronize_widgets(self, master_identifier):
        ic('Synchronizing widgets', master_identifier)
        # Get the DataFrame from the master widget
        master_widget = self.grids[master_identifier]['main_widget']
        master_df = master_widget.get_changed_df()

        # Update the DataFrame in the dependent widgets
        for dependent_identifier in self.relationships[master_identifier]:
            # Start with the 'default' version of the DataFrame
            dependent_df = self.grids[dependent_identifier]['df_versions']['default']

            # Filter the DataFrame based on the index of the master widget
            filtered_df = dependent_df[dependent_df.index.isin(master_df.index)]

            # Set the filtered DataFrame as the DataFrame of the dependent widget
            dependent_widget = self.grids[dependent_identifier]['main_widget']
            dependent_widget.df = filtered_df.copy()

            # Update the 'filtered' version of the DataFrame
            self.grids[dependent_identifier]['df_versions']['filtered'] = filtered_df.copy()

            # Update the visible columns of the dependent grid
            self.update_visible_columns(None, dependent_widget)

    def on(self, identifier, event_name, handler_func):
        """Add an event listener to a qgrid widget."""
        grid_info = self.grids.get(identifier)
        if grid_info and 'main_widget' in grid_info:
            grid_info['main_widget'].on(event_name, handler_func)


class FilterGrid:
    def __init__(self, update_decks_display):
        self.update_decks_display = update_decks_display
        self.df = self.create_initial_dataframe()
        self.qgrid_filter = self.create_filter_qgrid()
        #selection_box, selection_widgets = self.create_selection_box()
        self.selection_box, self.selection_widgets  = self.create_selection_box()
        #self.selection_widgets = selection_widgets

    def create_filter_qgrid(self):
        # Create a qgrid widget for the data from the selection widgets
        qgrid_filter = qgrid.show_grid(self.df, grid_options={'forceFitColumns' : False, 'minVisibleRows' : 4, 'maxVisibleRows':5, 'enableColumnReorder':False} , 
                                       column_definitions={'index' : {'width' : 50}, 'op1' : {'width' : 50}, 'op2' : {'width' : 50}} ,
                    
                                       show_toolbar=True)    
        qgrid_filter.layout = widgets.Layout(height='auto%')  
        qgrid_filter.on('row_added', self.grid_filter_on_row_added)           
        qgrid_filter.on('row_removed', self.grid_filter_on_row_removed)   
        qgrid_filter.on('cell_edited', self.on_cell_edit)             
        return qgrid_filter

    @staticmethod
    def create_initial_dataframe():
        return pd.DataFrame({
            'Modifier': [''],
            'op1': [''],
            'Creature': [''],
            'op2': [''],
            'Spell': [''], 
            'Active': [False]
        })
    
    def grid_filter_on_row_removed(self, event, widget):        
        # Check if index 0 is in the indices
        if 0 in event['indices']:
            df = self.create_initial_dataframe()
            widget.df = pd.concat([df, widget.get_changed_df()], ignore_index=True)
            # Remove index 0 from the indices
            event['indices'].remove(0)
    
        # If there are any indices left, update the display
        if event['indices']:
            # Create the active rows DataFrame
            active_rows = widget.df[widget.df['Active'] == True]
            self.update_decks_display({'new': active_rows, 'old': None, 'owner': 'filter'})

    def grid_filter_on_row_added(self, event, widget):          
        print(f"Row added at index {event['index']}")
        new_row_index = event['index']
        df = widget.get_changed_df()                           
        for column in df.columns:
            if column == 'Active':
                df.loc[new_row_index, column] = self.selection_widgets[column].value
                print(f"Active value: {df.loc[new_row_index, column]}")
            else:
                df.loc[new_row_index, column] = ', '.join(self.selection_widgets[column].value) if isinstance(self.selection_widgets[column].value, (list, tuple)) else self.selection_widgets[column].value
                print(f"Value for {column}: {df.loc[new_row_index, column]}")
        widget.df = df
        display(widget.df)
        if widget.df.loc[new_row_index, 'Active']:            
            print(f"Calling update_decks_display from grid_filter_on_row_added")                                
            self.update_decks_display({'new': new_row_index, 'old': None, 'owner': 'filter'})
    
    def on_cell_edit(self, event, widget):        
        #print(f"Old value: {event['old']} -> New value: {event['new']}")
        row_index = event['index']
        column_index = event['column']                        
        # Set the value for the cell
        widget.df.loc[row_index, column_index] = event['new']
        #print(f"Cell edited at row {row_index}, column {column_index}")
        #print(f"Final value in cell = {widget.df.loc[row_index, column_index]}")
        
        if widget.df.loc[row_index, 'Active']:
            # Filter is active , so it needs to update the list
            #print(f"Calling update_decks_display from on_cell_edit")   
            self.update_decks_display({'new': row_index, 'old': None, 'owner': 'filter'})        

        elif column_index == 'Active':
            # Filter is inactive , so it needs to update the list
            #print(f"Calling update_decks_display from on_cell_edit")   
            self.update_decks_display({'new': row_index, 'old': None, 'owner': 'filter'})

    def update_selection_content(self, change): 
        if change['name'] == 'value' and change['new'] != change['old']:
            print(f"Updating selection content {gv.username} = {change}")
            for cardType in ['Modifier', 'Creature', 'Spell']:
                print(f"Updating widget for {cardType}")
                widget = self.selection_widgets[cardType]
                widget.options = [''] + get_cardType_entity_names(cardType)

    def create_cardType_names_selector(self, cardType):    
        cardType_entity_names = [''] + get_cardType_entity_names(cardType)    
        cardType_name_widget = widgets.SelectMultiple(
            options=cardType_entity_names,
            description='',        
            #layout=widgets.Layout(width="200px"),
            value=()
        )
        return cardType_name_widget

    def create_selection_box(self):
        selection_widgets = {}

        # Selection Widgets 
        label_widgets = {}
        selection_items = {}
        for cardTypesString in ['Modifier', 'Creature' , 'Spell']:        
            widget = self.create_cardType_names_selector(cardTypesString)
            if cardTypesString == 'Modifier':
                label = widgets.Label(value='( ' + cardTypesString)
            elif cardTypesString == 'Creature':
                label = widgets.Label(value=cardTypesString + ' )')
            else:
                label = widgets.Label(value=cardTypesString)
            selection_widgets[cardTypesString] = widget
            label_widgets[cardTypesString] = label
            selection_items[cardTypesString] = widgets.VBox([label, widget], layout=widgets.Layout(align_items='center'))
            #selection_items.append(widgets.VBox([label, widget], layout=widgets.Layout(align_items='center')))

        # Operator Widgets + Active Widget
        operator1_widget = widgets.Dropdown(
            options=['+', 'AND', 'OR', ''], 
            description='', 
            layout=widgets.Layout(width='60px'),  # Adjust the width as needed
            value='OR'
        )        
        operator2_widget = widgets.Dropdown(
            options=['AND', 'OR', ''], 
            description='', 
            layout=widgets.Layout(width='60px'),  # Adjust the width as needed
            value='OR'
        )
        active_widget = widgets.Checkbox(value=True, description='Activated')        
        
        # Operator Labels + Active Label
        operator1_label = widgets.Label(value='Operator')
        operator2_label = widgets.Label(value='Operator')
        active_label = widgets.Label(value='Active')

        selection_widgets['op1'] = operator1_widget
        selection_widgets['op2'] = operator2_widget
        selection_widgets['Active'] = active_widget
        #label_widgets['op1']= operator1_label
        #label_widgets['op2'] = operator2_label
        #label_widgets['Active'] = active_label
        
        selection_items['op1'] = widgets.VBox([operator1_label, operator1_widget], layout=widgets.Layout(align_items='center'))
        selection_items['op2'] = widgets.VBox([operator2_label, operator2_widget], layout=widgets.Layout(align_items='center'))
        selection_items['Active'] = widgets.VBox([active_label, active_widget], layout=widgets.Layout(align_items='center'))
                        
        selection_box = widgets.HBox([selection_items[name] for name in ['Modifier', 'op1', 'Creature', 'op2' ,'Spell', 'Active']])
        
        #selection_widgets_list = [selection_widgets[name] for name in ['Modifier', 'op1', 'Creature', 'op2' ,'Spell', 'Active']]
        #label_widgets_list = [label_widgets[name] for name in ['Modifier', 'op1', 'Creature', 'op2' ,'Spell', 'Active']]
        return selection_box, selection_widgets #, label_widgets_list
    
    def get_changed_df(self):
        return self.qgrid_filter.get_changed_df()

    def get_widgets(self):        
        return self.selection_box, self.qgrid_filter
    


def get_cardType_entity_names(cardType):

    #print(f"Getting entity names for {cardType}")
    cardType_entities  = gv.commonDB.find('Entity', {"attributes.cardType": cardType})       
    cardType_entities_names = [cardType_entity['name'] for cardType_entity in cardType_entities]    
    ic(cardType_entities_names)

    # Get cardnames from the database
    def get_card_title(card):
        if card: 
            if 'title' in card:
                return card['title']
            elif 'name' in card:
                return card['name']
            else:
                print(f"Card {card} has no title/name")
                return ''
        else:
            print(f"Card {card} not found")
            return ''

    cards = gv.myDB.find('Card', {})
    cardNames = [get_card_title(card) for card in cards]

    # Filter all strings where the entity name is a substring of any card name
    cardType_entities_names = [cardType_entity for cardType_entity in cardType_entities_names if any(cardType_entity in cardName for cardName in cardNames)]

    #Sort cardType_entities_names
    cardType_entities_names.sort()

    #print(f"Entity names for {cardType}: {cardType_entities_names}")
    return cardType_entities_names