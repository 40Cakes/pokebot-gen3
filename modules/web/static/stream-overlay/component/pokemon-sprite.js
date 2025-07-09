import {eggSpritePath, speciesSpritePath} from "../helper.js";

const spriteAnimationLengths = {
    Egg: 2.820000,
    Abra: 2.930000,
    Absol: 3.190000,
    Aerodactyl: 3.130000,
    Aggron: 3.030000,
    Aipom: 3.070000,
    Alakazam: 2.950000,
    Altaria: 3.010000,
    Ampharos: 2.970000,
    Anorith: 3.210000,
    Arbok: 2.730000,
    Arcanine: 3.110000,
    Ariados: 2.730000,
    Armaldo: 2.890000,
    Aron: 3.730000,
    Articuno: 2.930000,
    Azumarill: 3.970000,
    Azurill: 3.030000,
    Bagon: 3.050000,
    Baltoy: 3.310000,
    Banette: 3.310000,
    Barboach: 4.110000,
    Bayleef: 2.830000,
    Beautifly: 2.730000,
    Beedrill: 3.050000,
    Beldum: 2.690000,
    Bellossom: 3.630000,
    Bellsprout: 2.730000,
    Blastoise: 3.050000,
    Blaziken: 2.710000,
    Blissey: 2.830000,
    Breloom: 3.030000,
    Bulbasaur: 2.970000,
    Butterfree: 3.330000,
    Cacnea: 3.970000,
    Cacturne: 2.910000,
    Camerupt: 3.190000,
    Carvanha: 3.970000,
    Cascoon: 2.730000,
    Castform: 3.330000,
    Caterpie: 3.390000,
    Celebi: 3.350000,
    Chansey: 3.290000,
    Charizard: 2.730000,
    Charmander: 2.790000,
    Charmeleon: 2.670000,
    Chikorita: 2.810000,
    Chimecho: 3.510000,
    Chinchou: 3.290000,
    Clamperl: 2.910000,
    Claydol: 3.330000,
    Clefable: 4.010000,
    Clefairy: 2.810000,
    Cleffa: 2.670000,
    Cloyster: 3.350000,
    Combusken: 2.970000,
    Corphish: 3.190000,
    Corsola: 2.830000,
    Cradily: 3.210000,
    Crawdaunt: 2.910000,
    Crobat: 2.810000,
    Croconaw: 2.730000,
    Cubone: 3.210000,
    Cyndaquil: 2.650000,
    Delcatty: 2.870000,
    Delibird: 2.670000,
    Deoxys: 3.310000,
    Dewgong: 3.270000,
    Diglett: 2.710000,
    Ditto: 2.750000,
    Dodrio: 3.270000,
    Doduo: 3.090000,
    Donphan: 3.150000,
    Dragonair: 2.730000,
    Dragonite: 3.130000,
    Dratini: 2.810000,
    Drowzee: 3.250000,
    Dugtrio: 3.470000,
    Dunsparce: 2.910000,
    Dusclops: 2.870000,
    Duskull: 2.910000,
    Dustox: 3.030000,
    Eevee: 2.750000,
    Ekans: 3.050000,
    Electabuzz: 2.930000,
    Electrike: 3.070000,
    Electrode: 3.070000,
    Elekid: 2.870000,
    Entei: 2.730000,
    Espeon: 2.710000,
    Exeggcute: 3.110000,
    Exeggutor: 3.070000,
    Exploud: 3.050000,
    "Farfetch'd": 3.210000,
    Fearow: 2.990000,
    Feebas: 3.990000,
    Feraligatr: 2.770000,
    Flaaffy: 2.650000,
    Flareon: 2.730000,
    Flygon: 3.390000,
    Forretress: 2.730000,
    Furret: 3.070000,
    Gardevoir: 2.810000,
    Gastly: 3.610000,
    Gengar: 3.490000,
    Geodude: 3.170000,
    Girafarig: 3.150000,
    Glalie: 2.910000,
    Gligar: 2.830000,
    Gloom: 3.270000,
    Golbat: 3.330000,
    Goldeen: 3.590000,
    Golduck: 3.090000,
    Golem: 3.050000,
    Gorebyss: 3.330000,
    Granbull: 2.730000,
    Graveler: 3.190000,
    Grimer: 3.110000,
    Groudon: 2.830000,
    Grovyle: 2.790000,
    Growlithe: 2.950000,
    Grumpig: 3.050000,
    Gulpin: 2.870000,
    Gyarados: 3.170000,
    Hariyama: 3.070000,
    Haunter: 3.210000,
    Heracross: 2.970000,
    Hitmonchan: 2.990000,
    Hitmonlee: 2.730000,
    Hitmontop: 2.690000,
    "Ho-oh": 2.750000,
    Hoothoot: 3.130000,
    Hoppip: 3.350000,
    Horsea: 2.830000,
    Houndoom: 2.730000,
    Houndour: 2.730000,
    Huntail: 2.910000,
    Hypno: 3.090000,
    Igglybuff: 3.330000,
    Illumise: 3.190000,
    Ivysaur: 2.730000,
    Jigglypuff: 3.190000,
    Jirachi: 3.330000,
    Jolteon: 2.830000,
    Jumpluff: 3.330000,
    Jynx: 3.530000,
    Kabuto: 3.350000,
    Kabutops: 2.730000,
    Kadabra: 2.870000,
    Kakuna: 3.110000,
    Kangaskhan: 2.730000,
    Kecleon: 3.170000,
    Kingdra: 2.970000,
    Kingler: 3.390000,
    Kirlia: 2.810000,
    Koffing: 2.810000,
    Krabby: 2.750000,
    Kyogre: 3.330000,
    Lairon: 3.110000,
    Lanturn: 3.310000,
    Lapras: 2.750000,
    Larvitar: 2.650000,
    Latias: 2.830000,
    Latios: 2.710000,
    Ledian: 3.130000,
    Ledyba: 2.670000,
    Lickitung: 3.290000,
    Lileep: 2.910000,
    Linoone: 2.870000,
    Lombre: 3.030000,
    Lotad: 3.070000,
    Loudred: 3.970000,
    Ludicolo: 3.990000,
    Lugia: 3.670000,
    Lunatone: 3.330000,
    Luvdisc: 3.310000,
    Machamp: 2.970000,
    Machoke: 2.950000,
    Machop: 3.210000,
    Magby: 3.110000,
    Magcargo: 2.710000,
    Magikarp: 3.170000,
    Magmar: 2.730000,
    Magnemite: 3.710000,
    Magneton: 3.110000,
    Makuhita: 3.310000,
    Manectric: 3.070000,
    Mankey: 3.270000,
    Mantine: 3.330000,
    Mareep: 3.330000,
    Marill: 3.610000,
    Marowak: 3.210000,
    Marshtomp: 2.730000,
    Masquerain: 2.950000,
    Mawile: 2.910000,
    Medicham: 3.270000,
    Meditite: 3.190000,
    Meganium: 2.730000,
    Meowth: 3.050000,
    Metagross: 2.950000,
    Metang: 2.730000,
    Metapod: 3.350000,
    Mew: 3.350000,
    Mewtwo: 2.730000,
    Mightyena: 2.730000,
    Milotic: 3.250000,
    Miltank: 3.310000,
    Minun: 2.730000,
    Misdreavus: 3.350000,
    Moltres: 3.310000,
    "Mr. Mime": 3.130000,
    Mudkip: 2.730000,
    Muk: 3.310000,
    Murkrow: 2.830000,
    Natu: 2.910000,
    Nidoking: 2.970000,
    Nidoqueen: 2.770000,
    Nidoran_f: 3.130000,
    Nidoran_m: 2.710000,
    Nidorina: 2.750000,
    Nidorino: 2.790000,
    Nincada: 3.130000,
    Ninetales: 3.010000,
    Ninjask: 3.090000,
    Noctowl: 2.730000,
    Nosepass: 3.970000,
    Numel: 2.970000,
    Nuzleaf: 3.190000,
    Octillery: 2.930000,
    Oddish: 2.970000,
    Omanyte: 3.350000,
    Omastar: 2.730000,
    Onix: 3.190000,
    Parasect: 3.170000,
    Paras: 3.390000,
    Pelipper: 3.310000,
    Persian: 2.930000,
    Phanpy: 3.170000,
    Pichu: 3.010000,
    Pidgeot: 2.830000,
    Pidgeotto: 2.930000,
    Pidgey: 3.130000,
    Pikachu: 2.970000,
    Piloswine: 2.730000,
    Pineco: 3.350000,
    Pinsir: 2.710000,
    Plusle: 2.810000,
    Politoed: 3.470000,
    Poliwag: 2.810000,
    Poliwhirl: 3.050000,
    Poliwrath: 3.070000,
    Ponyta: 2.970000,
    Poochyena: 2.850000,
    Porygon2: 2.910000,
    Porygon: 2.650000,
    Primeape: 3.190000,
    Psyduck: 3.010000,
    Pupitar: 2.730000,
    Quagsire: 2.750000,
    Quilava: 2.750000,
    Qwilfish: 3.850000,
    Raichu: 3.010000,
    Raikou: 2.870000,
    Ralts: 3.290000,
    Rapidash: 2.830000,
    Raticate: 2.990000,
    Rattata: 3.170000,
    Rayquaza: 3.310000,
    Regice: 2.950000,
    Regirock: 2.730000,
    Registeel: 2.730000,
    Relicanth: 2.890000,
    Remoraid: 2.670000,
    Rhydon: 3.110000,
    Rhyhorn: 2.690000,
    Roselia: 3.270000,
    Sableye: 3.550000,
    Salamence: 3.310000,
    Sandshrew: 2.810000,
    Sandslash: 2.730000,
    Sceptile: 2.710000,
    Scizor: 2.910000,
    Scyther: 2.890000,
    Seadra: 2.830000,
    Seaking: 3.310000,
    Sealeo: 2.910000,
    Seedot: 3.190000,
    Seel: 3.370000,
    Sentret: 2.830000,
    Seviper: 3.210000,
    Sharpedo: 3.870000,
    Shedinja: 3.630000,
    Shelgon: 2.910000,
    Shellder: 2.890000,
    Shiftry: 2.730000,
    Shroomish: 2.910000,
    Shuckle: 3.330000,
    Shuppet: 3.330000,
    Silcoon: 2.810000,
    Skarmory: 3.010000,
    Skiploom: 3.350000,
    Skitty: 2.810000,
    Slaking: 3.630000,
    Slakoth: 3.290000,
    Slowbro: 3.330000,
    Slowking: 2.810000,
    Slowpoke: 3.290000,
    Slugma: 2.730000,
    Smeargle: 2.770000,
    Smoochum: 3.130000,
    Sneasel: 2.730000,
    Snorlax: 3.330000,
    Snorunt: 3.330000,
    Snubbull: 2.750000,
    Solrock: 3.610000,
    Spearow: 3.310000,
    Spheal: 4.070000,
    Spinarak: 2.770000,
    Spinda: 1.260000,
    Spoink: 3.870000,
    Squirtle: 3.330000,
    Stantler: 2.830000,
    Starmie: 2.830000,
    Staryu: 3.710000,
    Steelix: 3.170000,
    Sudowoodo: 3.130000,
    Suicune: 2.730000,
    Sunflora: 2.810000,
    Sunkern: 2.670000,
    Surskit: 2.810000,
    Swablu: 2.830000,
    Swalot: 3.270000,
    Swampert: 3.190000,
    Swellow: 2.730000,
    Swinub: 2.830000,
    Taillow: 2.630000,
    Tangela: 3.210000,
    Tauros: 3.150000,
    Teddiursa: 2.750000,
    Tentacool: 2.810000,
    Tentacruel: 3.230000,
    Togepi: 3.330000,
    Togetic: 2.810000,
    Torchic: 2.730000,
    Torkoal: 2.910000,
    Totodile: 2.770000,
    Trapinch: 2.910000,
    Treecko: 2.810000,
    Tropius: 2.910000,
    Typhlosion: 2.930000,
    Tyranitar: 2.810000,
    Tyrogue: 2.750000,
    Umbreon: 2.730000,
    "Unown (A)": 2.870000,
    "Unown (B)": 2.870000,
    "Unown (C)": 2.870000,
    "Unown (D)": 2.870000,
    "Unown (E)": 2.870000,
    "Unown (em)": 2.870000,
    "Unown (F)": 2.870000,
    "Unown (G)": 2.870000,
    "Unown (H)": 2.870000,
    "Unown (I)": 2.870000,
    "Unown (J)": 2.870000,
    "Unown (K)": 2.870000,
    "Unown (L)": 2.870000,
    "Unown (M)": 2.870000,
    "Unown (N)": 2.870000,
    "Unown (O)": 2.870000,
    "Unown (P)": 2.870000,
    "Unown (Q)": 2.870000,
    "Unown (qm)": 2.870000,
    "Unown (R)": 2.870000,
    "Unown (S)": 2.870000,
    "Unown (T)": 2.870000,
    "Unown (U)": 2.870000,
    "Unown (V)": 2.870000,
    "Unown (W)": 2.870000,
    "Unown (X)": 2.870000,
    "Unown (Y)": 2.870000,
    "Unown (Z)": 2.870000,
    Ursaring: 2.730000,
    Vaporeon: 2.750000,
    Venomoth: 3.390000,
    Venonat: 3.170000,
    Venusaur: 3.050000,
    Vibrava: 3.210000,
    Victreebel: 3.050000,
    Vigoroth: 2.910000,
    Vileplume: 3.990000,
    Volbeat: 2.970000,
    Voltorb: 2.890000,
    Vulpix: 3.010000,
    Wailmer: 3.630000,
    Wailord: 3.330000,
    Walrein: 2.790000,
    Wartortle: 2.790000,
    Weedle: 3.170000,
    Weepinbell: 3.310000,
    Weezing: 2.730000,
    Whiscash: 4.110000,
    Whismur: 3.350000,
    Wigglytuff: 3.010000,
    Wingull: 3.310000,
    Wobbuffet: 3.010000,
    Wooper: 2.810000,
    Wurmple: 2.890000,
    Wynaut: 3.070000,
    Xatu: 3.410000,
    Yanma: 2.990000,
    Zangoose: 3.210000,
    Zapdos: 2.870000,
    Zigzagoon: 2.770000,
    Zubat: 2.810000,
};

export default class PokemonSprite extends HTMLElement {
    static observedAttributes = ["species", "shiny", "cropped", "continuously-animated"];

    constructor() {
        super();
        /** @type {HTMLImageElement | null} */
        this.sprite = null;
        this.shiny = false;
        this.antiShiny = false;
        this.cropped = false;
        this.continuouslyAnimated = false;
        this.species = null;
        this.animationTimeout = null;
    }

    animate() {
        if (this.continuouslyAnimated) {
            console.error(`Cannot animate sprite of '${this.species}' because it is already continuously animated.`);
            return;
        }

        if (this.cropped) {
            console.error(`Cannot animate sprite of '${this.species}' because it is cropped.`);
            return;
        }

        if (this.animationTimeout) {
            return;
        }

        const spritePath = this.species !== "Egg"
            ? speciesSpritePath(this.species, this.shiny ? "shiny" : "normal", true)
            : eggSpritePath(true);
        this.sprite.src = spritePath;
        const fileNameWithoutExtension = spritePath.substring(spritePath.lastIndexOf("/") + 1, spritePath.lastIndexOf("."))

        this.animationTimeout = window.setTimeout(
            () => {
                this.sprite.src = this.species !== "Egg"
                    ? speciesSpritePath(this.species, this.shiny ? "shiny" : "normal", false)
                    : eggSpritePath(false);
                this.animationTimeout = null;
            },
            spriteAnimationLengths[fileNameWithoutExtension] * 1000);
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === "shiny") {
            if (newValue === "anti") {
                this.shiny = false;
                this.antiShiny = true;
            } else if (newValue !== null && newValue !== "no" && newValue !== "false") {
                this.shiny = true;
                this.antiShiny = false;
            } else {
                this.shiny = false;
                this.antiShiny = false;
            }
        }

        if (name === "cropped") {
            this.cropped = newValue !== null;
        }

        if (name === "continuously-animated") {
            this.continuouslyAnimated = newValue !== null;
        }

        if (name === "species") {
            this.species = newValue ? newValue : null;
        }

        let type = "normal";
        if (this.shiny) {
            type = "shiny";
        } else if (this.antiShiny) {
            type = "anti-shiny";
        }
        if (this.cropped && !this.continuouslyAnimated && !this.antiShiny) {
            type += "-cropped";
        }

        let src = "";
        if (this.species === "Egg") {
            src = eggSpritePath(this.continuouslyAnimated);
        } else if (this.species) {
            src = speciesSpritePath(this.species, type, this.continuouslyAnimated);
        }

        if (!this.species && this.sprite) {
            this.sprite.remove();
            this.sprite = null;
            return;
        } else if (this.species && !this.sprite) {
            this.sprite = document.createElement("img");
            this.append(this.sprite);
        }

        if (this.sprite.src !== src) {
            this.sprite.src = src;
            this.sprite.alt = this.species;
        }
    }
}
