from IPython.display import display, HTML

from IPython.display import HTML, display
import os

# Function to inject CSS from a file
def inject_css(css_file_path):
    if os.path.exists(css_file_path):
        with open(css_file_path, 'r') as f:
            css = f.read()
        # Suppress the output from display
        try:
            display(HTML(f"<style>{css}</style>"))
        except Exception as e:
            print(f"Failed to inject CSS: {e}")

# # Function to inject CSS from a file
# def inject_css(css_file_path):
#     with open(css_file_path, 'r') as f:
#         css = f.read()
#     display(HTML(f"<style>{css}</style>"))

# Inject initial CSS files
inject_css('custom/custom.css')

class CSSManager:
    def __init__(self):
        self.css_classes = {}

    def create_and_inject_css(self, class_name, column_selector='', header_height=140):
        """
        Creates and injects CSS for a specific class.

        Parameters:
        - class_name: A unique name for the CSS class.
        - column_selector: A CSS selector to target specific columns (e.g., by ID or class).
        - header_height: The height to apply to the headers (in pixels).

        Returns:
        - The name of the generated CSS class.
        """
        if column_selector and not column_selector.startswith('.'):
            column_selector = f'.{column_selector}'

        # Generate the CSS style as a string
        style = f"""
        <style>
            .{class_name} .slick-header-column {{
                height: {header_height}px !important;
                text-align: left !important;
                vertical-align: bottom !important;
            }}
            
            /* Position the sort indicator at the bottom of the rotated column */
            .{class_name} .slick-header-column .slick-sort-indicator {{
                position: absolute !important;
                bottom: 10px !important; /* Position at the bottom */
                left: 50% !important; /* Center horizontally */
                transform: translateX(-100%) !important; /* Proper centering */
                display: inline-block !important;
                visibility: visible !important;
                font-size: 20px !important; /* Adjust size as needed */
                z-index: 2; /* Ensure it's above other elements */
                color: blue !important; /* Adjust color */
            }}
            
            .{class_name} {column_selector} .slick-column-name {{
                display: inline-block !important;
                transform-origin: bottom left !important;
                white-space: nowrap !important;
                transform: rotate(90deg) !important;
                margin-top: 10px !important;
            }}
        </style>
        """
        display(HTML(style))
        self.css_classes[class_name] = column_selector
        return class_name



    def apply_css_to_widget(self, widget, class_name):
        """
        Applies the CSS class to the qgrid widget.

        Parameters:
        - widget: The qgrid widget to apply the CSS class.
        - class_name: The CSS class name to apply.
        """
        if class_name in self.css_classes:
            widget.add_class(class_name)
        else:
            print(f"CSS class '{class_name}' does not exist.")

    def needs_custom_styles(self, qgrid_widget, column_selector=''):
        """
        Checks if there are any columns in the qgrid widget that need a custom style.

        Parameters:
        - qgrid_widget: The qgrid widget to check.
        - column_selector: A CSS selector to target specific columns (e.g., by ID or class).

        Returns:
        - True if any columns have the column_selector, False otherwise.
        """
        found_matching_columns = False
        df = qgrid_widget.get_changed_df()
        
        for column in df.columns:
            column_definition = qgrid_widget.column_definitions.get(column, {})
            if 'headerCssClass' in column_definition and column_definition['headerCssClass'] == column_selector:
                found_matching_columns = True
                break

        return found_matching_columns

    def apply_conditional_class(self, qgrid_widget, condition, custom_class):    
        if self.needs_custom_styles(qgrid_widget, condition):
            self.apply_css_to_widget(qgrid_widget, custom_class)            
        else:
            qgrid_widget.remove_class(custom_class)

    def apply_column_styles(self, qgrid_widget, sorted_columns=[], filtered_columns=[]):
        """
        Apply custom CSS styles to columns that are sorted or filtered.
        """
        column_definitions = qgrid_widget.column_definitions

        # Apply CSS class for sorted columns
        for sort_col in sorted_columns:
            column_definitions[sort_col]['cssClass'] = 'sorted-column'

        # Apply CSS class for filtered columns
        for filter_col in filtered_columns:
            column_definitions[filter_col]['cssClass'] = 'filtered-column'

        return column_definitions
    
    def get_column_definitions_with_gradient(self, column_definitions, sorting_info):
        """
        Update the column definitions with custom CSS for sorted columns.
        Applies a vertical gradient to the header based on the sorting direction,
        and applies a static background color to the column cells that matches the header's gradient.
        """
        
        # CSS classes for ascending and descending sorts
        ascending_header_class = 'sorted-column-header-ascending'
        descending_header_class = 'sorted-column-header-descending'
        
        # Static cell color classes for ascending and descending sorts
        ascending_cell_class = 'sorted-column-cells-ascending'
        descending_cell_class = 'sorted-column-cells-descending'

        # Loop over each sorted column to apply or update the gradient in the header and static color in the cells
        for col_name, sort_info in sorting_info.items():
            if col_name in column_definitions:
                # Determine the new CSS class based on the current ascending state
                if sort_info['ascending']:
                    new_header_class = ascending_header_class
                    #new_cell_class = ascending_cell_class
                    old_header_class = descending_header_class
                    #old_cell_class = descending_cell_class
                else:
                    new_header_class = descending_header_class
                    #new_cell_class = descending_cell_class
                    old_header_class = ascending_header_class
                    #old_cell_class = ascending_cell_class

                # Get the current headerCssClass
                existing_header_class = column_definitions[col_name].get('headerCssClass', '')

                # Add the new header class for gradient and ensure no duplicates
                updated_header_class = add_css_class(existing_header_class, new_header_class)

                # Remove the old gradient class from the header
                updated_header_class = remove_css_class(updated_header_class, old_header_class)

                # Get the current cssClass (for cells)
                existing_cell_class = column_definitions[col_name].get('cssClass', '')

                # Apply static color to the cells in the sorted column
               # updated_cell_class = add_css_class(existing_cell_class, new_cell_class)

                # Apply general sorted column style if needed (optional for borders)
                #updated_cell_class = add_css_class(updated_cell_class, 'sorted-column')

                # Remove old cell color class to avoid duplication
                #updated_cell_class = remove_css_class(updated_cell_class, old_cell_class)

                print(f"Updated CSS for column {col_name}: Header = {updated_header_class}")                
                # Update the column definition with the new classes
                column_definitions[col_name]['headerCssClass'] = updated_header_class
                #column_definitions[col_name]['cssClass'] = updated_cell_class

        return column_definitions

# Global functions

def add_css_class(existing_class, new_class):
    """Helper function to append a CSS class without duplication."""
    classes = existing_class.split() if existing_class else []
    if new_class not in classes:
        classes.append(new_class)
    return " ".join(classes)

def remove_css_class(existing_class, old_class):
    """Helper function to remove a CSS class."""
    classes = existing_class.split() if existing_class else []
    if old_class in classes:
        classes.remove(old_class)
    return " ".join(classes)