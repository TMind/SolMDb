import math
from itertools import islice
from scipy.stats import hypergeom
from Synergy import SynergyTemplate


def product(l):
    x = 1
    for y in l:        
        x *= y
    print(f"product of {l} = {x}")        
    return x

def calc_prob(s, t, N, n, m, C ):
    # Calculate probability of drawing at least n target cards and at most m source cards
    p_target_at_least_n = 1 - hypergeom.cdf(k=n-1, M=N, n=t, N=C)
    p_source_at_most_m = hypergeom.cdf(k=m, M=N, n=s, N=C)

    # Calculate probability of meeting condition
    p_meeting_condition = p_target_at_least_n * p_source_at_most_m

    return p_meeting_condition


def calc_synergy_validity(synergy):

    s = sum(synergy.get_source_counts().values())
    t = sum(synergy.get_target_counts().values())

    p_cond_1 = []
    p_cond_2 = [0]
    
    inverse = 1
    result = []
    
    if synergy.name == 'SPELL':       
        inverse = 0
        
        sources = [s]
        for k in range(2):
            pmf = []        
            for j in range(min(s+1,5)):            
                p_source = hypergeom.pmf(k=j, M=20-5*k, n=s, N=5)
                pmf.append(p_source)                 

            sources_drawn = sum([pmf[i] * i for i in range(min(int(s)+1,5))])
            #print(pmf)    
            #print(f"Most probably number of sources drawn from {s}: {sources_drawn}")
            s -= round(sources_drawn) #pmf.index(max(pmf))             
            sources.append(s)

        #print(f"Sources drawn over three turns: {sources}")
        #for p in pmf:
        #    print(f"Probality: {pmf.index(p)} -> {p} ")
        #print(f"Final draw: {pmf.index(max(pmf))}")    

        for i in range(3):          
        
            p_source = 1 - hypergeom.cdf(0, M=20-5*i, n=sources[i], N=5)         # At least one source               
            p_target = 1 - hypergeom.cdf(0, M=20-5*i, n=t, N=5)         # At least one target

            if math.isnan(p_source): p_source = 0
            if math.isnan(p_target): p_target = 0

            #print(f"Ps(>0/{sources[i]}) = {p_source}\n"
            #      f"Pt(>0/({t}) = {p_target}\n"
            #      f"product = {p_source*p_target}"
            #)
            
            p_cond_1.append(p_source * p_target)       # Both source and target
            p_cond_2.append(p_target)               # Neither source nor target
            
            prod_p_2 = math.prod([ 1-p_cond_2[j] for j in range(i+1) ]) 
            #prod_p_2 = math.prod([(1 - p) for p in list(islice(p_cond_2,0,i))])     

            #äprint(f"Drawing Both in Turn {i} : {p_source} * {p_target} = {p_cond_1[i]} | {p_cond_2[i]} => {prod_p_2}")
            
    else:

        #p_cond_2[0] = 0# Calculate probability of meeting condition in a single turn
        for i in range(3):
            p1 = calc_prob(s, t, 20-5*i, 1, 0, 5)                  # No source                         
            p2 = 1 - hypergeom.pmf(0, M=20-5*i, n=t, N=5)        # At least one target     
            if math.isnan(p1): p1 = 0
            if math.isnan(p2): p2 = 0
            p_cond_1.append(p1)           
            p_cond_2.append(p2)            
                       
    for i in range(3):
        #print(f"P2 = {list(islice(p_cond_2,0,i+1))}")
        #print(f"P1 = {list(islice(p_cond_1,0,i+1))}")
        prod_p_cond_2 = math.prod([1 - p_cond_2[j] for j in range(i+1)])
        #prod_p_cond_2 = math.prod([(1 - p) for p in list(islice(p_cond_2,i))])
        result.append(prod_p_cond_2 * p_cond_1[i])
        #print(f"Target only/general {i}: {p_cond_1[i]} * {p_cond_2[i]} = {prod_p_cond_2} -> Result {result[i]}") 

    #p_cond_123 = sum([s for s in list(islice(result,0,2))])
    p_cond_123 = sum([result[i] for i in range(3)])
    
    #p_cond_123 = (                                            p_cond_1[0] + 
    #                (1 - p_cond_2[1]) *                       p_cond_1[1] + 
    #                (1 - p_cond_2[1]) * (1 - p_cond_2[2]) *   p_cond_1[2]   )

    #print( f"Synergy validity: {1 - p_cond_123 if inverse else p_cond_123}")
    return 1 - p_cond_123 if inverse else p_cond_123



class Evaluation:
    def __init__(self, synergy_stats):
        self.synergy_stats = synergy_stats
  

    def evaluate_synergy(self, synergy):
        source_count = sum(synergy.get_source_counts().values())
        target_count = sum(synergy.get_target_counts().values())
       
        synergy_prob = calc_synergy_validity(synergy)  
        target_prob = 0
        if synergy_prob > 0.5 :        
            t_cond1 = [1 - hypergeom.cdf(k=0, M=20-5*i, n=target_count, N=5) for i in range(2)]
            t_cond2 = [0] + t_cond1
            target_prob  = sum([ (1 - t_cond2[j]) * t_cond1[j]  for j in range(2)  ])
              
        total_prob = synergy_prob * target_prob * 100     
        
        print(f"{synergy.name:<15}: {source_count} / {target_count} -> Validity: {synergy_prob:.2f} => Target: {target_prob:.2f} => {total_prob:.2f} ")
        return  total_prob
    

    def evaluate_deck(self, deck):
        # loop through each synergy in the deck
        print(f"=====================================")
        print(f"Evaluating Deck: {deck.name}")
        synergy_total = 0

        #total_sources = set(deck.synergy_collection.sources.keys())
        #total_targets = set(deck.synergy_collection.targets.keys())

        for synergy in deck.synergy_collection.synergies.values():
            synergy_total += self.evaluate_synergy(synergy)
            #total_sources -= set(synergy.source_counts.keys())
            #total_targets -= set(synergy.target_counts.keys())

        #total_sources_sum = sum(deck.synergy_collection.sources[source] for source in total_sources)
        #total_targets_sum = sum(deck.synergy_collection.targets[target] for target in total_targets)

        #percentage_sources = total_sources_sum / sum(deck.synergy_collection.sources.values())
        #percentage_targets = total_targets_sum / sum(deck.synergy_collection.targets.values())
                
        #print(f"Missing percentage of sources : {percentage_sources * 100 :.2f}%")
        #print(f"Missing percentage of targets:  {percentage_targets * 100 :.2f}%")

        #synergy_total *= (1 -  percentage_targets) * (1 - percentage_sources)

        print(f"{synergy_total} <- Total synergy ")

        return synergy_total
