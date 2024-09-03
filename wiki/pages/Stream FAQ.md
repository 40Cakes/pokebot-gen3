🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

This page contains answers to questions frequently asked in the live chat of the stream, please check that your question hasn't already been answered here before asking anything. Any questions about running the bot for yourself should be asked in Discord [#pokebot-gen3-support❔](https://discord.com/channels/1057088810950860850/1139190426834833528).

**If you're on desktop, use CTRL+F to search for keywords related to your question!** For example, if you're wondering about something related to breeding, you could search `breed` or `egg`. Many mobile browsers also have search features in their menus.

# I have no idea what's happening!

A basic explanation of what this bot is doing is covered in [the explanation video](https://www.youtube.com/watch?v=6kA1_-FhnAQ), but if you stumbled on the livestream and have no idea what’s going on then here’s the short version.

This bot is attempting a **Professor Oak's Living Shiny Dex Challenge** in Pokémon Emerald. This means obtaining one of every single shiny Pokémon as soon as it's available. A breakdown of all the challenges being mixed together here is:
- The **Professor Oak's Challenge** requires you to obtain one of every single Pokémon available to you before you can fight the next Gym leader(/the League) and continue with the game. This means catching one of each Pokémon available and evolving it as far as it can go - Pokémon that require items to evolve that we can’t get yet will be evolved as soon as the item becomes available.
- A **Living Dex** means having one of every single Pokémon in your boxes - if a Pokémon can evolve, you will need one of each. For example, you will need 3 Ralts: one to stay as a Ralts, one to evolve into a Kirlia, and a third and final one to evolve into a Gardevoir. _(Gallade doesn’t exist in Gen III, before anyone asks)_ 
- As this is a **Shiny Dex**, every single one of these Pokémon also has to be **shiny**. A **shiny Pokémon** is a rare version of a Pokémon with different colours than normal and a special sparkling animation when sent into battle. 
  - **In Emerald, there is a 1 in 8,192 chance for a Pokémon to be shiny.** These odds cannot be boosted in any way in Gen 3.

# Helpful chat commands

- `!commands` - Will link you to a full list of commands.
- `!faq` - Will link you to this page! Feel free to use this if anyone asks a question answered here
- `!target` - Responds with the current shiny target(s) and encounter rates
- `!guide` - Links to the [Emerald Version Professor Oak's Challenge Guide by Mewlax](https://docs.google.com/document/d/1cn5awGNEVZx3wuv-2EsIn3e746RfH5-Spm7mnP-_PxU)
- `!map` - Links to a [Map of Pokemon Emerald](https://simplyblgdev.github.io/pokemon/hoenn)
- `!shiny_value` or `!sv` - Explains what SV means and links the [Bulbapedia page](https://bulbapedia.bulbagarden.net/wiki/Personality_value#Shininess)
- `!download` - Links to the Github repo
- `!discord` - Links to [the Discord](https://discord.gg/CXQDjGSeyV)
- `!download` - You can download and run your own PokéBot from [here](https://github.com/40Cakes/pokebot-gen3)
- `!longest` and `!shortest` - Displays the current longest and shortest phase

# Glossary
You will regularly see these terms used on the stream overlay, or in chat:

## Phase
  - A term used by shiny hunters to refer to the amount of Pokémon encountered since the last shiny Pokémon.
  - For example, if you were trying to find a shiny Lotad, and after 8,931 encounters you found a shiny Wurmple, you have now ‘**phased**’ and the counter is reset to zero.

## SV
  - Calculated from a Pokémon's Personality ID (PID), a Pokémon's **SV** (or **Shiny Value**) is a number between `0` and `65,535`. If this number is **less than `8`**, the Pokémon will be shiny!
  - In Generation 4 and later, this is doubled and any number less than `16` will be shiny
  - See the [Bulbapedia page](https://bulbapedia.bulbagarden.net/wiki/Personality_value#Shininess) for more

## TID and SID
  - Your **TID** and **SID** (short for **Trainer ID** and **Secret ID**) are numbers assigned to you at the start of the game. These are two of the three numbers that the game uses in its calculations to decide if a wild Pokémon is shiny or not
  - See the [Bulbapedia Page](https://bulbapedia.bulbagarden.net/wiki/Trainer_ID_number) for more

## PID
  - Short for **Personality ID**, this is a number the game creates and assigns when generating a Pokémon. This determines different properties of the Pokémon, such as gender, nature and ability. Most importantly, this is one of the three numbers used to decide if a Pokémon is shiny or not
  - See the [Bulbapedia Page](https://bulbapedia.bulbagarden.net/wiki/Personality_value) for more

## PSP
  - Short for Phase Shiny Probability - if the current PSP was 60% and 1,000 people were shiny hunting at the same time, 600 of them would have likely found a shiny in the current # phase encounters
  - Phase Shiny Probability % B(n,p) refers to the [binomial distribution](https://en.wikipedia.org/wiki/Binomial_distribution) that models the probability (p) of encountering a shiny after (n) phase encounters, where each encounter has an independent chance of success
  - Use [this calculator](https://oldschool.runescape.wiki/w/Calculator:Dry_calc) with chance of `1/8192` to run your own PSP calcs

# Stream FAQs
Answers to questions frequently asked in the live chat of the stream, please check that your question hasn't already been answered here before asking anything.

## What is the bot doing?
### What is the bot currently looking for?
The chat command `!target` will respond with the Pokémon currently being searched for and its encounter rate

### What does the bot need to get?
A list of Pokémon the bot needs to catch before the next badge is in the description. The top right panel of the stream overlay also displays every Pokémon in this part of the challenge, how many it has caught and how many more it needs. The top of the bottom right panel has a progress bar for progress to the next badge, and how many badges the bot has accquired.
[A full guide](https://docs.google.com/document/d/1cn5awGNEVZx3wuv-2EsIn3e746RfH5-Spm7mnP-_PxU/edit) to the **Emerald Professor Oak’s Challenge** can also be found in the description. This lays out each section, which Pokémon will need to be caught and evolved in it, and any Pokémon that we can’t evolve yet, but will need to later.

### How long has the bot been playing?
A timer can be found at the top left of the overlay. 
The bot started on the **1st January 2023 AEST**.

## What does the bot do?

### Why do we lead with Lotad?
Lotad has a very short cry (12.2 frames), this saves fractions of seconds per encounter but adds up to days of saved time over the entire challenge.
See [here](https://docs.google.com/spreadsheets/d/1rmtNdlIXiif1Sz20i-9mfhFdoqb1VnAOIntlr3tnPeU) for a full list of cry lengths for gen 3.

### What happens when the bot encounters a shiny?
The bot will simply throw the best ball available, once the Pokémon has been caught, the bot will save the game.

### Does the bot catch extra shiny Pokémon it encounters?
**Yes**, the bot catches every shiny, not just the ones it needs.

### What if the bot runs out of box space? / What will you do with the extra shinies?
Extra Pokémon in boxes may be transferred to another save file via save editing once the boxes start to get full. 
What happens to them after that is undecided, however they may be transferred to newer games and wonder traded away.

### What if the bot runs out of Pokéballs?
The bot has thousands of Pokéballs, that won't be a problem, items were farmed with the Pickup ability. 
The Pickup ability item table for Emerald [can be found here.](https://bulbapedia.bulbagarden.net/wiki/Pickup_(Ability)#Pok.C3.A9mon_Emerald)

### How does the bot reset for shiny starters?
The bot waits for a new, untested frame when resetting for shiny starters.

### How does the bot hunt for static encounters, like Rayquaza?
The bot uses the run away method that shiny hunters use.

### How does the bot hunt for Feebas? Will it pull the tiles from memory?
The bot will search for Feebas tiles, as if it were a person using no external tools to check tiles.

### When does the bot save?
The bot saves after it catches a shiny - Saving more often isn't necessary since in the event of a crash nothing would be lost.

## "Will the bot...?"

### Will the bot use trades? / Will the bot do trade evolutions?
**No**. The bot will be using a single Emerald version only.
This means all trade evolutions, other starters and version exclusives not present in Emerald are _not_ a part of the challenge.

### Will the bot use RNG Manipulation?
**No**. 

 ### Will the bot use the repel trick?
**Yes**, where possible.
Repel tricking works with both `spin` and `bunny hop` bot modes, so we can either bunny hop on the Acro bike, or spin on the spot. Neither of these uses up steps. We won't encounter any Pokémon of a lower level than our lead - for example Poochyena on Route 116 at level 7 will increase the odds to encounter Abra.

### Will the bot use breeding to hunt Pokémon with low encounter rates?
**Probably not**. The plan is to use breeding as little as possible. 

### Can you tell if an egg is shiny before it hatches? / Will the bot only hatch shiny eggs?
**Yes** and **No**: 
**Yes**, the Pokémon is generated upon recieving the egg, so programs such as the bot can be used to check if they are shiny before they hatch.
**No**, the bot will not check if the eggs are shiny and hatch only those. All eggs will be hatched and the SV will be hidden from viewers.

### Will the bot breed Mudkip pre-evolutions?
**Yes**. However, 40 Cakes forgot we needed a female shiny Mudkip to breed Mudkip without Ditto, and this was realised so far in that it was decided we wouldn't reset. Because of this, **Mudkip and Marshtomp will be accuired post-game**, when Ditto is available.

### Will the bot use emulator speedup/throttling?
**No**. ​Some people in the Discord run the bot unthrottled, but we obey the laws of time and physics in this stream.

### Will the bot battle trainers and gyms by itself?
**No**, these will be done manually. The bot is designed to automate repetitive, grindy tasks, such as shiny hunting.

### Will the bot hunt event Pokémon like Latias/Latios/Mew/Etc?
**Yes**. The tickets and event flags will be edited into the save, and will be done at the end of the challenge.

### Will the bot catch Pokémon with perfect/no IVs? / Has the bot seen a Pokémon with perfect/no IVs?
**Yes**, the bot will catch any Pokémon with 6 identical IVs. No we haven't seen any so far.

## What's up with that?

### Why did you move grass patches? Did the hunt change?
So long as the route is the same, the hunt has not changed. Sometimes the bot gets moved to another part of the route during long grinds for a change of scenery.

### What's with those Pokémon in the background? Can they be shiny?
Background Pokémon have a 1/128 chance of being shiny, keep an eye out for one (they sparkle)! Type `!bingo` for a bingo card to play along at home.

### What does it mean when an SV is highlighted purple?
This is just a fun little overlay Easter egg to show which Pokémon are "anti-shiny", the complete opposite of a shiny. Anything with an SV of `65,528` - `65,535` is anti-shiny.
This is not a real thing in the game - it's just a term used on the stream.

## Pokémon FAQs

### What is the chance of a shiny Pokémon in Emerald?
**1 in 8,192**
Rates can NOT be increased or decreased in any way (no shiny charm, no Masuda method).

### What is the chance of a Pokémon having Pokérus?
**1 in 21,845**

### What is the chance of a Pokémon having 6 perfect IVs?
**1 in 1,073,741,824**

### What about a shiny with 6 perfect IVs?
**1 in 8,796,093,000,000**

### What about a shiny Seedot with 6 perfect IVs?
Wild Seedot actually can't be generated with perfect IVs on this save due to how the game generates Pokémon, but if they could it'd be **1 in 879,609,300,000,000.**

## Seedot FAQs
Because it's gotten to this point.

### What are the odds for shiny Seedot?
Seedot is a **1% encounter**. This makes the odds of a shiny Seedot **1 in 819,200**.

### Can't you go somewhere else where it's more common?
Even if we weren't forced to hunt on this route because of the rules of the challenge, no. Seedot is a **1% encounter** in every single route in the game where it shows up. 
The same goes for Nuzleaf.

### 🤓 What about the in-game trade Seedot?
DOTS is the same Pokémon every time and cannot be shiny.

**Longer version for nerds:** DOTS is a Pokémon already generated by the game before he's given to you. Information about him, including his PID, OT (Original Trainer) and the TID and SID of said trainer are already set by the game beforehand. Since the OT isn't you and the data is set, the trade will always give you the exact same Pokémon, who is not shiny.

**Data for turbo-nerds:** DOTS is a male level 4 Seedot with the PID 00000084 and a Relaxed nature. His OT is named KOBE and has a TID of 38726 and an SID of 00000 (or incomplete trainer data, which is common for NPCs in R/S/E.)

### You're still on Seedot!?
We have already caught two shiny Seedot, so at least for now we don't need any more.  
We will eventually need another one in order to evolve it to Shiftry, but at this stage in the game we don't have access to a Leaf Stone. So that can wait until at least after the 4th badge.

### How long did Seedot take?
Shiny Seedot #1 was hunted basically non-stop between **19th Feb 2023 AEST** (**20th Feb 2023 UTC**) and **8th June 2023** (**7th June 2023 UTC**) when it was finally found. This makes it **109 days** or **3 months 20 days** to find the first Seedot.  
Regular Seedot was encountered before this, but 19th Feb was when we committed to the grind.  
Shiny Seedot #2 hunt started on **27th Aug 2023** and finally completed on **28th August 2024**. So it took **367 days** or **1** (leap) **year and 1 day** to find.

### Will everything take this long?
Probably not, Seedot is expected to be the single worst part of the whole challenge. 
Seedot has a **1% encounter rate**, and is the only Pokémon with an encounter rate this low we will need to get before we have access to breeding and can guarantee all 'encounters' will be Seedot. As we don't have bikes, running is the fastest we can move, and the repel trick will not work on Seedot.

### 🤓 What about other 1% encounters?
The other 1% encounters in this game are: Seedot, Nuzleaf, Volbeat, Keckleon, Electrode, Magneton, Octillery, Quagsire, Tentacruel and Wailord
  - Keckleon also has static encounters, which could be reset hunted for a 100% encounter rate.
  - Electrode, Magneton, Octillery, Quagsire, Tentacruel and Wailord have pre-evolutions with higher encounter rates.
We will have access to breeding and bikes for all 1% encounters other than Seedot. Some of these may also work with the repel trick.

### 🤓 What about Feebas?
Feebas is a **50% encounter** once you find the tile. 
Tiles change when the Trendy Phrase is changed¹, so once the bot finds a tile it'll have time to stick with it.
  - _¹ There is conflicting information online surrounding Feebas tiles changing without manually changing the Trendy Phrase. No matter when this is, it'll be fine._

### How long until 40 Cakes makes another video?
![](https://cdn.betterttv.net/emote/5d61b1b14932b21d9c332f1b/3x.webp)
