from xml.dom import minidom

import argparse
import math
import pulp
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
parser.add_argument('-v' '--verbose', action='store_true', help='Output all the problem data.')
parser.add_argument('-f', '--force', help='Force the provided items to be considered.', default=[], nargs='+')

args = parser.parse_args()

# these are the six "price" and/or "value" categories for a given item
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

# implementation and explanation can be found here:
# https://docs.python.org/3/library/xml.dom.minidom.html
# or here:
# https://www.geeksforgeeks.org/parsing-xml-with-dom-apis-in-python/
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
    slipstreamItems = []
    
    rarities = {}
    itemToOptimize = ' '.join(args.item)
    
    # grab all uncommented lines and append their contents to the exclude list
    exclusionsFile = open('exclude.txt', 'r')
    for line in exclusionsFile:
        if line.startswith('//') or len(line.strip()) == 0:
            continue
        exclude.append(line.replace('\n', ''))
    
    if not os.path.exists('minershaven.xml'):
        # if the file doesn't exist, scrape it via the ScrapeFandom submodule
        # this is to make updating easy and to avoid scraping every run
        os.system('python3 ' + os.path.join('ScrapeFandom', 'ScrapeFandom.py') + ' minershaven')
    
    parser = minidom.parse('minershaven.xml')
    prob = pulp.LpProblem('Minimize_Item_Cost', pulp.LpMinimize)

    for element in parser.getElementsByTagName('text'):
        elementText = getNodeText(element)
        itemName = getNodeText(element.parentNode.parentNode.getElementsByTagName('title')[0])

        # if the element doesn't have the elements table, skip it
        # this means it either can't be "bought" or "sold"
        if not '|elements = {{Elements' in elementText:
            continue

        # if the item is force-included, skip the exclusion list/category checks
        if itemName not in args.force:
            if '[[Category:Advanced Reborn]]' in elementText and not args.advanced:
                continue
            elif '[[Category:Slipstream]]' in elementText:
                continue
            elif itemName in exclude:
                continue
        
        # grab the element values from the current node's text
        relevantText = re.compile('\|elements[^\}\}]*', re.U).search(elementText).group(0)
        # read the integer values from the extracted text
        integers = re.findall(r'-?\d+', relevantText, re.U)
        
        # it is assumed that superstitious items cannot be "sold"
        # so the only value we care about is the "cost" of the item for which a recipe is being obtained
        if '[[Category:Superstitious]]' in elementText:
            if itemName == itemToOptimize:
                price = [int(i) for i in integers]
            continue
        
        if '[[Category:Slipstream]]' in elementText:
            # slipstreams can only be force-included and do not have a rarity, so their rarity weight is set to 0
            rarities[itemName] = 0
            for i in range(len(categories)):
                categoryDictionaries[categories[i]][itemName] = int(integers[i])
            
            items.append(itemName)
            slipstreamItems.append(itemName)
            # slipstreams cannot be bought or sold for shards, so their shard weights are set to 0
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
        
        # set a default value that can be modified by the command line arguments and item weights
        rarities[itemName] = 1
        
        if args.rarity:
            rarities[itemName] *= 1/rarity
        if args.shards:
            rarities[itemName] *= shardSellValue
        if args.buy:
            rarities[itemName] *= shardBuyValue
            
    if len(price) == 0:
        return    

    # set up item weights in the problem
    vars = pulp.LpVariable.dicts('element', items, cat=pulp.LpInteger, lowBound=0)
    prob += (
        pulp.lpSum(i[1] * vars[i[0]] for i in rarities.items())
    )
    
    updatedPrice = []
    categoriesInUse = []
    for i in range(len(categories)):
        if price[i] != 0:
            updatedPrice.append(price[i])
            categoriesInUse.append(categories[i])

    # for any price categories that != 0 in cost, add a price constraint to the problem
    for i in range(len(categoriesInUse)):
        prob += (
            pulp.lpSum(categoryDictionaries[categoriesInUse[i]][j] * vars[j] for j in items) >= updatedPrice[i],
            f'{categoriesInUse[i]} requirement'
        )
    
    # it is not possible to have more than one of a given slipstream item
    for slipstreamItem in slipstreamItems:
        prob += (vars[slipstreamItem]) <= 1
    
    if args.v__verbose:
        print(prob)
        prob.solve()
        print("Status:", pulp.LpStatus[prob.status], "\n")
    else:
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
    
    shardBuyCostSum = 0
    shardSellCostSum = 0
    for v in prob.variables():
        if v.varValue > 0:
            name = v.name.replace('element_', '').replace('_', ' ')
            truncVal = math.trunc(v.varValue)
            print(name, "=", truncVal)
            shardBuyCostSum += itemShardCosts[name][1] * truncVal
            shardSellCostSum += itemShardCosts[name][0] * truncVal
            
    print('Total shard buy cost:', shardBuyCostSum)
    print('Total shard sell amount:', shardSellCostSum)
           
if __name__ == '__main__':
    main()
