import requests


def download_file(url):
    response = requests.get(url)

    if response.status_code == 200:
        filename = url.split("/")[-1]

        with open(filename, "wb") as file:
            file.write(response.content)

        print(f"File '{filename}' downloaded successfully.")
    else:
        print(f"Failed to download file. Status code: {response.status_code}")


# Example usage
urls = [
    "https://raw.githubusercontent.com/pret/pokeruby/symbols/pokeruby.sym",
    "https://raw.githubusercontent.com/pret/pokeruby/symbols/pokeruby_de.sym",
    "https://raw.githubusercontent.com/pret/pokeruby/symbols/pokeruby_de_rev1.sym",
    "https://raw.githubusercontent.com/pret/pokeruby/symbols/pokeruby_rev1.sym",
    "https://raw.githubusercontent.com/pret/pokeruby/symbols/pokeruby_rev2.sym",
    "https://raw.githubusercontent.com/pret/pokeruby/symbols/pokesapphire.sym",
    "https://raw.githubusercontent.com/pret/pokeruby/symbols/pokesapphire_de.sym",
    "https://raw.githubusercontent.com/pret/pokeruby/symbols/pokesapphire_de_rev1.sym",
    "https://raw.githubusercontent.com/pret/pokeruby/symbols/pokesapphire_rev1.sym",
    "https://raw.githubusercontent.com/pret/pokeruby/symbols/pokesapphire_rev2.sym",
    "https://raw.githubusercontent.com/pret/pokeemerald/symbols/pokeemerald.sym",
    "https://raw.githubusercontent.com/pret/pokefirered/symbols/pokefirered.sym",
    "https://raw.githubusercontent.com/pret/pokefirered/symbols/pokefirered_rev1.sym",
    "https://raw.githubusercontent.com/pret/pokefirered/symbols/pokeleafgreen.sym",
    "https://raw.githubusercontent.com/pret/pokefirered/symbols/pokeleafgreen_rev1.sym"
]

for url in urls:
    download_file(url)
