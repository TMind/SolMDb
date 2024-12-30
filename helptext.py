# Create the guidance text
db_guide_text = """
### **Creating a New Database**

1. **Select a Database:**
    - Use the "Databases" list to select an existing database or leave it empty if you want to create a new one.

2. **Set Your Username:**
    - Enter your username in the "Username" text box. This username will be associated with your Solforge Fusion account.

3. **Choose an Action:**

    - **Load Decks/Fusions:**  
      Select this option to fetch and load decks and fusions from the network. This action is necessary to populate your database with existing data.
    
    - **Create All Fusions:**  
      Choose this option to generate all possible fusions based on the decks currently available in the database. This is helpful for exploring new combinations and strategies.
    
    - **Generate Dataframe:**  
      This option generates a comprehensive dataframe summarizing your decks, fusions, and other related statistics. The dataframe contains all relevant information in a non-structured format.

4. **Execute the Action:**
    - Once you’ve selected the desired action, click the "Execute" button to perform the operation. The system will process your request and update the database accordingly.

5. **Review Data Counts:**
    - The label below the action buttons will display the current counts of decks and fusions in your database, along with the timestamp of the last update. This helps you monitor the content of your database.

### **Button Descriptions**

- **Load Decks/Fusions:**  
  Fetches and loads online decks and fusions into the selected database. Creates a new database if none exists.

- **Create All Fusions:**  
  Creates all possible fusions based on the decks in the database. Useful for exploring new combinations.

- **Generate Dataframe:**  
  Aggregates data from the database into a central dataframe, providing a summary of all relevant statistics.

- **Execute:**  
  Executes the selected action (loading data, creating fusions, or generating the dataframe).
"""

deck_guide_text = """
### **FilterGrid Guide**

The **FilterGrid** is a dynamic filtering tool that allows you to apply custom filters to your data and view the results in an interactive grid. Below is a guide on how to use the FilterGrid and its features.

---

#### **Using the FilterGrid**

1. **Creating and Managing Filters:**
   - The FilterGrid allows you to create multiple filters by defining criteria across different columns of your dataset. Each filter is represented by a row in the filter grid.
   - You can specify conditions for different types of data (e.g., `Creature`, `Spell`, `Forgeborn Ability`) and combine them using logical operators such as `AND`, `OR`, and `+`.
     - **`AND`**: Filters will match only if both surrounding fields are met (mandatory).
     - **`OR`**: Filters will match if either of the surrounding fields is met (optional).
   - Within each field, you can make specific items mandatory or optional:
     - **`+`**: Use `+` to delimit items that must be included in the filter. For example, `+Dragon+` will make "Dragon" a mandatory match.
     - **`-`**: Use `-` to delimit items that are optional. For example, `-Elf-` will make "Elf" an optional match.
   - The **Forgeborn Ability** field is mandatory in every filter row and must be filled in to apply the filter.
   - For each filter, you can decide whether it is active or not by toggling the **Active** checkbox. Only active filters will be applied to the data.

2. **Adding a New Filter Row:**
   - To add a new filter row, click the **"Add Row"** button. A new row will appear in the filter grid where you can define your filter criteria.
   - The available fields include:
     - **Type**: Choose between `Deck` and `Fusion`.
     - **Modifier**, **Creature**, **Spell**: Select the entities or card types that you want to filter.
     - **Forgeborn Ability**: Select specific abilities from the Forgeborn cards.
     - **Data Set**: Choose the dataset to apply the filter to (e.g., `Fusion Tags`).

3. **Removing a Filter Row:**
   - To remove a filter row, select the row you want to remove and click the **"Remove Row"** button. The row will be deleted, and the remaining filters will be automatically adjusted.

4. **Editing Filters:**
   - You can edit any existing filter by clicking on its cells and modifying the content. The filter will be applied in real-time as you make changes.

5. **Visualizing Filtered Data:**
   - Once the filters are applied, the FilterGrid will dynamically generate and display the filtered datasets in individual grids below the filter row. Each grid corresponds to the specific filter applied to the data, bearing the same number.
   - The filtered results are shown in a tabular format, allowing you to analyze the data that meets your specified criteria.

"""

guide_text = {'db': db_guide_text, 'deck': deck_guide_text}