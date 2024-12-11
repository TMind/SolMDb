import os
import re
import time
import webbrowser
from datetime import datetime
from typing import OrderedDict

import ipywidgets as widgets
import pandas as pd
import qgridnext as qgrid
from icecream import ic
from pymongo.collection import Collection
from qgridnext import QgridWidget

from CardLibrary import Forgeborn, ForgebornAbility, ForgebornData
from CustomCss import CSSManager
from CustomGrids import ActionToolbar, TemplateGrid
from DataSelectionManager import DataSelectionManager
from DeckLibrary import Deck, Fusion, FusionData
from DynamicGrids import GridManager, VBoxManager
from FilterGrid import FilterGrid
from GlobalVariables import global_vars as gv, rotate_suffix
from MongoDB.DatabaseManager import DatabaseManager
from SortingManager import SortingManager
from Synergy import SynergyTemplate
from Utils import get_min_time, apply_filter_to_dataframe, FieldUnifier

from MyGraph import MyGraph
from NetApi import NetApi

import logging
from soldb import parse_arguments
from tzlocal import get_localzone
import pytz
from IPython.display import display

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DEFAULT_FILTER = pd.DataFrame({
    'Type': ['Deck'],
    'Name': [''],
    'Modifier': [''],
    'Creature': [''],
    'Spell': [''],
    'Forgeborn Ability': [''],
    'Active': [True],
    'Mandatory Fields': ['Name, Forgeborn Ability']
})


class DynamicGridManager:
    def __init__(self, data_generate_functions, qg_options, out_debug):
        self.out_debug = out_debug
        self.data_generate_functions = data_generate_functions
        self.qg_options = qg_options
        self.qm = GridManager(out_debug)

        self.filterGridObject = FilterGrid(self.refresh_gridbox)
        self.deck_content_Grid = self.create_deck_content_Grid()
        self.sorting_info = {}
        self.css_manager = CSSManager()
        self.custom_css_class = self.css_manager.create_and_inject_css('deck_content', rotate_suffix)
        self.grid_widget_states = {}

        # GridBox
        self.VBoxGrids = VBoxManager()

        # Initialize filter widgets
        self.selectionGrid, self.filterGrid = self.filterGridObject.get_widgets()

        # Initialize UI components
        self.deck_filter_bar = self.create_styled_html(
            "Filter Selection: Set custom filters to your deck base.",
            text_color='white', bg_color='#2E86AB', border_color='#205E86'  # Darker blue for contrast
        )
        self.filter_grid_bar = self.create_styled_html(
            "Filter Grid: Apply your custom filter to the deck base.",
            text_color='white', bg_color='#FFA630', border_color='#CC7A00'  # A darker orange to complement the background
        )
        self.filter_results_bar = self.create_styled_html(
            "Filter Results: Displays the results of the filters applied to the deck base.",
            text_color='#2E2E2E', bg_color='#CFF27E', border_color='#B2D38A'  # A more muted green to blend with the background
        )
        self.deck_content_bar = self.create_styled_html(
            "Deck / Fusion Content: Displays the last selected item",
            text_color='white', bg_color='#AA4465', border_color='#4A4A4A'
        )

        # Initialize the widget dictionary and wrap each group in a VBox
        self.ui_widget_dict = OrderedDict({
            'Selection': widgets.VBox([self.deck_filter_bar, self.selectionGrid]),
            'Filter': widgets.VBox([self.filter_grid_bar, self.filterGrid]),
            'Grid': widgets.VBox([self.filter_results_bar, self.VBoxGrids.get_main_vbox()]),
            'Content': widgets.VBox([self.deck_content_bar, self.deck_content_Grid.main_widget])
        })

        self.ui = widgets.VBox([])

        # Initialize other UI components
        self.create_widgets()

    def create_styled_html(self, text, text_color, bg_color, border_color):
        html = widgets.HTML(
            value=f"<div style='padding:10px; color:{text_color}; background-color:{bg_color};"
                  f" border:solid 2px {border_color}; border-radius:5px;'>"
                  f"<strong>{text}</strong></div>"
        )
        return html

    def create_widgets(self):
        # Initialize faction toggles and dropdowns
        self.factionToggles = []
        self.dropdowns = []
        factionNames = ['Alloyin', 'Nekrium', 'Tempys', 'Uterra']
        for i in range(2):
            factionToggle, dropdown = self.initialize_widgets(factionNames)
            self.factionToggles.append(factionToggle)
            self.dropdowns.append(dropdown)

        # Button to create network graph
        button_graph = widgets.Button(description='Show Graph')
        button_graph.on_click(lambda button: self.display_graph())

        # Toggle buttons to select load items
        loadToggle = widgets.ToggleButtons(
            options=['Load Decks/Fusions', 'Update Decks/Fusions', 'Create all Fusions', 'Generate Dataframe', 'Find Combos', 'Update CM Sheet', 'Refresh Grid'],
            description='Action:',
            disabled=False,
            button_style='warning',
            tooltips=[
                'Load Decks and Fusions from the website',
                'Update Decks and Fusions in the database',
                'Create Fusions from loaded decks',
                'Generate central dataframe',
                'Find Combos',
                'Update Collection Manager Sheet',
                'Refresh Grid'
            ]
        )

        # Button to execute selected action
        button_load = widgets.Button(description='Execute', button_style='info', tooltip='Execute the selected action')
        button_load.on_click(lambda button: self.reload_data_on_click(button, loadToggle.value))

        # Database selection widget
        db_list = self.create_database_selection_widget()
        db_list.observe(lambda change: self.handle_db_list_change(change), names='value')

        # Create a Checkbox widget to toggle debugging
        debug_toggle = widgets.Checkbox(value=False, description='Debugging', disabled=False)
        debug_toggle.observe(lambda change: self.handle_debug_toggle(change), 'value')

        # Initialize Action Toolbar
        self.action_toolbar_ui = self.create_action_toolbar_ui()

        # Assemble everything into the UI
        self.ui_widget_dict['Additional Controls'] = widgets.VBox([loadToggle, button_load, button_graph, debug_toggle, db_list, self.action_toolbar_ui])

    def initialize_widgets(self, factionNames):
        faction_toggle = self.create_faction_selection_toggle(factionNames)
        dropdown = widgets.Dropdown()
        faction_toggle.observe(lambda change: self.refresh_faction_deck_options(faction_toggle, dropdown), 'value')
        return faction_toggle, dropdown

    def create_faction_selection_toggle(self, faction_names, initial_style='info'):
        faction_toggle = widgets.ToggleButtons(
            options=faction_names,
            description='Faction:',
            disabled=False,
            button_style=initial_style,
            tooltips=['Alloyin', 'Nekrium', 'Tempys', 'Uterra'],
        )

        def update_button_style(change):
            if change['new'] == 'Alloyin':
                faction_toggle.button_style = 'info'
            elif change['new'] == 'Nekrium':
                faction_toggle.button_style = 'warning'
            elif change['new'] == 'Tempys':
                faction_toggle.button_style = 'danger'
            elif change['new'] == 'Uterra':
                faction_toggle.button_style = 'success'

            # Force a redraw of the widget
            faction_toggle.layout = widgets.Layout()

        faction_toggle.observe(update_button_style, 'value')

        return faction_toggle

    def refresh_faction_deck_options(self, faction_toggle, dropdown):
        if self.out_debug:
            with self.out_debug:
                print(f'Faction toggle changed: {faction_toggle.value}')

        deckCursor = []
        if gv.myDB:
            deckCursor = gv.myDB.find('Deck', {'faction': faction_toggle.value})
        deckNames = [deck['name'] for deck in deckCursor]
        dropdown.options = deckNames

    def create_database_selection_widget(self):
        DB = DatabaseManager('common')
        db_names = DB.mdb.client.list_database_names()
        db_names = [db for db in db_names if db not in ['local', 'admin', 'common', 'config']]
        db_list = widgets.RadioButtons(
            options=[''] + db_names,
            description='Databases:',
            disabled=False
        )

        def on_db_list_change(change):
            if self.out_debug:
                with self.out_debug:
                    print(f'Database list changed: {change["new"]}')
            if change['new']:
                gv.username = change['new']

        db_list.observe(on_db_list_change, 'value')

        return db_list

    def create_action_toolbar_ui(self):
        action_toolbar = ActionToolbar()
        action_toolbar.assign_callback('Export', lambda identifier=None: self.save_dataframes_to_csv(identifier))
        action_toolbar.assign_callback('Open', lambda identifier=None: self.open_deck(identifier))
        action_toolbar.assign_callback('Graph', lambda identifier=None: self.show_graph(identifier))
        return action_toolbar.get_ui()

    def create_deck_content_Grid(self):
        # Define the default grid options
        default_options = {
            'minVisibleRows': 10,
            'maxVisibleRows': 20
        }

        # Create the deck content qgrid with the merged options
        deck_content_grid = self.qm.add_grid(
            'deck_content',
            pd.DataFrame(),  # Start with an empty DataFrame
            options=self.qg_options
        )

        # Apply CSS if needed
        self.css_manager.apply_conditional_class(deck_content_grid.main_widget, rotate_suffix, self.custom_css_class)

        return deck_content_grid

    def reload_data_on_click(self, button, value):
        # Prevent multiple concurrent operations
        if getattr(self, 'operation_in_progress', False):
            print('Operation is already in progress. Please wait.')
            return

        # Set the flag to indicate that the operation is ongoing
        self.operation_in_progress = True

        try:
            username_value = gv.username if hasattr(gv, 'username') else ''  # Retrieve the username from gv

            if not username_value:
                print('Username cannot be empty.')
                return

            gv.username = username_value

            if not getattr(gv, 'myDB', None):
                gv.set_myDB()

            # Execute based on action value
            if value == 'Load Decks/Fusions':
                arguments = ['--username', username_value,
                             '--mode', 'create',
                             '--type', 'deck,fuseddeck']
                args = parse_arguments(arguments)
            elif value == 'Update Decks/Fusions':
                arguments = ['--username', username_value,
                             '--mode', 'update',
                             '--type', 'deck,fuseddeck']
                args = parse_arguments(arguments)
            elif value == 'Create all Fusions':
                arguments = ['--username', username_value,
                             '--mode', 'fuse']
                args = parse_arguments(arguments)
            elif value == 'Generate Dataframe':
                self.data_generate_functions['central_dataframe'](force_new=True)
                self.refresh_gridbox()
                return
            elif value == 'Update CM Sheet':
                if hasattr(gv, 'commonDB') and gv.commonDB:
                    gv.commonDB.drop_database()
                if hasattr(gv, 'cm_manager') and gv.cm_manager:
                    gv.cm_manager.update_local_csv('Card Database')
                gv.reset_universal_library()
                self.update_sheet_stats()
                return
            elif value == 'Find Combos':
                combo_df = self.data_generate_functions.get('find_combos')()
                # Handle the combo_df as needed
                return
            elif value == 'Refresh Grid':
                self.refresh_gridbox()
                return

            # Execute main task if other tasks are not returning early
            self.data_generate_functions.get('load_deck_data')(args)

            # Refresh db_list widget
            if hasattr(gv.myDB, 'mdb'):
                db_names = gv.myDB.mdb.client.list_database_names()
                valid_db_names = [db for db in db_names if db not in ['local', 'admin', 'common', 'config']]

                if valid_db_names:
                    # Update the db_list widget options
                    db_list_widget = self.ui_widget_dict['Additional Controls'].children[4]  # Assuming db_list is the 5th widget
                    db_list_widget.options = [''] + valid_db_names
                    if username_value in valid_db_names:
                        self.update_deck_and_fusion_counts()
                        db_list_widget.value = username_value
                    else:
                        db_list_widget.value = valid_db_names[0]
                else:
                    db_list_widget = self.ui_widget_dict['Additional Controls'].children[4]
                    db_list_widget.options = ['']
                    db_list_widget.value = ''  # Set to an empty string if no valid databases
        finally:
            # Reset the progress flag
            self.operation_in_progress = False
            # Re-enable the button if necessary
            if button:
                button.disabled = False

    def handle_debug_toggle(self, change):
        if change['new']:
            ic.enable()
            gv.debug = True
        else:
            ic.disable()
            gv.debug = False

    def handle_db_list_change(self, change):
        if gv.out_debug:
            with self.out_debug:
                print(f'DB List Change: {change}')

        if change['name'] == 'value' and change['old'] != change['new']:
            new_username = change['new']  # Ensure new_username is a string

            if new_username:
                # Update the Global Username Variable
                gv.username = new_username

                # Handle the database change
                self.handle_database_change()
            else:
                pass  # Handle the case where no valid database is selected

    def update_deck_and_fusion_counts(self):
        display_data = {}

        db_manager = gv.myDB
        if db_manager:
            deck_count = db_manager.count_documents('Deck', {})
            fusion_count = db_manager.count_documents('Fusion', {})
            username = db_manager.get_current_db_name()

            # Query the GridFS for the 'central_df' file
            file_record = db_manager.find_one('fs.files', {'filename': f"central_df_{username}"})

            if file_record and 'uploadDate' in file_record:
                # Get the local timezone from your system
                utc_upload_date = file_record['uploadDate']
                local_timezone = get_localzone()
                NuOfDecks = file_record['metadata']['decks'] if 'metadata' in file_record else 0
                NuOfFusions = file_record['metadata']['fusions'] if 'metadata' in file_record else 0

                # Convert UTC to your local timezone
                creation_date = utc_upload_date.replace(tzinfo=pytz.utc).astimezone(local_timezone)
                creation_date_str = creation_date.strftime('%Y-%m-%d %H:%M:%S')

                # Store the DataFrame information in the dictionary
                display_data['DataFrame'] = {
                    'Timestamp': creation_date_str,
                    'Decks': NuOfDecks,
                    'Fusions': NuOfFusions
                }

            else:
                creation_date_str = "No previous update found"

            # Store the deck and fusion count information in the dictionary
            display_data['Collection'] = {
                'Timestamp': creation_date_str,
                'Decks': deck_count,
                'Fusions': fusion_count
            }

            # Update the display
            self.update_count_display(display_data)
        else:
            print('No database manager found.')

    def update_count_display(self, display_data):
        """
        Updates the count_display widget with the combined information stored in the display_data dictionary.
        """
        count_display = self.ui_widget_dict['Additional Controls'].children[3]  # Assuming count_display is the 4th widget
        count_display.clear_output()

        rows = []

        for key, value in sorted(display_data.items()):
            if value:
                if isinstance(value, dict):
                    for sub_key, sub_value in sorted(value.items()):
                        rows.append((key, sub_key, sub_value))

        if rows:
            df_display = pd.DataFrame(rows, columns=['Info Type', 'Key', 'Value'])
            df_display.set_index(['Info Type', 'Key'], inplace=True)
            with count_display:
                display(df_display)
        else:
            with count_display:
                print("No data to display.")

    def update_sheet_stats(self):
        """
        Updates the timestamp, title, and tags of the Google Sheet only when this function is called.
        """
        display_data = {}

        if hasattr(gv, 'cm_manager') and gv.cm_manager:
            current_timestamp = gv.cm_manager.timestamp
            current_title = gv.cm_manager.title

            display_data['CM Sheet'] = {
                'Title': current_title,
                'Timestamp': current_timestamp
            }

            self.update_count_display(display_data)
        else:
            print("CMManager not initialized.")

    def display_graph(self):
        selected_items = self.get_selected_grid_items()
        if selected_items:
            for grid_id, items in selected_items.items():
                self.show_graph(grid_id, items)
        else:
            print("No items selected to display graph.")

    def save_dataframes_to_csv(self, identifier=None, directory='dataframes'):
        def df_to_disk(widget):
            df = widget.get_changed_df()
            if df is not None and not df.empty:
                csv_filename = os.path.join(directory, f"{identifier}.csv")
                df.to_csv(csv_filename, index=False)
                with self.out_debug:
                    print(f"Saved DataFrame '{identifier}' to {csv_filename}")
            else:
                with self.out_debug:
                    print(f"No data available for grid '{identifier}', skipping...")

        # Create the directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        if identifier:
            grid = self.qm.grids.get(identifier)
            if grid is not None:
                df_to_disk(grid.main_widget)
            else:
                with self.out_debug:
                    print(f"Grid '{identifier}' not found in GridManager, skipping...")
            return

        # Iterate through all grids
        for identifier, widget in self.qm.grids.items():
            df_to_disk(widget.main_widget)
        with self.out_debug:
            print(f"All applicable DataFrames saved to {directory}:")

    def open_deck(self, grid_id, button=None):
        if not grid_id in self.grid_widget_states or not 'Selection' in self.grid_widget_states[grid_id]:
            print(f"No selection found for grid_id '{grid_id}', skipping...")
            return

        selected_items_list = self.grid_widget_states[grid_id]['Selection']
        central_df = self.qm.get_grid_df('collection').copy()

        for item in selected_items_list:
            item_row = central_df[central_df['Name'] == item]
            if not item_row.empty:
                item_dict = item_row.to_dict(orient='records')[0]
                item_id = item_dict['id']
                item_type = item_dict['type']

                if item_type == 'Fusion':
                    item_type = 'fused'
                elif item_type == 'Deck':
                    item_type = 'decks'

                item_link = f'https://solforgefusion.com/{item_type}/{item_id}'
                webbrowser.open(item_link)
            else:
                print(f"Item '{item}' not found in the central dataframe.")

    def show_graph(self, grid_id, button=None):
        selected_items_list = self.grid_widget_states.get(grid_id, {}).get('Selection', [])
        if selected_items_list:
            self.display_selected_graph(selected_items_list)
        else:
            print("No items selected to display graph.")

    def display_selected_graph(self, selected_items_list):
        for item in selected_items_list:
            item_row = gv.myDB.find_one('Deck', {'name': item}) or gv.myDB.find_one('Fusion', {'name': item})
            if item_row:
                graph = item_row.get('graph', {})
                if graph:
                    myGraph = MyGraph()
                    myGraph.from_dict(graph)
                    net = Network(notebook=True, directed=True, height='1500px', width='2000px', cdn_resources='in_line')
                    net.from_nx(myGraph.G)
                    net.force_atlas_2based()
                    net.show_buttons(True)

                    filename = f'html/{item}.html'
                    net.show(filename)

                    # Read HTML file content and display using IPython HTML
                    filepath = os.path.join(os.getcwd(), filename)
                    if os.path.exists(filepath):
                        webbrowser.open(f'file://{filepath}')
                        display(widgets.HTML(filename=filepath))
                    else:
                        print(f"File {filename} not found.")
            else:
                print(f"Item '{item}' not found in the database.")

    def apply_filters(self, df, widget_states):
        info_level = widget_states['info_level']
        data_set = widget_states['data_set']
        filter_row = widget_states['filter_row']
        filtered_df = apply_filter_to_dataframe(df, pd.DataFrame([filter_row]))
        return self.determine_columns(filtered_df, info_level, data_set, filter_row['Type'])

    def determine_columns(self, df, info_level, data_set, item_type):
        data_set_columns = FieldUnifier.generate_final_fields(info_level, data_set, item_type)
        existing_columns = [col for col in data_set_columns if col in df.columns]
        filtered_df = df.loc[:, existing_columns]
        return filtered_df

    def update_or_refresh_grid(self, grid_identifier, collection_df=None, filter_row=None):
        logger.info(f"Updating or refreshing grid '{grid_identifier}'")

        if filter_row is not None:
            grid_state = self._get_or_update_grid_state(grid_identifier, filter_row)
        else:
            grid_state = self.grid_widget_states.get(grid_identifier)

        if not grid_state:
            logger.warning(f"No state found for grid identifier: {grid_identifier}")
            return

        if collection_df is None:
            collection_df = self.qm.get_grid_df('collection')
            logger.info(f"Retrieved collection DataFrame with {len(collection_df)} rows and {len(collection_df.columns)} columns")

        filtered_df = self.apply_filters(collection_df, grid_state)

        if grid_identifier not in self.qm.grids:
            logger.info(f"Rebuilding grid '{grid_identifier}'")
            grid = self.qm.add_grid(grid_identifier, filtered_df, options=self.qg_options)
            self.qm.on(grid_identifier, 'selection_changed', self.update_deck_content)
            new_widget = self.construct_grid_ui(grid_identifier, filter_row, grid)
            self.VBoxGrids.add_widget(new_widget, grid_identifier)
            logger.info(f"Grid '{grid_identifier}' rebuilt with {len(filtered_df)} rows and {len(filtered_df.columns)} columns")
        else:
            logger.info(f"Updating grid '{grid_identifier}' with filtered data")
            self.qm.update_dataframe(grid_identifier, filtered_df)
            logger.info(f"Grid '{grid_identifier}' updated with {len(filtered_df)} rows and {len(filtered_df.columns)} columns")

    def _get_collection_dataframe(self, change):
        collection_df = self.qm.get_grid_df('collection')
        if collection_df.empty or (change and 'type' in change and change['type'] in {'username', 'generation'}):
            collection_df = self.data_generate_functions['central_dataframe'](force_new=True)
            self.qm.add_grid('collection', collection_df, options=self.qg_options)
        return collection_df

    def _get_or_update_grid_state(self, grid_identifier, filter_row):
        grid_state = self.grid_widget_states.get(grid_identifier, {})
        grid_state.update({
            "info_level": grid_state.get("info_level", 'Basic'),
            "data_set": grid_state.get("data_set", 'Stats'),
            "filter_row": filter_row.to_dict()
        })
        self.grid_widget_states[grid_identifier] = grid_state
        return grid_state

    def construct_grid_ui(self, grid_identifier, filter_row, grid):
        toolbar_widget = self.create_toolbar(grid_identifier)
        filter_row_widget = qgrid.show_grid(
            pd.DataFrame([filter_row]),
            show_toolbar=False,
            grid_options={'forceFitColumns': True, 'filterable': False, 'sortable': False, 'editable': True}
        )
        filter_row_widget.layout = widgets.Layout(height='70px')

        def on_filter_row_change(event, qgrid_widget=filter_row_widget):
            if event['new'] != event['old']:
                logger.info(f"Cell edited in filter_row_widget for grid '{grid_identifier}': {event}")
                self.update_or_refresh_grid(grid_identifier)

        if not hasattr(filter_row_widget, '_event_listener_attached'):
            filter_row_widget.on('cell_edited', on_filter_row_change)
            filter_row_widget._event_listener_attached = True

        return widgets.VBox([toolbar_widget, filter_row_widget, grid.get_grid_box()],
                            layout=widgets.Layout(border='2px solid black'))

    def get_ui_widget(self, group_name):
        return self.ui_widget_dict.get(group_name, widgets.Label(""))

    def create_toolbar(self, grid_identifier):
        info_level_button = widgets.ToggleButtons(
            options=['Basic', 'Detail'],
            value='Basic',
            description='Info Level:',
            button_style='info',
            layout=widgets.Layout(width='30%', height='25px', display='flex', flex_flow='row', align_items='center')
        )

        spacer = widgets.Box(layout=widgets.Layout(flex='1'))

        data_set_dropdown = widgets.Dropdown(
            options=gv.data_selection_sets.keys(),
            value=list(gv.data_selection_sets.keys())[0] if gv.data_selection_sets else None,
            description='Data Set:',
            layout=widgets.Layout(width='25%', align_self='flex-end')
        )

        def on_info_level_change(change):
            if change['type'] == 'change' and change['name'] == 'value':
                self.grid_widget_states[grid_identifier]['info_level'] = change['new']
                self.update_or_refresh_grid(grid_identifier)

        def on_data_set_change(change):
            if change['type'] == 'change' and change['name'] == 'value':
                self.grid_widget_states[grid_identifier]['data_set'] = change['new']
                self.update_or_refresh_grid(grid_identifier)

        info_level_button.observe(on_info_level_change, 'value')
        data_set_dropdown.observe(on_data_set_change, 'value')

        per_grid_controls = widgets.HBox([info_level_button, spacer, data_set_dropdown],
                                         layout=widgets.Layout(padding='5px 5px', align_items='center', width='100%'))

        # Create Action Toolbar
        action_toolbar = ActionToolbar()
        action_toolbar.assign_callback('Export', lambda identifier=grid_identifier: self.save_dataframes_to_csv(identifier))
        action_toolbar.assign_callback('Open', lambda identifier=grid_identifier: self.open_deck(identifier))
        action_toolbar.assign_callback('Graph', lambda identifier=grid_identifier: self.show_graph(identifier))
        action_toolbar_ui = action_toolbar.get_ui()

        # Combine Per-Grid Controls and Action Toolbar
        combined_toolbar = widgets.VBox([
            per_grid_controls,    # Per-grid controls
            action_toolbar_ui     # Action buttons
        ], layout=widgets.Layout(width='100%'))

        return combined_toolbar

    def display_selected_graph(self, selected_items_list):
        for item in selected_items_list:
            item_row = gv.myDB.find_one('Deck', {'name': item}) or gv.myDB.find_one('Fusion', {'name': item})
            if item_row:
                graph = item_row.get('graph', {})
                if graph:
                    myGraph = MyGraph()
                    myGraph.from_dict(graph)
                    net = Network(notebook=True, directed=True, height='1500px', width='2000px', cdn_resources='in_line')
                    net.from_nx(myGraph.G)
                    net.force_atlas_2based()
                    net.show_buttons(True)

                    filename = f'html/{item}.html'
                    net.show(filename)

                    # Read HTML file content and display using IPython HTML
                    filepath = os.path.join(os.getcwd(), filename)
                    if os.path.exists(filepath):
                        webbrowser.open(f'file://{filepath}')
                        display(widgets.HTML(filename=filepath))
                    else:
                        print(f"File {filename} not found.")
            else:
                print(f"Item '{item}' not found in the database.")
