import Card_Library
from Synergy import SynergyTemplate

#def create_fusions(deck1, deck2):
#    deck1 = Fusion(deck1, deck2, deck1.forgeborn)
#    deck2 = Fusion(deck2, deck1, deck2.forgeborn)
#    return (deck1, deck2)

class DeckLibrary:
    def __init__(self, decks):
        self.decks = decks
        self.fusions = self.get_fusions()
        self.synergy_stats = {synergy_name: {'target': {}, 'source': {}} for synergy_name in SynergyTemplate().get_synergies() }
        self.build_stats()

    def get_fusions(self):
        fusions = []
        for deck1 in self.decks:
            for deck2 in self.decks:
                fusion = deck1 + deck2
                if fusion is not None:
                    fusions.append(fusion)
        return fusions

        
                            
    def build_stats(self):
        
        for eval_fusion in self.fusions:
            fusion_synergies = eval_fusion.synergy_collection
            for synergy_name, synergy in fusion_synergies.synergies.items():
                target_count = sum(synergy.get_target_counts().values())
                source_count = sum(synergy.get_source_counts().values())
                if target_count not in self.synergy_stats[synergy_name]['target']:
                    self.synergy_stats[synergy_name]['target'][target_count] = 0
                self.synergy_stats[synergy_name]['target'][target_count] += 1
                if source_count not in self.synergy_stats[synergy_name]['source']:
                    self.synergy_stats[synergy_name]['source'][source_count] = 0
                self.synergy_stats[synergy_name]['source'][source_count] += 1

    def print_fusion_synergies(self):
        for fusion in self.fusions:
            print("========================================")
            print(f"Synergies for fusion '{fusion.name}':\n")
            for synergy_name, synergy in fusion.synergy_collection.synergies.items():
                target_count_max = max(self.synergy_stats[synergy_name]['target'].keys())
                source_count_max = max(self.synergy_stats[synergy_name]['source'].keys())
                source_count     = sum(synergy.get_source_counts().values())
                target_count     = sum(synergy.get_target_counts().values())
                source_ratio     = source_count*100/source_count_max  
                target_ratio     = target_count*100/target_count_max 
                mean_ratio       =  (source_ratio + target_ratio) / 2
                syn_sources_string = f"{synergy.get_source_counts()} / {source_count_max:<4}"
                syn_targets_string = f"{synergy.get_target_counts()} / {target_count_max:<4}"
                print(f"{synergy_name:<15} : {syn_sources_string:>60} [{source_ratio:>3.0f}] ** [{target_ratio:>3.0f}] {syn_targets_string:>60} -> {mean_ratio:>3.0f}")
        
             # check if any synergy is missing in the fusion
            missing_synergies = set(SynergyTemplate().get_synergies()) - set(fusion.synergy_collection.synergies.keys())

            #num_missing = len(missing_synergies)
            #num_syn     = len(fusion.synergy_collection.synergies.items())


            # print missing synergies
            for missing_synergy in missing_synergies:                                
                source_tags = SynergyTemplate().get_source_tags_by_synergy(missing_synergy)
                target_tags = SynergyTemplate().get_target_tags_by_synergy(missing_synergy)

                source_count = 0
                for tag in source_tags:
                    if tag in fusion.synergy_collection.sources:
                        source_count += fusion.synergy_collection.sources[tag]

                target_count = 0
                for tag in target_tags:
                    if tag in fusion.synergy_collection.targets:
                        target_count += fusion.synergy_collection.targets[tag]

                target_count_max = max(self.synergy_stats[missing_synergy]['target'].keys(), default=0)
                source_count_max = max(self.synergy_stats[missing_synergy]['source'].keys(), default=0)                
                source_ratio     = source_count*100/source_count_max if source_count_max else 0 
                target_ratio     = target_count*100/target_count_max if target_count_max else 0

                if (source_count > 0 or target_count > 0):   
                    syn_sources_string = f"{source_count} / {source_count_max:<4}"
                    syn_targets_string = f"{target_count} / {target_count_max:<4}"
                    #print(f"{missing_synergy:<15} : {syn_sources_string:>60} [{source_ratio:>3.0f}] ** [{target_ratio:>3.0f}] {syn_targets_string:>60}")

            nm_mean_p = self.get_normalized_mean_percentage(fusion)
            print(f"Normalized mean percentage: '{nm_mean_p}':\n")

        return


    def get_normalized_mean_percentage(self, fusion):
        normalized_percentages = []
        for synergy_name, synergy in fusion.synergy_collection.synergies.items():
            source_count = sum(synergy.get_source_counts().values())
            target_count = sum(synergy.get_target_counts().values())
            source_ratio = source_count * 100 / max(self.synergy_stats[synergy_name]['source'])
            target_ratio = target_count * 100 / max(self.synergy_stats[synergy_name]['target'])
            normalized_percentages.append((source_ratio + target_ratio) / 2)

        missing_synergies = set(SynergyTemplate().get_synergies()) - set(fusion.synergy_collection.synergies.keys())

        for missing_synergy in missing_synergies:                                
            source_tags = SynergyTemplate().get_source_tags_by_synergy(missing_synergy)
            target_tags = SynergyTemplate().get_target_tags_by_synergy(missing_synergy)

            source_count = 0
            for tag in source_tags:
                if tag in fusion.synergy_collection.sources:
                    source_count += fusion.synergy_collection.sources[tag]

            target_count = 0
            for tag in target_tags:
                if tag in fusion.synergy_collection.targets:
                    target_count += fusion.synergy_collection.targets[tag]

            target_count_max = max(self.synergy_stats[missing_synergy]['target'].keys(), default=0)
            source_count_max = max(self.synergy_stats[missing_synergy]['source'].keys(), default=0)                
            source_ratio     = source_count*100/source_count_max if source_count_max else 0 
            target_ratio     = target_count*100/target_count_max if target_count_max else 0

            normalized_percentages.append(-(source_ratio + target_ratio)/2)



        if len(normalized_percentages) == 0:
            return 0

        return sum(normalized_percentages) / len(normalized_percentages)




                

      
 
    # def evaluate_library(self, synergy_template):
    #     library_syn_pairs = SynergyPairs(synergy_template=synergy_template)
    #     for i in range(len(self.decks)):
    #         for j in range(i+1, len(self.decks)):
    #             deck1_syn_pairs = SynergyPairs.from_deck(self.decks[i], synergy_template=synergy_template)
    #             deck2_syn_pairs = SynergyPairs.from_deck(self.decks[j], synergy_template=synergy_template)
    #             library_syn_pairs += (deck1_syn_pairs * deck2_syn_pairs) / len(self.decks)

    #     return library_syn_pairs.calculate_scores()




from collections import defaultdict

class DeckEvaluator:
    
    def __init__(self, decks):
        self.synergy_template = SynergyTemplate()
        self.synergy_pairs = SynergyCollection(synergy_template=self.synergy_template)
        self.fb_synpairs = {}
        self.synergy_collections = {}
        self.scores = defaultdict(lambda: -1)
        self.decknames = [ deck.name for deck in decks ]

        if decks: 
            #print("===============================================")
            #print(f"Decks:{'|'.join(deck.name for deck in decks)} ")            
            for deck in decks:
                synergies = SynergyCollection.from_deck(deck, synergy_template=self.synergy_template)
                self.synergy_pairs += synergies          
                self.fb_synpairs[deck.forgeborn.title] = SynergyCollection.from_forgeborn(deck.forgeborn, synergy_template=self.synergy_template)

            for fb_name in self.fb_synpairs:                
                #print("----------------------------------------------")
                self.synergy_collections[fb_name] = self.get_synergies(fb_name)
                self.scores[fb_name] = self.calculate_fitness_score(fb_name)                            

 
    def calculate_fitness_score(self, forgeborn_name=None, stats=None):
        synpairs = SynergyCollection(synergy_template=self.synergy_template)
        if forgeborn_name :
            #print(f"Forgeborn: {forgeborn_name}")
            synpairs = self.synergy_pairs + self.fb_synpairs[forgeborn_name]*(1/3)
        else:
            synpairs = self.synergy_pairs

        s = synpairs.calculate_scores(stats)
        a = synpairs.calculate_average(s)   
        p = synpairs.calculate_percentage()
        

        score = int(s*10)
        print(f"{score}: {p}% , {a}ø {s}∑ ")
        #print("==========================================================")
        return score

    def get_synergies(self, fb_name=None):
        synergies = self.synergy_pairs
        if fb_name :
            synergies += self.fb_synpairs[fb_name]
        return synergies 

    def get_name(self):
        return "_".join(self.decknames)
        
    def __str__(self, fb_name=[]):
        fb_names = fb_name
        if not fb_name:
            fb_names = self.fb_synpairs.keys()

        fb_string = ""
        for fb_name in fb_names:
            synpairs = self.synergy_pairs + self.fb_synpairs[fb_name]
            fb_string += f"{fb_name} : \n{str(synpairs)}"

        decknames_string = f"{self.decknames}\n"

        return decknames_string + fb_string
