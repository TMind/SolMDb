from unittest.mock import DEFAULT
import pandas as pd
import ipywidgets as widgets
import logging
import re

try:
    import qgridnext as qgrid
except ImportError:
    import qgrid

from GlobalVariables import global_vars as gv
from GlobalVariables import DEFAULT_FILTER
from MyWidgets import EnhancedSelect
from MongoDB.DatabaseManager import DatabaseManager
from DataSelectionManager import Observable

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class FilterGrid:
    """
    Manages the grid for filtering data based on user-defined criteria.
    Acts as the central widget for filter criteria.
    """
    def __init__(self, function_refresh):
        """
        Initializes a new instance of the FilterGrid class.
        
        Args:
            function_refresh (function): The function to call when the filter grid is updated.
        """
        self.observable = Observable()  # Delegated observer functionality.
        self.refresh_function = function_refresh
        self.df = self.create_initial_dataframe()
        self.qgrid_filter = self.create_filter_qgrid()        
        self.selection_box, self.selection_widgets, self.toggle_buttons_dict = self.create_selection_box()
        # DataSelectionManager.register_observer(self.update)  # Uncomment if needed

    def add_filter_observer(self, observer_id, observer_callback):
        """
        Registers an observer to be notified when the filter changes.
        
        Args:
            observer_id (str): The identifier for the observer.
            observer_callback (function): A callback that accepts a filter dictionary.
        """
        logger.info(f"FilterGrid::add_filter_observer() - Adding observer with ID: {observer_id}")
        self.observable.add_observer(observer_id, observer_callback)

    def notify_filter_observers(self, event, grid_id=None):
        """
        Notifies all registered observers with the current filter criteria.
        """
        if grid_id: 
            self.observable.notify_observer_by_id(grid_id, event)
        else:
            self.observable.notify_observers(event)

    def create_filter_qgrid(self):
        """
        Creates the filter qgrid.
        
        Returns:
            qgrid.QGridWidget: The qgrid widget for filtering.
        """        
        qgrid_filter = qgrid.show_grid(
            self.df,
            grid_options={
                'forceFitColumns': False,
                'minVisibleRows': 4,
                'maxVisibleRows': 5,
                'enableColumnReorder': False
            },
            column_definitions={'index': {'width': 50}},
            show_toolbar=True
        )
        qgrid_filter.layout = widgets.Layout(height='auto')
        qgrid_filter.on('row_added', self.grid_filter_on_row_added)
        qgrid_filter.on('row_removed', self.grid_filter_on_row_removed)
        qgrid_filter.on('cell_edited', self.grid_filter_on_cell_edit)
        
        return qgrid_filter

    @staticmethod
    def create_initial_dataframe():
        """
        Creates the initial dataframe for the filter grid.
        
        Returns:
            pandas.DataFrame: The initial dataframe.
        """        
        
        return DEFAULT_FILTER

    def grid_filter_on_row_removed(self, event, widget):
        """
        Handles the 'row_removed' event for the filter grid.
        
        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        if gv.out_debug:
            with gv.out_debug:
                print(f"FilterGrid::grid_filter_on_row_removed() - Removing row {event['indices']} from filter grid")
        
        num_rows = len(widget.get_changed_df())
        if num_rows == 0:
            df = pd.DataFrame({
                'Type': ['Deck'],
                'Name': [''],
                'Modifier': [''],
                'Creature': [''],
                'Spell': [''],
                'Forgeborn Ability': [''],
                'Active': [False],
                'Mandatory Fields': ['Name, Forgeborn Ability'],
                'ID': ['']
            })
            widget.df = df
        else:
            widget.df = widget.get_changed_df()

        #self.notify_filter_observers(event)
        self.refresh_function(event, widget)
        

    def grid_filter_on_row_added(self, event, widget, row_data=None):
        """
        Handles the 'row_added' event for the filter grid.
        
        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        logger.info("FilterGrid::grid_filter_on_row_added() - Adding new row to filter grid")
        new_row_index = event['index']
        df = widget.get_changed_df()
        mandatory_fields = []

        # Set the values for each column in the new row
        for column in df.columns:
            if row_data is not None and not row_data.empty:
                if column in row_data.columns:
                    widget_value = row_data.iloc[0][column]
            elif column in self.selection_widgets:
                widget_value = self.selection_widgets[column].value

            if widget_value is not None:
                logger.info(f"FilterGrid::grid_filter_on_row_added() - Column: {column}, Value: {widget_value}")
                if column == 'Forgeborn Ability':
                    fb_ability_list = [fb_ability.split(' : ')[1] for fb_ability in widget_value]
                    value = '; '.join(fb_ability_list)
                else:
                    if isinstance(widget_value, (list, set, tuple)):
                        if len(widget_value) == 1:
                            value = str(widget_value[0])
                        else:
                            value = '; '.join([str(v) for v in widget_value])
                    elif isinstance(widget_value, str):
                        value = widget_value
                    else:
                        value = str(widget_value)

                df.at[new_row_index, column] = value

                if column in self.toggle_buttons_dict and self.toggle_buttons_dict[column].value:
                    mandatory_fields.append(column)

        df.at[new_row_index, 'Active'] = True
        df.at[new_row_index, 'Mandatory Fields'] = ', '.join(mandatory_fields)
        df.at[new_row_index, 'ID'] = id(widget)
        widget.df = df

        logger.info(f"FilterGrid::grid_filter_on_row_added() - Calling refresh function for index {new_row_index}")
        #self.notify_filter_observers(event)
        self.refresh_function(event, widget)

    def grid_filter_on_cell_edit(self, event, widget):
        """
        Handles the 'cell_edited' event for the filter grid.
        
        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        logger.info(f"FilterGrid::grid_filter_on_cell_edit() - Editing cell at index {event['index']}, column {event['column']}")
        row_index, column_index = event['index'], event['column']
        widget.df.loc[row_index, column_index] = event['new']
        widget.df = widget.df
        if event['new'] != event['old']:
            # Notify observers only if the event is not from the local source
            # This prevents infinite loops when the event is triggered by the observer itself
            if not ('source' in event and event['source'] == 'local'):
                grid_id = f"filtered_grid_{row_index}"
                event['source'] = 'central'
                self.notify_filter_observers(event, grid_id=grid_id)
            self.refresh_function(event, widget)

    def update(self, event, widget):
        """
        Updates the filter grid based on changes in the data selection sets.
        """
        if gv.out_debug:
            with gv.out_debug:
                print(f"FilterGrid::update() -> Updating filter grid with new data selection sets: {gv.data_selection_sets.keys()}")
        self.selection_widgets['Data Set'].options = gv.data_selection_sets.keys()

    def update_selection_content(self, change):
        """
        Updates the selection content based on changes in the widget values.
        
        Args:
            change (dict): The change notification data.
        """
        if (change['name'] == 'value' or change['name'] == 'selected_index') and change['new'] != change['old']:
            for cardType in ['Modifier', 'Creature', 'Spell']:
                widget = self.selection_widgets[cardType]
                widget.options = [''] + get_cardType_entity_names(cardType)
            
            dbDeckNames = gv.myDB.find('Deck', {}, {'name': 1})
            sorted_deckNames = [''] + sorted(
                [deck.get('name', '') for deck in dbDeckNames if 'name' in deck],
                key=lambda x: x.lower()
            )
            self.selection_widgets['Name'].update_options_from_db(sorted_deckNames)

    def create_cardType_names_selector(self, cardType, options=None):
        if options is None:
            options = {}
        layout_options = {
            'width': '20%',
            'height': 'auto',
            'align_items': 'center',
            'justify_content': 'center',
            'overflow': 'hidden',
        }
        layout_options.update(options)
        cardType_entity_names = [''] + get_cardType_entity_names(cardType)
        cardType_name_widget = EnhancedSelect(
            options=cardType_entity_names,
            toggle_description=cardType,
            description='',
            layout=widgets.Layout(**layout_options)
        )
        return cardType_name_widget

    def create_deckName_selector(self):
        deckNames = []
        dbDeckNames = gv.myDB.find('Deck', {}, {'name': 1})
        deckNames = [deck.get('name', '') for deck in dbDeckNames if 'name' in deck]
        deckNames = sorted(deckNames, key=lambda x: x.lower())
        deckNames.insert(0, '')
        deckName_widget = EnhancedSelect(
            options=deckNames,
            description='',
            toggle_description='Name',
            layout=widgets.Layout(width='30%', height='auto', align_items='center', justify_content='center', overflow='hidden'),
            toggle_default=True
        )
        return deckName_widget

    def create_selection_box(self):
        widgets_dict = {
            'Type': EnhancedSelect(
                allow_multiple=False,
                options=['Deck', 'Fusion'],
                value='Deck',
                description='',
                toggle_description='Type',
                toggle_default=True,
                toggle_disable=True,
                layout=widgets.Layout(width='30%', height='auto', border='1px solid cyan', align_items='center', justify_content='center', overflow='hidden')
            ),
            'Name': self.create_deckName_selector(),
            'Modifier': self.create_cardType_names_selector('Modifier', options={'border': '1px solid blue'}),
            'Creature': self.create_cardType_names_selector('Creature', options={'border': '1px solid green'}),
            'Spell': self.create_cardType_names_selector('Spell', options={'border': '1px solid red'}),
            'Forgeborn Ability': EnhancedSelect(
                options=[''] + get_forgeborn_abilities(),
                description='',
                toggle_description='Forgeborn Ability',
                toggle_default=True,
                layout=widgets.Layout(width='30%', height='auto', border='1px solid orange', align_items='center', justify_content='center', overflow='hidden')
            ),
        }

        widget_row_items = [widgets_dict[key] for key in widgets_dict]
        widget_row_items = [widget.get_widget() if isinstance(widget, EnhancedSelect) else widget for widget in widget_row_items]
        widget_row = widgets.HBox(
            widget_row_items,
            layout=widgets.Layout(display='flex', flex_flow='row nowrap', width='100%', align_items='center', justify_content='flex-start', gap='5px')
        )
        toggle_buttons_dict = {key: widget.toggle_button for key, widget in widgets_dict.items() if hasattr(widget, 'toggle_button') and key != 'Type'}
        selection_box = widgets.VBox([widget_row], layout=widgets.Layout(width='100%'))
        return selection_box, widgets_dict, toggle_buttons_dict

    def get_changed_df(self):
        """
        Returns the current DataFrame with any user changes.
        
        Returns:
            pandas.DataFrame: The changed dataframe.
        """
        return self.qgrid_filter.get_changed_df()

    def get_widgets(self):
        """
        Returns the widgets associated with the filter grid.
        
        Returns:
            tuple: A tuple containing the selection box and the filter qgrid widget.
        """
        return self.selection_box, self.qgrid_filter

    def merge_active_filters(self):
        """
        Merges multiple deck filters into a single fusion filter.
        
        Returns:
            dict: The merged filter.
        """
        merged_filter = {
            "Type": "Fusion",
            "Active": True,
            "Mandatory Fields": set()
        }
        df = self.get_changed_df()
        filters = df.loc[df['Active'] == True]

        for _, filter_row in filters.iterrows():
            for field, value in filter_row.items():
                if field in ["Type", "Active", "Mandatory Fields", "ID"] or not value:
                    continue
                if field not in merged_filter:
                    merged_filter[field] = set()
                merged_filter[field].add(value)
                merged_filter["Mandatory Fields"].add(field)

        for field in list(merged_filter.keys()):
            if field in ["Type", "Active", "Mandatory Fields", "ID"]:
                continue
            merged_filter[field] = ":".join(merged_filter[field])

        merged_filter["Mandatory Fields"] = ", ".join(merged_filter["Mandatory Fields"])
        return merged_filter

    # Function to update the ID of a specific row in the filter grid
    # This is useful for tracking the grid ID of each filter row.
    def update_filter_row_id(self, row_index, new_id):
        """
        Updates the 'ID' column for the row at the given index with the new grid ID.

        Args:
            row_index (int): The index of the row to update.
            new_id (int): The new unique identifier (e.g. id(grid_widget)) to set.
        """
        # Get the current state of the filter DataFrame.
        df = self.qgrid_filter.get_changed_df().copy()
        
        # Make sure the "ID" column exists; if not, create it.
        if 'ID' not in df.columns:
            df['ID'] = ""
        
        # Update the specific row's ID.
        df.at[row_index, 'ID'] = new_id
        
        # Update the qgrid widget's DataFrame so that the change takes effect.
        self.qgrid_filter.df = df


def get_cardType_entity_names(cardType):
    """
    Retrieves the names of entities that match the specified card type.
    
    Args:
        cardType (str): The type of card.
    
    Returns:
        list: A list of entity names that match the card type.
    """
    commonDB = DatabaseManager('common')
    cardType_entities = commonDB.find('Entity', {"attributes.cardType": cardType})
    cardType_entities_names = [entity['name'] for entity in cardType_entities]
    cards = gv.myDB.find('Card', {})
    cardNames = [card.get('title', card.get('name', '')) for card in cards]
    cardType_entities_names = [name for name in cardType_entities_names if any(name in cardName for cardName in cardNames)]
    cardType_entities_names.sort()
    return cardType_entities_names


def get_forgeborn_abilities():
    """
    Retrieves the names of forgeborn abilities.
    
    Returns:
        list: A list of forgeborn ability names.
    """
    commonDB = DatabaseManager('common')
    forgeborns = commonDB.find('Forgeborn', {})
    forgeborn_abilities_list = [forgeborn['abilities'] for forgeborn in forgeborns]
    ability_names = [f"{id[5:-5].capitalize()} : {name}" 
                     for abilities in forgeborn_abilities_list 
                     for id, name in abilities.items() if "Fraud" not in name]
    ability_names = [re.sub(r'C\d+ - ', '', name) for name in ability_names]
    ability_names = list(set(ability_names))
    ability_names.sort()
    return ability_names