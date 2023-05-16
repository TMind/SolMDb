from collections import defaultdict
from Synergy import SynergyTemplate
from Interface import InterfaceCollection

class Evaluation:
    def __init__(self, synergy_stats):
        self.synergy_stats = synergy_stats
  

    def evaluate_deck(self, deck):
        # loop through each synergy in the deck
        print(f"=====================================")
        print(f"Evaluating Deck: {deck.name}")        
        evaluation = defaultdict(lambda: defaultdict(lambda: {'IN': set(), 'OUT': set(), 'SELF': set()}))

        
        synergy_template = SynergyTemplate()

        for i, (card_name_1, card_1) in enumerate(deck.cards.items()):
            for j, (card_name_2, card_2) in enumerate(deck.cards.items()): 
                            
                
                if card_name_1 == card_name_2:

                    synCC_matches = InterfaceCollection.match_synergies(card_1.ICollection, card_2.ICollection)                                        
                    synCF_matches = InterfaceCollection.match_synergies(card_1.ICollection, deck.forgeborn.ICollection)
                    synFC_matches = InterfaceCollection.match_synergies(deck.forgeborn.ICollection, card_1.ICollection)

                    if len(synCC_matches) > 0:                    
                        for synergy, count in synCC_matches.items(): 
                            if count > 0 :
                                ranges = []
                                for cardname, interface in card_1.ICollection.interfaces[synergy].items():                                    
                                    #print(f"Adding Range for {synergy} :: {cardname} :: {interface.name} -> {interface.range}")
                                    ranges.append(interface.range)
                                for range in ranges:
                                    if range == '+' : 
                                        print(f"Range not selfreferential! Omit synergy")
                                        break
                                #print(f"Synergy Match Dict:")    
                                #print(str(synCC_matches))
                                evaluation[card_name_1][synergy]['SELF'].add(card_name_2)                            
                    
                    if len(synCF_matches) > 0:                    
                        for synergy, count in synCF_matches.items():                             
                            if count > 0:
                                evaluation[card_name_1][synergy]['OUT'].add(deck.forgeborn.name)                                                     
                                evaluation[deck.forgeborn.name][synergy]['IN'].add(card_name_1)

                    if len(synFC_matches) > 0:                    
                        for synergy, count in synFC_matches.items():
                            if count > 0:
                                evaluation[deck.forgeborn.name][synergy]['OUT'].add(card_name_1)
                                evaluation[card_name_1][synergy]['IN'].add(deck.forgeborn.name)                                                     
                
                if i < j:
                    # compare only cards whose indices are greater        
                    # Check if the cards have any synergies                
                    #print(f"Matching Cards: {card_1.title} ~ {card_2.title}")
                    c12_matches = InterfaceCollection.match_synergies(card_1.ICollection, card_2.ICollection)
                    #print(f"Matching Cards: {card_2.title} ~ {card_1.title}")
                    c21_matches = InterfaceCollection.match_synergies(card_2.ICollection, card_1.ICollection)

                    if len(c12_matches) > 0 :                        
                        for synergy, count in c12_matches.items():
                            if count > 0:
                                evaluation[card_name_1][synergy]['OUT'].add(card_name_2)                                                     
                                evaluation[card_name_2][synergy]['IN'].add(card_name_1)

                    if len(c21_matches) > 0 :                        
                        for synergy, count in c21_matches.items():
                            if count > 0:
                                evaluation[card_name_2][synergy]['OUT'].add(card_name_1)
                                evaluation[card_name_1][synergy]['IN'].add(card_name_2)


        arrows = {'IN' : '->', 'OUT' : '<-', 'SELF' : '<=>'}

        for card_name, card_eval in evaluation.items():
            print(f"Card: {card_name}")
            for direction in ['IN', 'OUT', 'SELF']:
                card_sets_by_synergy = defaultdict(list)
                for synergy_name, synergy_eval in card_eval.items():
                    card_set = synergy_eval[direction]
                    if len(card_set) > 0:
                        for card in card_set:
                            card_sets_by_synergy[synergy_name].append(card)
                for synergy_name, card_list in card_sets_by_synergy.items():
                    card_names = ", ".join(card for card in card_list)
                    print(f"\t{arrows[direction]} [{synergy_name}] : {card_names}")
  
        return 
