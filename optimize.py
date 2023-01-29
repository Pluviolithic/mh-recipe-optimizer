from xml.dom import minidom
from pulp import *

import argparse
import math
import re
import os

parser = argparse.ArgumentParser(
    description = 'Optimize the cost of a supersitious item in Miners Haven.'
)
parser.add_argument('item', type=str, help='The item to optimize for.', nargs='+')
parser.add_argument('-a', '--advanced', action='store_true', help='Use advanced reborns.')
parser.add_argument('-r', '--rarity', action='store_true', help='Use rarity as weight.')
parser.add_argument('-s', '--shards', action='store_true', help='Use item sell value in shards as weight.')
parser.add_argument('-b', '--buy', action='store_true', help='Use item buy value in shards as weight.')
parser.add_argument('-p' '--problem', action='store_true', help='Output the problem specifics.')

args = parser.parse_args()

categories = [
    'aether',
    'water',
    'earth',
    'fire',
    'order',
    'entropy',
]

itemShardCosts = {}
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
    
    slipstreamItem = ''
    itemToOptimize = ' '.join(args.item)
    
    exclusionsFile = open('exclude.txt', 'r')
    for line in exclusionsFile:
        if line.startswith('//') or len(line.strip()) == 0:
            continue
        exclude.append(line.replace('\n', ''))
    
    if not os.path.exists('minershaven.xml'):
        os.system('python3 ' + os.path.join('ScrapeFandom', 'ScrapeFandom.py') + ' minershaven')
    
    parser = minidom.parse('minershaven.xml')
    prob = LpProblem('minimize MH cost', LpMinimize)

    for element in parser.getElementsByTagName('text'):
        elementText = getNodeText(element)
        itemName = getNodeText(element.parentNode.parentNode.getElementsByTagName('title')[0])
        
        if not '|elements = {{Elements' in elementText:
            continue
        if '[[Category:Advanced Reborn]]' in elementText and not args.advanced:
            continue
        if itemName in exclude:
            continue
        
        relevantText = re.compile('\|elements[^\}\}]*', re.U).search(elementText).group(0)
        integers = re.findall(r'-?\d+', relevantText, re.U)
        
        if '[[Category:Superstitious]]' in elementText:
            if itemName == itemToOptimize:
                price = [int(i) for i in integers]
            continue
        
        if '[[Category:Slipstream]]' in elementText:
            slipstreamItem = itemName
            rarities[itemName] = 0
            for i in range(len(categories)):
                categoryDictionaries[categories[i]][itemName] = int(integers[i])
            
            items.append(itemName)
            itemShardCosts[itemName] = (0, 0)
            continue
        
        shardSellText = re.compile('\|sell[^\n]*', re.U).search(elementText).group(0)
        shardBuyText = re.compile('\|cost[^\n]*', re.U).search(elementText).group(0)
        rarityText = re.compile('\|rarity[^\n]*', re.U).search(elementText).group(0)
        
        shardSellValue = int(re.search(r'\d+', shardSellText, re.U).group(0))
        shardBuyValue = int(re.search(r'\d+', shardBuyText, re.U).group(0))
        rarity = int(re.search(r'\d+', rarityText, re.U).group(0))
        
        itemShardCosts[itemName] = (shardSellValue, shardBuyValue)
        
        for i in range(len(categories)):
            categoryDictionaries[categories[i]][itemName] = int(integers[i])
            
        items.append(itemName)
        
        rarities[itemName] = 1
        
        if args.rarity:
            rarities[itemName] *= 1/rarity
        if args.shards:
            rarities[itemName] *= shardSellValue
        if args.buy:
            rarities[itemName] *= shardBuyValue
            
    if len(price) == 0:
        return
        
    vars = LpVariable.dicts('elemenet', items, cat=LpInteger, lowBound=0)
    prob += (
        lpSum(i[1] * vars[i[0]] for i in rarities.items())
    )
    
    categoriesInUse = []
    for i in range(len(categories)):
        if price[i] != 0:
            categoriesInUse.append(categories[i])

    for i in range(len(categoriesInUse)):
        prob += (
            lpSum(categoryDictionaries[categoriesInUse[i]][j] * vars[j] for j in items) >= price[i],
            f'{categoriesInUse[i]} requirement'
        )
    
    if slipstreamItem != '':
        prob += (vars[slipstreamItem]) <= 1
        
    if args.p__problem:
        print(prob)
    
    shardBuyCostSum = 0
    shardSellCostSum = 0
    
    prob.solve()
    print("Status:", LpStatus[prob.status])
    for v in prob.variables():
        if v.varValue > 0:
            name = v.name.replace('elemenet_', '').replace('_', ' ')
            truncVal = math.trunc(v.varValue)
            print(name, "=", truncVal)
            shardBuyCostSum += itemShardCosts[name][1] * truncVal
            shardSellCostSum += itemShardCosts[name][0] * truncVal
            
    print('Total shard buy cost:', shardBuyCostSum)
    print('Total shard sell amount:', shardSellCostSum)
           
if __name__ == '__main__':
    main()
