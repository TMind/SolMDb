import ipywidgets as widgets
from IPython.display import display

username = 'enterUsernameHere'
uri = "mongodb://localhost:27017"
myDB = None
commonDB = None
progress_containers = {}
tqdmBar = None
debug = False

def get_or_create_progress_container(identifier, description=None):
    global progress_containers
    if identifier not in progress_containers:
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
        progress_containers[identifier] = {'container': hbox, 'progress_bar': progress_bar, 'label': label}
        # Display the new HBox
        display(hbox)
    return progress_containers[identifier]

def update_progress(identifier, value=None, total=None, message=None):
    container = get_or_create_progress_container(identifier)
    progress_bar = container['progress_bar']
    label = container['label']

    if message:
        label.value = message
    if total is not None:
        progress_bar.max = total
    if value is not None:
        progress_bar.value = value
        if value == 0 :
            progress_bar.bar_style = 'info'
            progress_bar.style.bar_color = 'lightblue'
    else:
        progress_bar.value += 1  # Auto-increment if no value provided

    if progress_bar.value >= progress_bar.max:
        progress_bar.bar_style = 'success'
        progress_bar.style.bar_color = 'lightgreen'
        label.value = f"{message} -> Finished!"