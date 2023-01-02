from xml.dom import minidom
import re
from pulp import *

parser = minidom.parse('minershaven.xml')
prob = LpProblem('minimize MH cost', LpMinimize)

categories = [
    'wind',
    'water',
    'grass',
    'fire',
    'spirit',
    'death',
]

items = []
rarities = {}
categoryDictionaries = {}

for category in categories:
    categoryDictionaries[category] = {}

def getNodeText(node):
    nodelist = node.childNodes
    result = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            result.append(node.data)
    return ''.join(result)
 
def main():
    input = []
    
    useAdvancedReborns = False
    useRarityAsWeight = False
    slipstreams = []
    exclude = []

    for element in parser.getElementsByTagName('text'):
        elementText = getNodeText(element)
        itemName = getNodeText(element.parentNode.parentNode.getElementsByTagName('title')[0])
        if not '|elements = {{Elements' in elementText or 'Category:Superstitious' in elementText:
            continue
        if 'Category:Slipstream' in elementText and itemName not in slipstreams:
            continue
        if 'Category:Advanced Reborn' in elementText and not useAdvancedReborns:
            print("Skipping advanced reborn: " + itemName)
            continue
        if itemName in exclude:
            continue
        
        relevantText = re.compile('\|elements[^\}\}]*', re.U).search(elementText).group(0)
        shardCostText = re.compile('\|cost[^\n]*', re.U).search(elementText).group(0)
        rarityText = re.compile('\|rarity[^\n]*', re.U).search(elementText).group(0)
        
        integers = re.findall(r'-?\d+', relevantText, re.U)
        rarity = re.search(r'\d+', rarityText, re.U).group(0)
        
        for i in range(len(categories)):
            categoryDictionaries[categories[i]][itemName] = int(integers[i])
        items.append(itemName)
        if useRarityAsWeight:
            rarities[itemName] = 1/int(rarity)
        else:
            rarities[itemName] = 1
        
    vars = LpVariable.dicts('elemenet', items, cat=LpInteger, lowBound=0)
    prob += (
        lpSum(i[1] * vars[i[0]] for i in rarities.items())
    )

    for i in range(len(categories)):
        prob += (
            lpSum(categoryDictionaries[categories[i]][j] * vars[j] for j in items) >= input[i],
            f'{categories[i]} requirement'
        )
        
    prob.solve()
    print("Status:", LpStatus[prob.status])
    for v in prob.variables():
        if v.varValue > 0:
            print(v.name, "=", v.varValue)
           
if __name__ == '__main__':
    main()