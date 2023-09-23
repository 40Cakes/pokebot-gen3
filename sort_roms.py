import os
import hashlib
import shutil
from pathlib import Path

print('\nPlace all of your .gba Pokémon ROMS into the same folder as this script.')
print('ROMs will be verified and sorted into directories in the following format: `./roms/<GAME_CODE>/<LANGUAGE>/<REVISION>/`.')
print('For example, `Pokemon - Sapphire Version (USA, Europe) (Rev 2).gba` will be moved to `./roms/AXP/E/2/`.')
input('\nPress enter when ready...')

hashes = {
    "5a087835009d552d4c5c1f96be3be3206e378153": "./roms/AXP/D/0/",
    "7e6e034f9cdca6d2c4a270fdb50a94def5883d17": "./roms/AXP/D/1/",
    "3ccbbd45f8553c36463f13b938e833f652b793e4": "./roms/AXP/E/0/",
    "4722efb8cd45772ca32555b98fd3b9719f8e60a9": "./roms/AXP/E/1/",
    "89b45fb172e6b55d51fc0e61989775187f6fe63c": "./roms/AXP/E/2/",
    "c269b5692b2d0e5800ba1ddf117fda95ac648634": "./roms/AXP/F/0/",
    "860e93f5ea44f4278132f6c1ee5650d07b852fd8": "./roms/AXP/F/1/",
    "f729dd571fb2c09e72c5c1d68fe0a21e72713d34": "./roms/AXP/I/0/",
    "73edf67b9b82ff12795622dca412733755d2c0fe": "./roms/AXP/I/1/",
    "3233342c2f3087e6ffe6c1791cd5867db07df842": "./roms/AXP/J/0/",
    "01f509671445965236ac4c6b5a354fe2f1e69f13": "./roms/AXP/J/1/",
    "3a6489189e581c4b29914071b79207883b8c16d8": "./roms/AXP/S/0/",
    "0fe9ad1e602e2fafa090aee25e43d6980625173c": "./roms/AXP/S/1/",
    "1c2a53332382e14dab8815e3a6dd81ad89534050": "./roms/AXV/D/0/",
    "424740be1fc67a5ddb954794443646e6aeee2c1b": "./roms/AXV/D/1/",
    "f28b6ffc97847e94a6c21a63cacf633ee5c8df1e": "./roms/AXV/E/0/",
    "610b96a9c9a7d03d2bafb655e7560ccff1a6d894": "./roms/AXV/E/1/",
    "5b64eacf892920518db4ec664e62a086dd5f5bc8": "./roms/AXV/E/2/",
    "a6ee94202bec0641c55d242757e84dc89336d4cb": "./roms/AXV/F/0/",
    "ba888dfba231a231cbd60fe228e894b54fb1ed79": "./roms/AXV/F/1/",
    "2b3134224392f58da00f802faa1bf4b5cf6270be": "./roms/AXV/I/0/",
    "015a5d380afe316a2a6fcc561798ebff9dfb3009": "./roms/AXV/I/1/",
    "5c5e546720300b99ae45d2aa35c646c8b8ff5c56": "./roms/AXV/J/0/",
    "971e0d670a95e5b32240b2deed20405b8daddf47": "./roms/AXV/J/1/",
    "1f49f7289253dcbfecbc4c5ba3e67aa0652ec83c": "./roms/AXV/S/0/",
    "9ac73481d7f5d150a018309bba91d185ce99fb7c": "./roms/AXV/S/1/",
    "61c2eb2b380b1a75f0c94b767a2d4c26cd7ce4e3": "./roms/BPE/D/0/",
    "f3ae088181bf583e55daf962a92bb46f4f1d07b7": "./roms/BPE/E/0/",
    "ca666651374d89ca439007bed54d839eb7bd14d0": "./roms/BPE/F/0/",
    "1692db322400c3141c5de2db38469913ceb1f4d4": "./roms/BPE/I/0/",
    "d7cf8f156ba9c455d164e1ea780a6bf1945465c2": "./roms/BPE/J/0/",
    "fe1558a3dcb0360ab558969e09b690888b846dd9": "./roms/BPE/S/0/",
    "0802d1fb185ee3ed48d9a22afb25e66424076dac": "./roms/BPG/D/0/",
    "574fa542ffebb14be69902d1d36f1ec0a4afd71e": "./roms/BPG/E/0/",
    "7862c67bdecbe21d1d69ce082ce34327e1c6ed5e": "./roms/BPG/E/1/",
    "4b5758c14d0a07b70ef3ef0bd7fa5e7ce6978672": "./roms/BPG/F/0/",
    "a1dfea1493d26d1f024be8ba1de3d193fcfc651e": "./roms/BPG/I/0/",
    "5946f1b59e8d71cc61249661464d864185c92a5f": "./roms/BPG/J/0/",
    "de9d5a844f9bfb63a4448cccd4a2d186ecf455c3": "./roms/BPG/J/1/",
    "f9ebee5d228cb695f18ef2ced41630a09fa9eb05": "./roms/BPG/S/0/",
    "18a3758ceeef2c77b315144be2c3910d6f1f69fe": "./roms/BPR/D/0/",
    "41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc": "./roms/BPR/E/0/",
    "dd5945db9b930750cb39d00c84da8571feebf417": "./roms/BPR/E/1/",
    "fc663907256f06a3a09e2d6b967bc9af4919f111": "./roms/BPR/F/0/",
    "66a9d415205321376b4318534c0dce5f69d28362": "./roms/BPR/I/0/",
    "04139887b6cd8f53269aca098295b006ddba6cfe": "./roms/BPR/J/0/",
    "7c7107b87c3ccf6e3dbceb9cf80ceeffb25a1857": "./roms/BPR/J/1/",
    "ab8f6bfe0ccdaf41188cd015c8c74c314d02296a": "./roms/BPR/S/0/"
}

files = Path('.').glob('*.gba')
for file in files:
    sha1 = hashlib.sha1()
    print('\nChecking file `{}`...'.format(file))
    with open(file, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha1.update(data)
    hash = sha1.hexdigest()
    if hash in hashes:
        dir = hashes[hash]
        if not os.path.exists(dir):
            print('Creating directory: {}'.format(dir))
            os.makedirs(dir)
        print('Moving `{}` to `{}`...'.format(
            file,
            dir
        ))
        dest = dir + str(file)
        shutil.move(file, dest)
    else:
        print('Unrecognised ROM! Ignoring `{}`...'.format(
            file
        ))
