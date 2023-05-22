import csv
import re

# Define the input and output file names.
input_filename = 'sff.csv'
output_filename = 'sff_clean.csv'



def read_entities_from_csv(csv_path):
    entities = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            entities.append(row)
    return entities

entities = read_entities_from_csv('sff.csv')
print(entities[1])

if (0):

    # Open the input and output files.
    with open(input_filename, 'r') as infile, open(output_filename, 'w', newline='') as outfile:
        # Create a CSV reader and writer.
        reader = csv.reader(infile)
        writer = csv.writer(outfile, quotechar=None, quoting=csv.QUOTE_NONE, escapechar='\\')

        for row in reader:
            # Clean each field in the row.
            cleaned_row = [re.sub(r'[^\x20-\x7E]', '', field) for field in row]
            # Write the cleaned row to the output file.
            writer.writerow(cleaned_row)

