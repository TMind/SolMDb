from collections import defaultdict
from Synergy import SynergyTemplate
import networkx as nx
#import infomap
import csv
import time
import os
from tqdm import tqdm

def find_best_pairs(graphs,outpath):

    deck_combinations = []
    for name, myGraph in graphs.items():        
        deck1, deck2 = name.split('_')
        score = myGraph.avglbl
        deck_combinations.append((deck1, deck2, score))

    # sort deck combinations by score in decreasing order
    deck_combinations.sort(key=lambda x: x[2], reverse=True)

    chosen_combinations = []
    chosen_decks = set()
    total_score = 0

    for deck1, deck2, score in deck_combinations:
        if deck1 not in chosen_decks and deck2 not in chosen_decks:
            # neither deck has been chosen before, so choose this combination
            chosen_combinations.append((deck1, deck2, score))
            total_score += score
            chosen_decks.add(deck1)
            chosen_decks.add(deck2)

    with open(outpath, "w") as select_pair_file:
        select_pair_file.write(f"Total score: {total_score}\n")
        for combo in chosen_combinations:
             select_pair_file.write( f"Chosen combination: {combo[0]}, {combo[1]}, Score: {combo[2]} \n")

def evaluate_graph(my_graph):
  
    # create a dictionary to store labels in each community
    community_labelinfos = defaultdict(list)

   # Iterate over the edges in the graph
    for edge in my_graph.G.edges(data=True):
        # Get locality of edge
        local_faction = edge[2]['local']
        # Get the label(s) of the edge
        labels = edge[2]['label'].split(',')
        # Get the weight of the edge
        total_weight = edge[2]['weight']
         # Calculate weight for each label
        weight_per_label = total_weight / len(labels)
        
        for label in labels:
            community_labelinfos['Community'].append((label.strip(), weight_per_label, local_faction))


    for synergy, interfaces in my_graph.unmatched_synergies.items():        
        total =sum(int(value) for value in interfaces.values())
        community_labelinfos['Community'].append((synergy, -total, 0))

    # Calculate the total number of community labels and the average number of labels per community
    total_nr_community_labels = sum(len(labelinfos) for labelinfos in community_labelinfos.values())

    my_graph.avglbl = total_nr_community_labels
    my_graph.community_labels = community_labelinfos

    return my_graph

def calculate_weight(synergy, count):

    syn = SynergyTemplate().get_synergy_by_name(synergy)
    return count * syn.weight


def export_csv(csvname, my_graphs, local_mode=False):
   
    # Get all labels from the SynergyTemplate
    synergy_template = SynergyTemplate()
    all_labels = list(synergy_template.synergies.keys())

    
    # Define the fieldnames for the CSV
    fieldnames = ["deckname1", "deckname2","forgeborn", "L2", "L3", "L4", "factions", "numlbl", "#>~1stats", "#>~2stats", "#>~3stats", 
                  #"seeks1", "seeks2", "seeks3", "seeks4", 
                  "Creatures", "Spells"]
    # Add columns for each label before and after
    for label in all_labels:
        #fieldnames.append(f"{label}_OUT->")        
        fieldnames.append(f"{label}")
        #fieldnames.append(f"{label}_<-IN")
        

    # Create an in-memory CSV writer
    from io import StringIO
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames = fieldnames, delimiter=';')
    writer.writeheader()

    # Create a tqdm instance for the loop
    progress_bar = tqdm(my_graphs.items(), total=len(my_graphs), desc=f"Exporting CSV {os.path.basename(csvname)}", mininterval=0.1, colour='RED')

    for i, (key, MyGraph) in enumerate(progress_bar):         

        #Composition of Fusion 
        composition = MyGraph.fusion.composition
        #Determine decknames                                    
        deckname1, *rest = MyGraph.name.split('_')
        deckname2 = rest[0] if rest else None

        num_creatures = composition['Creature']
        num_spells    = composition['Spell']
        above_stats1  = f"{composition['1attack']}/{composition['1health']}"
        above_stats2  = f"{composition['2attack']}/{composition['2health']}"
        above_stats3  = f"{composition['3attack']}/{composition['3health']}"

        # Create a dictionary mapping labels to weights
        community_labels = MyGraph.community_labels
        label_weights = defaultdict(float)
        for label_info in community_labels.values():
            for label, weight, loc_faction in label_info:
                if loc_faction and local_mode: continue
                label_weights[label] += weight
                    
        max_graph_ranges = [syn for syn_list in MyGraph.max_ranges.values() for syn in syn_list.split(',') if syn]

        # Ensure the list has at least 3 elements
        #max_graph_ranges += [''] * (3 - len(max_graph_ranges))

        range1 = max_graph_ranges[0] if len(max_graph_ranges) > 0 else ''
        range2 = max_graph_ranges[1] if len(max_graph_ranges) > 1 else ''
        range3 = max_graph_ranges[2] if len(max_graph_ranges) > 2 else ''
        range4 = ', '.join(max_graph_ranges[3:]) if len(max_graph_ranges) > 3 else ''

        ability = {}
        for ability_name in MyGraph.fusion.forgeborn.abilities:
            level = ability_name[0]
            if "Inspire" in ability_name and ability.get(level): continue                
            ability[level] = ability_name
        
        row = {
            "deckname1": deckname1,
            "deckname2": deckname2,
            "forgeborn": MyGraph.forgeborn_name,
            "L2" : ability['2'],
            "L3" : ability['3'],
            "L4" : ability['4'],
            "factions":  MyGraph.faction,
            "numlbl": MyGraph.avglbl,
            "#>~1stats": above_stats1,
            "#>~2stats": above_stats2,
            "#>~3stats": above_stats3,
            # "seeks1": range1,
            # "seeks2": range2,
            # "seeks3": range3,
            # "seeks4": range4,
            "Creatures": num_creatures,
            "Spells": num_spells
        }

        # Add label weights to the row
        for label in all_labels:

            #output_tags = synergy_template.get_output_tags_by_synergy(label)
            #deck1_count = 0
            #deck2_count = 0

            #for tag in output_tags:
            #    deck1_count += compositions[deckname1].setdefault(tag,0) 
            #    deck2_count += compositions[deckname2].setdefault(tag,0)
            
            #row[f"{label}_1"] = deck1_count                
            input = len(MyGraph.matched_synergies.get(label,[]))
            
            weight = int(label_weights.get(label, 0))  
            
            row[label] = weight
            #row[f"{label}_<-IN"] = input            

        writer.writerow(row)
        time.sleep(0.001)

    progress_bar.close()

    csv_content = csv_buffer.getvalue()
    csv_buffer.close()

    # Split the CSV content into lines
    csv_lines = csv_content.strip().split('\n')

    # Modify the header row with custom headers
    header = csv_lines[0].split(';')
    custom_headers = {
        key: key.split('_')[-1]
        for key in header
    }
    header = [custom_headers.get(header_item, header_item) for header_item in header]

    # Replace the header row in the CSV content
    csv_lines[0] = ';'.join(header)

    # Write the final CSV content to the output file
    with open(f"{csvname}.csv","w", newline="") as csvfile:
        csvfile.write('\n'.join(csv_lines))
