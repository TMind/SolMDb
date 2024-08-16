import pandas as pd
import qgrid 
import ipywidgets as widgets

from GridManager import data_selection_sets
from DataSelectionManager import DataSelectionManager

class TemplateGrid:
    global data_selection_sets
    
    def __init__(self):        

        #self.data_selection_sets = data_selection_sets
        self.df = self.create_initial_dataframe()
        self.qgrid_filter = self.create_filter_qgrid()        

    def create_filter_qgrid(self):
        
        column_definitions = { 'index' : { 'width' : 25 } }
        columns = ['Template Name', 'name', 'type', 'registeredDate', 'UpdatedAt', 'pExpiry', 'elo', 'xp', 'level', 'Creatures', 'Spells', 'cardSetNo', 'faction', 'forgebornId', 'cardTitles', 'FB4', 'FB2', 'FB3', 'A1', 'A2', 'A3', 'H1', 'H2', 'H3', 
                        'Deck A', 'Deck B',
                        'Beast', 'Beast Synergy', 'Dinosaur', 'Dinosaur Synergy', 'Mage', 'Mage Synergy', 'Robot', 'Robot Synergy',
                        'Scientist', 'Scientist Synergy', 'Spirit', 'Spirit Synergy', 'Warrior', 'Warrior Synergy',
                        'Zombie', 'Zombie Synergy', 'Dragon', 'Dragon Synergy', 'Elemental', 'Elemental Synergy',
                        'Plant', 'Plant Synergy', 'Replace Setup', 'Replace Profit', 'Minion', 'Minion Synergy',
                        'Spell', 'Spell Synergy', 'Healing Source', 'Healing Synergy', 'Movement', 'Disruption',
                        'Movement Benefit', 'Armor', 'Armor Giver', 'Armor Synergy', 'Activate', 'Ready', 'Free',
                        'Upgrade', 'Upgrade Synergy', 'Face Burn', 'Removal', 'Breakthrough', 'Breakthrough Giver',
                        'Aggressive', 'Aggressive Giver', 'Defender', 'Defender Giver', 'Stealth', 'Stealth Giver',
                        'Stat Buff', 'Attack Buff', 'Health Buff', 'Stat Debuff', 'Attack Debuff', 'Health Debuff',
                        'Destruction Synergy', 'Destruction Activator', 'Self Damage Payoff', 'Self Damage Activator',
                        'Silence',  'Exalts', 'Exalt Synergy', 'Slay', 'Deploy', 'White Fang', 'Last Winter', 'Spicy',
                        'Cool', 'Fun', 'Annoying']

        for column in columns:
            width  = len(column) * 11
            column_definitions[column] = { 'width': width }
            #print(f"Column: {column}, Width: {width}")

        qgrid_filter = qgrid.show_grid(
            self.df,
            column_definitions= column_definitions,
            grid_options={'forceFitColumns': False, 'filterable' : False, 'sortable' : False, 'defaultColumnWidth' : 75,  'enableColumnReorder': True},
            show_toolbar=True
        )
        qgrid_filter.layout = widgets.Layout(height='auto')
        
        qgrid_filter.on('row_added', self.grid_filter_on_row_added)
        qgrid_filter.on('row_removed', self.grid_filter_on_row_removed)        
        qgrid_filter.on('cell_edited', self.grid_filter_on_cell_edit)

        return qgrid_filter

    def create_initial_dataframe(self):

        rows = []

        for template_name, template_set in data_selection_sets.items():
            # Create a dictionary with True for each column in the template_set
            #row = {col: True for col in template_set}
            row = template_set.copy()
            # Add the template_name to the dictionary
            row['Template Name'] = template_name
            # Append the dictionary to the list
            rows.append(row)

        # Create the DataFrame from the list of dictionaries
        template_df = pd.DataFrame(rows)
        columns = ['Template Name'] + [col for col in template_df.columns if col != 'Template Name']
        template_df = template_df[columns]
        template_df.fillna(False, inplace=True)
        template_df = template_df.infer_objects()

        # Set the 'Template Name' column as the index of the DataFrame
        #template_df.set_index('Template Name', inplace=True)
        return template_df

    def grid_filter_on_row_removed(self, event, widget):
        """
        Handles the 'row_removed' event for the filter grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        active_rows = []
        if 0 in event['indices']:
            df = self.create_initial_dataframe()
            widget.df = pd.concat([df, widget.get_changed_df()], ignore_index=True)
            event['indices'].remove(0)        
        
        # Update the Data Set in the FilterGrid widget 
        self.update_data_selection_sets()
        DataSelectionManager.update_data(event, widget)
        

    def grid_filter_on_row_added(self, event, widget):
        new_row_index = event['index']
        df = widget.get_changed_df()
        
        # Set default values for the new row
        for column in df.columns:
            if column != 'Template Name':
                df.at[new_row_index, column] = False
        
        df.at[new_row_index, 'Template Name'] = 'New Template'
        widget.df = df

        # Update the Data Set in the FilterGrid widget 
        self.update_data_selection_sets()
        DataSelectionManager.update_data(event, widget)
        

    def grid_filter_on_cell_edit(self, event, widget):        
        row_index, column_index = event['index'], event['column']
        df = widget.get_changed_df()
        df.loc[row_index, column_index] = event['new']
        widget.df = df 
    
        # Update the Data Set in the FilterGrid widget 
        self.update_data_selection_sets()
        DataSelectionManager.update_data(event, widget)
   
    def update_data_selection_sets(self):
        global data_selection_sets
        #print(f"TemplateGrid::update_data_selection_sets() -> old data: {data_selection_sets}")
        # Set data_selection_sets to reflect the current keys and values of the dataframe        
        template_df = self.qgrid_filter.get_changed_df()
        data_selection_sets = {template_df.loc[template]['Template Name']: template_df.loc[template].index[template_df.loc[template] == True].tolist() for template in template_df.index}
        #print(f"TemplateGrid::update_data_selection_sets() -> Updating data selection sets with new data: {data_selection_sets}")



 