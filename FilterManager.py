class FilterManager:
    def __init__(self, qgrid_widget):
        """
        Initializes the FilterManager to manage filters for a given QGrid instance.
        Stores filters and ensures QGridNext applies them properly when reapplied.
        """
        self.qgrid_widget = qgrid_widget
        self.active_filters = {}  # Stores active filters

        # Attach event listener for filter changes
        self.qgrid_widget.on('filter_changed', self._handle_filter_change)

    def _handle_filter_change(self, event, qgrid_widget):
        """
        Stores filter changes when they occur in QGrid.
        Ensures that filters can be reapplied later.
        """
        column = event['column']
        filter_info = qgrid_widget._columns[column].get('filter_info', {})

        # Store the filter settings for reapplication
        self.active_filters[column] = filter_info
        print(f"Stored filter for {column}: {filter_info}")

    def apply_filters(self):
        """
        Reapplies stored filters, updates the DataFrame, and ensures the UI highlights filtered columns correctly.
        """
        print("\n🔁 Reapplying stored filters...\n")

        if not self.active_filters:
            print("❌ No active filters found. Skipping filtering step.")
            return

        print(f"📊 Current DataFrame shape before filtering: {self.qgrid_widget.df.shape}")

        # Start with the unfiltered DataFrame to ensure correctness
        filtered_df = self.qgrid_widget._unfiltered_df.copy()

        for column, filter_info in self.active_filters.items():
            print(f"\n🔍 Processing filter for column: {column} with info: {filter_info}")

            if column not in filtered_df.columns:
                print(f"⚠ Warning: Column '{column}' no longer exists. Skipping.")
                continue

            # Ensure indices are lists to avoid NoneType errors
            selected_indices = filter_info.get('selected', []) or []
            excluded_indices = filter_info.get('excluded', []) or []

            print(f"✅ Selected Indices: {selected_indices}, ❌ Excluded Indices: {excluded_indices}")

            # Fetch all unique values from the original dataset
            all_values = self.qgrid_widget._unfiltered_df[column].dropna().astype(str).unique().tolist()
            unique_sorted_values = sorted(all_values)

            if not unique_sorted_values:
                print(f"⚠ Warning: No unique values found for '{column}'. Skipping.")
                continue

            # Convert selected indices into actual values
            selected_values = [unique_sorted_values[i] for i in selected_indices if i < len(unique_sorted_values)]
            excluded_values = [unique_sorted_values[i] for i in excluded_indices if i < len(unique_sorted_values)]

            print(f"✅ Selected Values: {selected_values}")
            print(f"❌ Excluded Values: {excluded_values}")

            # Apply filtering logic
            if selected_values:
                filtered_df = filtered_df[filtered_df[column].isin(selected_values)]
            if excluded_values:
                filtered_df = filtered_df[~filtered_df[column].isin(excluded_values)]

            print(f"📊 Remaining rows after filtering '{column}': {filtered_df.shape[0]}")

            # Step 3: Apply filter in Qgrid backend (if available)
            if hasattr(self.qgrid_widget, '_handle_change_filter'):
                print(f"⚙️ Applying backend filter logic for column: {column}")
                self.qgrid_widget._handle_change_filter({
                    'field': column,
                    'filter_info': filter_info
                })
            else:
                print(f"⚠ WARNING: `_handle_change_filter` not found in QgridWidget!")

            # Step 4: Send `change_filter` event to frontend UI
            print(f"📡 [Frontend] Sending 'change_filter' → Column: {column}")
            self.qgrid_widget.send({
                'type': 'change_filter',
                'field': column,
                'filter_info': filter_info
            })

            # Step 5: Trigger `send_filter_changed()` on frontend
            print(f"📡 [Frontend] Triggering 'send_filter_changed' → {column}")
            self.qgrid_widget.send({
                'type': 'send_filter_changed',
                'field': column
            })

        # Step 6: Ensure the UI removes duplicated index columns
        if 'qgrid_unfiltered_index' in filtered_df.columns:
            print("⚠ Removing duplicate 'qgrid_unfiltered_index' before updating Qgrid.")
            filtered_df = filtered_df.drop(columns=['qgrid_unfiltered_index'])

        # Step 7: Assign filtered DataFrame to the widget
        print("\n📊 Updating Qgrid widget with the filtered DataFrame...")
        self.qgrid_widget.df = filtered_df
        print(f"✅ Updated grid with {filtered_df.shape[0]} rows and {filtered_df.shape[1]} columns.")

        # Step 8: Ensure filters are recognized as active
        print("📡 Checking if any filters are active on frontend...")
        self.qgrid_widget.send({'type': 'check_active_filters'})

        # Step 9: Refresh the UI to ensure it reflects applied filters
        print("🔄 Updating table and triggering refresh.")
        self.qgrid_widget._update_table(triggered_by='apply_stored_filters')
        self.qgrid_widget.send({'type': 'refresh_widgets'})  # Ensure frontend fully refreshes

        print("\n✅ Finished applying filters.\n")

    def clear_filters(self, clear_memory=False):
        """
        Clears all filters in the UI but optionally keeps them stored in memory.
        
        Args:
            clear_memory (bool): If True, completely removes stored filters.
        """
        if clear_memory:
            self.active_filters.clear()  # Remove stored filters
            print("❌ All filters cleared from memory.")

        self.qgrid_widget._df = self.qgrid_widget._unfiltered_df.copy()
        self.qgrid_widget._update_table(triggered_by="clear_filters")
        
        print("✅ Filters cleared from UI, but stored filters remain intact.")

    def get_active_filters(self):
        """
        Returns the currently stored filters.
        """
        return self.active_filters

    def set_active_filters(self, filters):
        """
        Manually sets and applies filters.
        """
        self.active_filters = filters
        self.apply_filters()
        print("Filters manually set and applied.")