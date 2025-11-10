import argparse
import math
import re
from pathlib import Path
from typing import Any

import pulp
import requests
import toml
from bs4 import BeautifulSoup
from defusedxml import minidom

XML_FILE_PATH = Path("minershaven.xml")


# inspired by https://github.com/JOHW85/ScrapeFandom
def create_xml_file() -> None:
    pages_as_string = ""
    current_page_url: str = "https://minershaven.fandom.com/wiki/Special:AllPages"
    while current_page_url != "":
        print(f"Scanning fandom page {current_page_url}...")
        response = requests.get(current_page_url)  # noqa: S113
        soup = BeautifulSoup(response.content, "lxml")
        content = soup.find("div", {"class": "mw-allpages-body"})
        next_page = soup.find("div", {"class": "mw-allpages-nav"})
        entries = content.find_all("li")

        for entry in entries:
            pages_as_string += entry.text.replace("(redirect", "") + "\n"

        if next_page is not None:
            nav = next_page.find_all("a")
            if len(nav) > 0:
                if "Next page" in nav[-1].text:
                    current_page_url = (
                        f"https://minershaven.fandom.com{nav[-1]['href']}"
                    )
                else:
                    current_page_url = ""
                    break
        else:
            break

    # Exports XML file of all the pages scraped
    payload = {
        "catname": "",
        "pages": pages_as_string,
        "curonly": "1",
        "wpDownload": 1,
        "wpEditToken": "+\\",
        "title": "Special:Export",
    }

    response = requests.post(  # noqa: S113
        "https://minershaven.fandom.com/wiki/Special:Export", data=payload
    )

    data = response.content
    with XML_FILE_PATH.open("wb") as s:
        s.write(data)

    print()


# implementation and explanation can be found here:
# https://docs.python.org/3/library/xml.dom.minidom.html
# or here:
# https://www.geeksforgeeks.org/parsing-xml-with-dom-apis-in-python/
def get_node_text(node: Any) -> str:
    result = [
        child_node.data
        for child_node in node.childNodes
        if child_node.nodeType == node.TEXT_NODE
    ]
    return "".join(result)


def get_argument_parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Optimize the cost of a supersitious item in Miners Haven."
    )

    _ = parser.add_argument(
        "item", type=str, help="The item to optimize for.", nargs="+"
    )
    _ = parser.add_argument(
        "-a", "--advanced", action="store_true", help="Use advanced reborns."
    )
    _ = parser.add_argument(
        "-r", "--rarity", action="store_true", help="Use rarity as weight."
    )
    _ = parser.add_argument(
        "-s",
        "--shards",
        action="store_true",
        help="Use item sell value in shards as weight.",
    )
    _ = parser.add_argument(
        "-b",
        "--buy",
        action="store_true",
        help="Use item buy value in shards as weight.",
    )
    _ = parser.add_argument(
        "-v", "--verbose", action="store_true", help="Output all the problem data."
    )
    _ = parser.add_argument(
        "-f",
        "--force",
        help="Force the provided items to be considered.",
        default=[],
        nargs="+",
    )

    return parser


def main() -> None:  # noqa: C901, PLR0912, PLR0915
    parser = get_argument_parser()
    args = parser.parse_args()
    config = toml.load("config.toml")

    # these are the six "cost" and/or "value" categories for a given item
    categories = [
        "aether",
        "water",
        "earth",
        "fire",
        "order",
        "entropy",
    ]

    item_shard_costs = {}
    category_dictionaries = {}
    for category in categories:
        category_dictionaries[category] = {}

    cost = []
    items = []
    exclude = config["exclude"]
    slipstream_items = []

    rarities = {}
    item_to_optimize = " ".join(args.item)

    if not XML_FILE_PATH.exists():
        # if the file doesn't exist, scrape it
        # this is to make updating easy and to avoid scraping every run
        create_xml_file()

    dom_parser = minidom.parse(XML_FILE_PATH.as_posix())
    problem = pulp.LpProblem("Minimize_Item_Cost", pulp.LpMinimize)

    for element in dom_parser.getElementsByTagName("text"):
        element_text = get_node_text(element)
        item_name = get_node_text(
            element.parentNode.parentNode.getElementsByTagName("title")[0]
        )

        # if the element doesn't have the elements table, skip it
        # this means it either can't be "bought" or "sold"
        if "|elements = {{Elements" not in element_text:
            continue

        # if the item is force-included, skip the exclusion list/category checks
        if item_name not in args.force and (
            ("[[Category:Advanced Reborn]]" in element_text and not args.advanced)
            or "[[Category:Slipstream]]" in element_text
            or item_name in exclude
        ):
            continue

        # grab the element values from the current node's text
        element_search_result = re.compile("\\|elements[^\\}\\}]*", re.UNICODE).search(
            element_text
        )
        if element_search_result is None:
            print("A previously working regex pattern has failed. Exiting...")
            return

        relevant_text: str = element_search_result.group(0)

        # read the integer values from the extracted text
        integers: list[str] = re.findall(r"-?\d+", relevant_text, re.UNICODE)

        # it is assumed that superstitious items cannot be "sold" so the only
        # value we care about is the "cost" of the item for which a recipe is
        # being obtained
        if "[[Category:Superstitious]]" in element_text:
            if item_name == item_to_optimize:
                cost = [int(i) for i in integers]
            continue

        if "[[Category:Slipstream]]" in element_text:
            # slipstreams can only be force-included and do not have a rarity,
            # so their rarity weight is set to 0
            rarities[item_name] = 0
            for i in range(len(categories)):
                category_dictionaries[categories[i]][item_name] = int(integers[i])

            items.append(item_name)
            slipstream_items.append(item_name)
            # slipstreams cannot be bought or sold for shards, so their shard
            # weights are set to 0
            item_shard_costs[item_name] = (0, 0)
            continue

        sell_search_result = re.compile("\\|sell[^\n]*", re.UNICODE).search(
            element_text
        )
        buy_search_result = re.compile("\\|cost[^\n]*", re.UNICODE).search(element_text)
        rarity_search_result = re.compile("\\|rarity[^\n]*", re.UNICODE).search(
            element_text
        )

        if (
            sell_search_result is None
            or buy_search_result is None
            or rarity_search_result is None
        ):
            print("A previously working regex pattern has failed. Exiting...")
            return

        sell_value_search_result = re.search(
            r"\d+", sell_search_result.group(0), re.UNICODE
        )
        buy_value_search_result = re.search(
            r"\d+", buy_search_result.group(0), re.UNICODE
        )
        rarity_value_search_result = re.search(
            r"\d+", rarity_search_result.group(0), re.UNICODE
        )

        if rarity_value_search_result is None:
            print("A previously working regex pattern has failed. Exiting...")
            return

        shard_sell_value = (
            int(sell_value_search_result.group(0))
            if sell_value_search_result is not None
            else 0
        )
        shard_buy_value = (
            int(buy_value_search_result.group(0))
            if buy_value_search_result is not None
            else 0
        )
        rarity = int(rarity_value_search_result.group(0))

        item_shard_costs[item_name] = (shard_sell_value, shard_buy_value)

        for i in range(len(categories)):
            category_dictionaries[categories[i]][item_name] = int(integers[i])

        items.append(item_name)

        # set a default value that can be modified by the command line arguments
        # and item weights
        rarities[item_name] = 1

        if args.rarity:
            rarities[item_name] *= 1 / rarity
        if args.shards:
            rarities[item_name] *= shard_sell_value
        if args.buy:
            rarities[item_name] *= shard_buy_value

    if len(cost) == 0:
        print("Cost for item was unobtainable. Exiting...")
        return

    # set up item weights in the problem
    variables = pulp.LpVariable.dicts("element", items, cat=pulp.LpInteger, lowBound=0)
    problem += pulp.lpSum(idx[1] * variables[idx[0]] for idx in rarities.items())

    updated_cost = []
    categories_in_use = []
    for i in range(len(categories)):
        if cost[i] != 0:
            updated_cost.append(cost[i])
            categories_in_use.append(categories[i])

    # for any cost categories that != 0 in cost, add a cost constraint to the problem
    for i in range(len(categories_in_use)):
        problem += (
            pulp.lpSum(
                category_dictionaries[categories_in_use[i]][j] * variables[j]
                for j in items
            )
            >= updated_cost[i],
            f"{categories_in_use[i]} requirement",
        )

    # it is not possible to have more than one of a given slipstream item
    for slipstream_time in slipstream_items:
        problem += (variables[slipstream_time]) <= 1

    if args.verbose:
        print(problem)
        problem.solve()
        print("Status:", pulp.LpStatus[problem.status], "\n")
    else:
        problem.solve(pulp.PULP_CBC_CMD(msg=False))

    shard_buy_cost = 0
    shard_sell_cost = 0

    for v in problem.variables():
        if v.varValue > 0:
            name = v.name.replace("element_", "").replace("_", " ")
            truncated_value = math.trunc(v.varValue)
            print(name, "=", truncated_value)
            shard_buy_cost += item_shard_costs[name][1] * truncated_value
            shard_sell_cost += item_shard_costs[name][0] * truncated_value

    print()
    print("Total shard buy cost:", shard_buy_cost)
    print("Total shard sell amount:", shard_sell_cost)


if __name__ == "__main__":
    main()
