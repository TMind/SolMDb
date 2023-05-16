from Evaluation import Evaluation
from Synergy import SynergyTemplate
class DeckLibrary:
    def __init__(self, decks):
        self.decks = decks
        self.fusions = self.get_fusions()
        self.synergy_stats = {synergy_name: {'target': {}, 'source': {}} for synergy_name in SynergyTemplate().get_synergies() }
        #self.build_stats()
        self.evaluator = Evaluation(self.synergy_stats)

    def get_fusions(self):
        fusions = []
        for deck1 in self.decks:
            for deck2 in self.decks:
                fusion = deck1 + deck2
                if fusion is not None:
                    fusions.append(fusion)
        return fusions

    def evaluate_decks(self):
        evaluation = {}
        for fusion in self.fusions:
            score = self.evaluator.evaluate_deck(fusion)
            evaluation[fusion.name]  = score
            print(f"Deck Evaluation added: {fusion.name} {score}")
        return evaluation

    def get_best_synergies(self):

        best_synergy_decks = { synergy : [] for synergy in SynergyTemplate().synergies}
      
        for synergy in SynergyTemplate().synergies:  
            max_percentage = 0 
            for fusion in self.fusions:                  
                if synergy in fusion.ICollection.synergies:
                    deck_synergy = fusion.ICollection.synergies[synergy] 
                    p = Evaluation(self.synergy_stats).evaluate_synergy(deck_synergy)
                    if p == max_percentage :
                        best_synergy_decks[synergy].append(fusion)     
                    if p > max_percentage :
                        max_percentage = p
                        best_synergy_decks[synergy] = [fusion] 
                    

        for synergy, fusions in best_synergy_decks.items():
            for fusion in fusions:
                deck_synergy = fusion.ICollection.synergies[synergy]
                sources = sum(deck_synergy.get_source_counts().values())
                targets = sum(deck_synergy.get_target_counts().values())
                print(f"Synergy: {synergy} in '{fusion.name}' = {sources} / {targets} =>  {Evaluation(self.synergy_stats).evaluate_synergy(deck_synergy)}")

    def print_fusion_synergies(self):
        for fusion in self.fusions:
            print("========================================")
            print(f"Synergies for fusion '{fusion.name}':\n")
            for synergy_name, synergy in fusion.ICollection.synergies.items():
                target_count_max = max(self.synergy_stats[synergy_name]['target'].keys())
                source_count_max = max(self.synergy_stats[synergy_name]['source'].keys())
                source_count     = sum(synergy.get_source_counts().values())
                target_count     = sum(synergy.get_target_counts().values())
                source_ratio     = source_count*100/source_count_max  
                target_ratio     = target_count*100/target_count_max 
                mean_ratio       =  (source_ratio + target_ratio) / 2
                syn_sources_string = f"{synergy.get_source_counts()} / {source_count_max:<4}"
                syn_targets_string = f"{synergy.get_target_counts()} / {target_count_max:<4}"
                print(f"{synergy_name:<15} : {syn_sources_string:>50} [{source_ratio:>3.0f}] ** [{target_ratio:>3.0f}] {syn_targets_string:>50} -> {mean_ratio:>3.0f}")
        
             # check if any synergy is missing in the fusion
            missing_synergies = set(SynergyTemplate().get_synergies()) - set(fusion.ICollection.synergies.keys())

            # print missing synergies
            for missing_synergy in missing_synergies:                                
                source_tags = SynergyTemplate().get_output_tags_by_synergy(missing_synergy)
                target_tags = SynergyTemplate().get_input_tags_by_synergy(missing_synergy)

                source_count = 0
                for tag in source_tags:
                    if tag in fusion.ICollection.sources:
                        source_count += fusion.ICollection.sources[tag]

                target_count = 0
                for tag in target_tags:
                    if tag in fusion.ICollection.targets:
                        target_count += fusion.ICollection.targets[tag]

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
            self.evaluator.evaluate_deck(fusion)
        return
