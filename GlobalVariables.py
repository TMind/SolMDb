import ipywidgets as widgets
from IPython.display import display
from gridfs import GridFS

class GlobalVariables:
    def __init__(self):
        self._username = ''
        self.uri = "mongodb://localhost:27017"
        self.myDB = None
        self.fs = None 
        self.commonDB = self._initialize_commonDB()
        self.progress_containers = {}
        self.debug = False

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        self._username = value
        self.set_myDB()

    def set_myDB(self):
        from MongoDB.DatabaseManager import DatabaseManager
        # Logic to set myDB based on the new username
        self.myDB = DatabaseManager(self._username)
        self.fs = GridFS(self.myDB.mdb.db)  # Set GridFS for the user-specific DB

    def _initialize_commonDB(self):
        from MongoDB.DatabaseManager import DatabaseManager  # Lazy import
        return DatabaseManager('common')

    def get_or_create_progress_container(self, identifier, description=None):
        if identifier not in self.progress_containers:
            # Create a new IntProgress widget
            progress_bar = widgets.IntProgress(
                description=description or identifier,
                value=0, min=0, max=100,
                bar_style='info', style={'bar_color': 'lightblue', 'description_width': '150px'},
                layout=widgets.Layout(width='25%')  # Relative width
            )
            # Create a label widget
            label = widgets.Label(description, layout=widgets.Layout(width='auto'))
            # Create an HBox to hold both the label and the progress bar
            hbox = widgets.HBox([progress_bar, label])
            self.progress_containers[identifier] = {'container': hbox, 'progress_bar': progress_bar, 'label': label}
            # Display the new HBox
            display(hbox)
        return self.progress_containers[identifier]

    def update_progress(self, identifier, value=None, total=None, message=None):
        container = self.get_or_create_progress_container(identifier)
        progress_bar = container['progress_bar']
        label = container['label']

        if message:
            label.value = message
        if total is not None:
            progress_bar.max = total
        if value is not None:
            progress_bar.value = value
            if value == 0:
                progress_bar.bar_style = 'info'
                progress_bar.style.bar_color = 'lightblue'
        else:
            progress_bar.value += 1  # Auto-increment if no value provided

        if progress_bar.value >= progress_bar.max:
            progress_bar.bar_style = 'success'
            progress_bar.style.bar_color = 'lightgreen'
            label.value = f"{message} -> Finished!"

# Initialize global_vars
global_vars = GlobalVariables()