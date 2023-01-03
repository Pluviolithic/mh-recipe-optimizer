from xml.dom import minidom
from os.path import exists
from pulp import *
import argparse
import math
import re

parser = argparse.ArgumentParser(
    description = 'Optimize the cost of a supersitious item in Miners Haven.'
)
parser.add_argument('item', type=str, help='The item to optimize for.', nargs='+')
parser.add_argument('-a', '--advanced', action='store_true', help='Use advanced reborns.')
parser.add_argument('-r', '--rarity', action='store_true', help='Use rarity as weight.')
parser.add_argument('-s', '--shards', action='store_true', help='Use shards as weight.')

args = parser.parse_args()

categories = [
    'aether',
    'water',
    'earth',
    'fire',
    'order',
    'entropy',
]

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
    price = []
    items = []
    exclude = []
    rarities = {}
    
    itemToOptimize = ' '.join(args.item)
    
    exclusionsFile = open('exclude.txt', 'r')
    for line in exclusionsFile:
        if line.startswith('//') or len(line.strip()) == 0:
            continue
        exclude.append(line.replace('\n', ''))
    
    if not exists('minershaven.xml'):
        os.system('python3 ScrapeFandom\\ScrapeFandom.py minershaven')
    
    parser = minidom.parse('minershaven.xml')
    prob = LpProblem('minimize MH cost', LpMinimize)

    for element in parser.getElementsByTagName('text'):
        elementText = getNodeText(element)
        itemName = getNodeText(element.parentNode.parentNode.getElementsByTagName('title')[0])
        
        if not '|elements = {{Elements' in elementText:
            continue
        if 'Category:Advanced Reborn' in elementText and not args.advanced:
            continue
        if itemName in exclude:
            continue
        
        relevantText = re.compile('\|elements[^\}\}]*', re.U).search(elementText).group(0)
        integers = re.findall(r'-?\d+', relevantText, re.U)
        
        if 'Category:Superstitious' in elementText:
            if itemName == itemToOptimize:
                price = [int(i) for i in integers]
            continue
        
        shardCostText = re.compile('\|cost[^\n]*', re.U).search(elementText).group(0)
        rarityText = re.compile('\|rarity[^\n]*', re.U).search(elementText).group(0)
        shardCost = int(re.search(r'\d+', shardCostText, re.U).group(0))
        rarity = int(re.search(r'\d+', rarityText, re.U).group(0))
        
        for i in range(len(categories)):
            categoryDictionaries[categories[i]][itemName] = int(integers[i])
            
        items.append(itemName)
        
        if args.rarity:
            rarities[itemName] = 1/rarity
        elif args.shards:
            rarities[itemName] = shardCost
        else:
            rarities[itemName] = 1
            
    if len(price) == 0:
        return
        
    vars = LpVariable.dicts('elemenet', items, cat=LpInteger, lowBound=0)
    prob += (
        lpSum(i[1] * vars[i[0]] for i in rarities.items())
    )

    for i in range(len(categories)):
        prob += (
            lpSum(categoryDictionaries[categories[i]][j] * vars[j] for j in items) >= price[i],
            f'{categories[i]} requirement'
        )
    
    prob.solve()
    print("Status:", LpStatus[prob.status])
    for v in prob.variables():
        if v.varValue > 0:
            name = v.name.replace('elemenet_', '').replace('_', ' ')
            print(name, "=", math.trunc(v.varValue))
           
if __name__ == '__main__':
    main()