from rich.console import Console
from rich.theme import Theme

theme = Theme({
    'normal': '#a8a878',
    'fire': '#f08030',
    'water': '#6890f0',
    'electric': '#f8d030',
    'grass': '#78c850',
    'ice': '#98d8d8',
    'fighting': '#c03028',
    'poison': '#a040a0',
    'ground': '#e0c068',
    'flying': '#a890f0',
    'psychic': '#f85888',
    'bug': '#a8b820',
    'rock': '#b8a038',
    'ghost': '#705898',
    'dragon': '#7038f8',
    'dark': '#705848',
    'steel': '#b8b8d0'
})

console = Console(theme=theme)
