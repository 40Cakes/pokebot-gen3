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
    "https://raw.githubusercontent.com/fattard/MissingEventFlagsCheckerPlugin/main/checklist/chkdb_gen3rs.txt",
    "https://raw.githubusercontent.com/fattard/MissingEventFlagsCheckerPlugin/main/checklist/chkdb_gen3e.txt",
    "https://raw.githubusercontent.com/fattard/MissingEventFlagsCheckerPlugin/main/checklist/chkdb_gen3frlg.txt"
]

for url in urls:
    download_file(url)
