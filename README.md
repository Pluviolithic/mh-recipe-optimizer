# mh-recipe-optimizer

## Getting Started

* Install [git](https://git-scm.com/downloads) (since this is a Roblox game, I don't expect much expertise with the GitHub workflow).
* Install Python3. You can do this via a package manager on Linux or the Windows [Store](https://apps.microsoft.com/store/detail/python-310/9PJPW5LDXLZ5) on Windows.
* Clone this repository into a local folder by opening powershell in a folder of your choice and running `git clone https://github.com/Pluviolithic/mh-recipe-optimizer.git`.
* Change directory into the cloned project (e.g. `cd mh-recipe-optimizer`)
* Run `git submodule update --init --recursive`.
* Finally, run `pip install -r requirements.txt` to add the Python dependencies for the project.

## Running the Script

`Python3 optimize.py Full Item Name` (as of right now, the program does not accept partial or lowercase names). Names with special characters like ' need to be surrounded in double quotes (e.g. `Python3 optimize.py "Draedon's Gauntlet"`). You can use arguments such as `-r` to optimize based on rarity, `-s` to optimize based on shard sell value, `-b` to optimize for shard buy cost, or `-a` to include advanced reborns. For those users who are interested in seeing more of what's going on under the hood, use the `-v` option and scroll up through the output. Multiple flags to change weight (i.e. `-s` and `-b`) can be used simultaneously, but poor(?) relative scaling in the game may cause it to yield unhelpful results. You may exclude items using`exclude.txt` (more details can be found in the file). All the slipstreams are excluded by default. You can use `-f` to include items that are normally excluded. This is helpful when you do not wish to include an entire category (e.g. Adv. Reborns with `-a`) or you have obtained a slipstream.

## Examples

```console
Python3 optimize.py Havium Mine -r
```

or

```console
Python3 optimize.py The Hourglass -f "Utopian Refiner" "Frigid Dystopia"
```

or

```console
Python3 optimize.py Midas Blaster -s -a
```

## Updating

If there is an update to the codebase that you would like to obtain, just open powershell in the `mh-recipe-optimizer` folder and run `git pull`.

## Comments

All missing features you think of will probably be added over time. Feel free to submit issues if there are bugs. Have fun crafting. :)
