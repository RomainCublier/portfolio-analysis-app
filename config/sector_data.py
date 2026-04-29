"""
Curated sector database — leaders + backbone companies per GICS sector.

Structure per sector
--------------------
{
    "label":       display name
    "etf":         main sector ETF ticker (SPDR series)
    "description": 2-sentence investment narrative
    "drivers":     list of key thematic drivers
    "leaders": [
        {"ticker": ..., "name": ..., "role": ..., "why": ...}
    ]
    "backbone": [
        {"ticker": ..., "name": ..., "role": ..., "why": ...}
    ]
}

"backbone" = essential but less visible companies that the sector cannot function
without (infrastructure, suppliers, exchanges, tooling layers).
"""

SECTORS: dict[str, dict] = {
    "Technology": {
        "label": "Technologie",
        "etf": "XLK",
        "description": (
            "Le secteur technologique englobe les semi-conducteurs, les logiciels d'entreprise "
            "et les services cloud. Il est le principal moteur de croissance des marchés développés "
            "depuis 2010, mais reste sensible aux cycles de taux et aux multiples de valorisation élevés."
        ),
        "drivers": [
            "Intelligence artificielle & LLMs",
            "Cloud computing & edge infrastructure",
            "Semi-conducteurs nouvelle génération",
            "Cybersécurité & zero-trust",
        ],
        "leaders": [
            {
                "ticker": "AAPL",
                "name": "Apple",
                "role": "Plateforme consumer & écosystème hardware/software",
                "why": "Effet réseau incomparable, marges services en croissance, base installée de 2Md+ appareils.",
            },
            {
                "ticker": "MSFT",
                "name": "Microsoft",
                "role": "Cloud d'entreprise & IA (Azure, Copilot, OpenAI)",
                "why": "Leader cloud n°2, croissance Azure >25% YoY, intégration IA la plus avancée en entreprise.",
            },
            {
                "ticker": "NVDA",
                "name": "NVIDIA",
                "role": "GPU pour IA & HPC",
                "why": "Monopole de facto sur les accélérateurs IA (H100/B200), marges brutes >75%.",
            },
            {
                "ticker": "GOOGL",
                "name": "Alphabet",
                "role": "Moteur de recherche, cloud (GCP), IA Gemini",
                "why": "Cash machine publicitaire finançant R&D IA de pointe; TPUs propriétaires.",
            },
        ],
        "backbone": [
            {
                "ticker": "AVGO",
                "name": "Broadcom",
                "role": "Semi-conducteurs réseau & ASICs IA sur mesure",
                "why": "Fournit les puces réseau à >80% des hyperscalers; custom AI chips pour Google & Meta.",
            },
            {
                "ticker": "AMAT",
                "name": "Applied Materials",
                "role": "Équipements de fabrication de puces",
                "why": "Aucune fab ne peut produire sans ses outils de dépôt/gravure; oligopole avec ASML & Lam.",
            },
            {
                "ticker": "CDNS",
                "name": "Cadence Design Systems",
                "role": "EDA software — conception de circuits intégrés",
                "why": "Tout chip moderne (NVIDIA, Apple, AMD) est conçu avec Cadence ou Synopsys.",
            },
            {
                "ticker": "KEYS",
                "name": "Keysight Technologies",
                "role": "Instruments de test électronique & R&D",
                "why": "Test 5G, Wi-Fi 7, composants semi : chaque nouveau standard passe par Keysight.",
            },
        ],
    },

    "Healthcare": {
        "label": "Santé",
        "etf": "XLV",
        "description": (
            "Le secteur santé combine des caractéristiques défensives (demande inélastique) "
            "et des catalyseurs de croissance structurels (vieillissement, GLP-1, oncologie). "
            "Les pipelines de R&D et l'approbation FDA sont les principaux moteurs de valorisation."
        ),
        "drivers": [
            "Médicaments GLP-1 (obésité & diabète)",
            "Oncologie & thérapies cellulaires CAR-T",
            "Vieillissement démographique",
            "IA appliquée au diagnostic & discovery",
        ],
        "leaders": [
            {
                "ticker": "LLY",
                "name": "Eli Lilly",
                "role": "Leader mondial GLP-1 (Mounjaro, Zepbound)",
                "why": "Meilleure pipeline blockbuster du secteur; croissance revenue +50% en 2024.",
            },
            {
                "ticker": "JNJ",
                "name": "Johnson & Johnson",
                "role": "Pharma & MedTech diversifié",
                "why": "Bilan triple-A, dividende aristocrate 60+ ans, oncologie en forte expansion.",
            },
            {
                "ticker": "UNH",
                "name": "UnitedHealth Group",
                "role": "Assurance santé & gestion des soins (Optum)",
                "why": "Accès aux données de 50M+ patients; Optum est la plus grande organisation de soins US.",
            },
            {
                "ticker": "ABBV",
                "name": "AbbVie",
                "role": "Immunologie & oncologie (Humira, Skyrizi, Rinvoq)",
                "why": "Transition post-Humira réussie; pipeline immunologie parmi les plus solides.",
            },
        ],
        "backbone": [
            {
                "ticker": "MCK",
                "name": "McKesson",
                "role": "Distribution pharmaceutique (30% du marché US)",
                "why": "Un médicament sur trois distribué aux US passe par McKesson. Infrastructure invisible mais critique.",
            },
            {
                "ticker": "TMO",
                "name": "Thermo Fisher Scientific",
                "role": "Équipements & réactifs de laboratoire",
                "why": "Fournit les outils à 99% des labos pharma et biotech mondiaux; duopole avec Danaher.",
            },
            {
                "ticker": "VEEV",
                "name": "Veeva Systems",
                "role": "CRM & cloud vertical pour l'industrie Life Sciences",
                "why": ">80% des grandes pharmas utilisent Veeva pour gérer leurs essais cliniques et compliance.",
            },
            {
                "ticker": "IQV",
                "name": "IQVIA",
                "role": "Data, analytics & CRO pour essais cliniques",
                "why": "Détient la plus grande base de données de santé mondiale; pilote les essais pour Big Pharma.",
            },
        ],
    },

    "Financials": {
        "label": "Finance",
        "etf": "XLF",
        "description": (
            "Le secteur financier bénéficie d'un environnement de taux élevés (NIM élargis) "
            "mais reste exposé au risque de crédit cyclique. Les plateformes de paiement "
            "et les bourses représentent la partie la plus défensive et en croissance structurelle."
        ),
        "drivers": [
            "Niveau des taux directeurs (NIM bancaire)",
            "Croissance des paiements digitaux",
            "Consolidation bancaire post-SVB",
            "Démocratisation de la gestion d'actifs",
        ],
        "leaders": [
            {
                "ticker": "JPM",
                "name": "JPMorgan Chase",
                "role": "Banque universelle n°1 mondiale",
                "why": "ROTE >17%, capital fortress, IB + retail + gestion actifs sous un même toit.",
            },
            {
                "ticker": "V",
                "name": "Visa",
                "role": "Réseau de paiement global n°1",
                "why": "Asset-light, marges EBITDA >65%, exposition à la croissance des paiements digitaux sans risque crédit.",
            },
            {
                "ticker": "BLK",
                "name": "BlackRock",
                "role": "Gestionnaire d'actifs n°1 mondial (>10T$)",
                "why": "ETF (iShares) + Aladdin (infrastructure risque du secteur) = double moat.",
            },
            {
                "ticker": "GS",
                "name": "Goldman Sachs",
                "role": "Banque d'investissement & trading",
                "why": "Leader IB/M&A, trading obligataire; profite d'une reprise du cycle M&A et IPO.",
            },
        ],
        "backbone": [
            {
                "ticker": "CME",
                "name": "CME Group",
                "role": "Principale bourse de dérivés mondiale (taux, indices, commodités)",
                "why": "Toute couverture de taux ou de matières premières passe par CME. Hausse de volatilité = hausse des revenus.",
            },
            {
                "ticker": "MSCI",
                "name": "MSCI",
                "role": "Indices de référence & ESG scoring",
                "why": "15T$ d'actifs indexés sur les benchmarks MSCI; les gérants ne peuvent s'en passer.",
            },
            {
                "ticker": "FIS",
                "name": "Fidelity National Information Services",
                "role": "Infrastructure bancaire & traitement des paiements",
                "why": "Fait tourner le core banking de centaines de banques; invisible mais systémique.",
            },
            {
                "ticker": "CBOE",
                "name": "Cboe Global Markets",
                "role": "Bourse des options (VIX, SPX options)",
                "why": "Monopole de fait sur les options SPX et le calcul du VIX; croissance via dérivés 24h.",
            },
        ],
    },

    "Energy": {
        "label": "Énergie",
        "etf": "XLE",
        "description": (
            "Le secteur énergie reste dominé par le cycle du prix du pétrole et du gaz, "
            "mais la transition énergétique crée une bifurcation entre les acteurs traditionnels "
            "et les utilities/renouvelables. Les majors intégrées génèrent des FCF massifs à >70$/baril."
        ),
        "drivers": [
            "Prix du Brent & production OPEP+",
            "Transition énergétique & capex renouvelables",
            "Demande GNL (Europe post-Ukraine)",
            "Discipline capex des majors",
        ],
        "leaders": [
            {
                "ticker": "XOM",
                "name": "ExxonMobil",
                "role": "Major intégrée n°1 US (amont, raffinage, chimie)",
                "why": "Acquisition Pioneer; Permian + Guyana = croissance volume rare pour une major.",
            },
            {
                "ticker": "CVX",
                "name": "Chevron",
                "role": "Major intégrée avec fort exposition GNL & Kazakhstan",
                "why": "Bilan le plus solide des majors; retour actionnaire discipliné (buybacks + dividende).",
            },
            {
                "ticker": "COP",
                "name": "ConocoPhillips",
                "role": "E&P pure-play avec actifs de tier-1 (Permian, Alaska, LNG)",
                "why": "Coûts d'équilibre <40$/b; focus E&P sans intégration verticale = meilleure exposition prix.",
            },
        ],
        "backbone": [
            {
                "ticker": "SLB",
                "name": "SLB (ex-Schlumberger)",
                "role": "Services pétroliers & technologie de forage n°1 mondial",
                "why": "Aucun forage complexe (offshore, unconventional) sans SLB. Bénéficie du capex E&P mondial.",
            },
            {
                "ticker": "KMI",
                "name": "Kinder Morgan",
                "role": "Pipelines & terminaux gaz naturel (50% du gaz US transite)",
                "why": "Infrastructure réglementée = revenus quasi-fixes; dividende élevé et stable.",
            },
            {
                "ticker": "VLO",
                "name": "Valero Energy",
                "role": "Raffinage indépendant n°1 US + biofuels",
                "why": "Le carburant que vous utilisez a probablement été raffiné par Valero. Crack spread = levier FCF.",
            },
        ],
    },

    "ConsumerDiscretionary": {
        "label": "Consommation Discrétionnaire",
        "etf": "XLY",
        "description": (
            "Le secteur de la consommation discrétionnaire est cyclique et corrélé au pouvoir d'achat "
            "des ménages et à l'emploi. L'e-commerce et l'économie de l'expérience (voyages, loisirs) "
            "sont les principales thématiques de croissance structurelle."
        ),
        "drivers": [
            "Taux d'emploi & confiance des consommateurs",
            "Dominance e-commerce (Amazon)",
            "Économie de l'expérience (voyages, restaurants)",
            "Électrification automobile (Tesla)",
        ],
        "leaders": [
            {
                "ticker": "AMZN",
                "name": "Amazon",
                "role": "E-commerce n°1 + AWS + logistique",
                "why": "AWS finance l'e-commerce; Prime crée la fidélisation; logistics devient concurrent de FedEx/UPS.",
            },
            {
                "ticker": "TSLA",
                "name": "Tesla",
                "role": "VE + énergie + software autonome",
                "why": "Leader VE avec la meilleure marge brute auto; FSD et Robotaxi = optionalité considérable.",
            },
            {
                "ticker": "MCD",
                "name": "McDonald's",
                "role": "QSR mondial — modèle franchise défensif",
                "why": "98% franchisé = asset-light; pricing power démontré; dividende aristocrate.",
            },
        ],
        "backbone": [
            {
                "ticker": "ORLY",
                "name": "O'Reilly Automotive",
                "role": "Distribution pièces automobiles (aftermarket)",
                "why": "Le parc automobile vieillit → demande structurelle de pièces. Duopole avec AutoZone.",
            },
            {
                "ticker": "BKNG",
                "name": "Booking Holdings",
                "role": "Plateforme OTA (Booking.com, Priceline, Kayak)",
                "why": "Agrège hôtels/vols mondiaux; take-rate sur tout voyage = péage sur le tourisme mondial.",
            },
            {
                "ticker": "DHI",
                "name": "D.R. Horton",
                "role": "Constructeur résidentiel n°1 US",
                "why": "Pénurie structurelle de logements US; bénéficie de taux hypothécaires en baisse.",
            },
        ],
    },

    "Industrials": {
        "label": "Industrie",
        "etf": "XLI",
        "description": (
            "Le secteur industriel est au cœur de la réindustrialisation américaine (IRA, CHIPS Act) "
            "et de la modernisation des infrastructures mondiales. "
            "L'aérospatiale, la défense et l'automatisation sont les thématiques les plus portantes."
        ),
        "drivers": [
            "Réindustrialisation US (IRA, CHIPS Act)",
            "Modernisation des infrastructures",
            "Cycle de défense (OTAN, Indo-Pacifique)",
            "Automatisation & robotique industrielle",
        ],
        "leaders": [
            {
                "ticker": "CAT",
                "name": "Caterpillar",
                "role": "Équipements de construction & mines",
                "why": "Bénéficiaire direct des plans d'infrastructure; pricing power et services récurrents.",
            },
            {
                "ticker": "RTX",
                "name": "RTX (Raytheon)",
                "role": "Défense & moteurs d'avion (Pratt & Whitney)",
                "why": "Carnets de commandes défense record; duopole moteurs avec GE sur les programmes OTAN.",
            },
            {
                "ticker": "HON",
                "name": "Honeywell",
                "role": "Automatisation industrielle, aérospatiale & bâtiment",
                "why": "Conglomérat de haute qualité en cours de séparation; marges EBIT >20%.",
            },
        ],
        "backbone": [
            {
                "ticker": "GWW",
                "name": "W.W. Grainger",
                "role": "Distribution MRO (maintenance, repair, operations)",
                "why": "L'Amazon de la fourniture industrielle; toute usine commande chez Grainger.",
            },
            {
                "ticker": "FAST",
                "name": "Fastenal",
                "role": "Fixations & fournitures industrielles — vending machines en usine",
                "why": "Modèle unique d'onsite d'inventaire; indicateur avancé de l'activité manufacturière.",
            },
            {
                "ticker": "RSG",
                "name": "Republic Services",
                "role": "Gestion des déchets & économie circulaire",
                "why": "Duopole avec Waste Management; revenus récurrents, pricing indexé inflation.",
            },
        ],
    },

    "CommunicationServices": {
        "label": "Services de Communication",
        "etf": "XLC",
        "description": (
            "Ce secteur hybride mêle médias sociaux, streaming, télécoms et publicité digitale. "
            "Meta et Alphabet dominent la publicité en ligne tandis que Netflix réinvente "
            "la monétisation du contenu via abonnements et publicité."
        ),
        "drivers": [
            "Publicité digitale (AI-driven targeting)",
            "Streaming & économie du contenu",
            "Réalité augmentée / mixed reality",
            "Infrastructure télécom 5G",
        ],
        "leaders": [
            {
                "ticker": "META",
                "name": "Meta Platforms",
                "role": "Réseau social (FB, Instagram, WhatsApp) + IA Llama",
                "why": "3Md+ utilisateurs actifs; moteur publicitaire le plus efficace au monde; investissement IA massif.",
            },
            {
                "ticker": "NFLX",
                "name": "Netflix",
                "role": "Streaming n°1 mondial + publicité",
                "why": "Tier avec pub en fort croissance; live events (sport) = prochain catalyseur.",
            },
            {
                "ticker": "GOOGL",
                "name": "Alphabet / YouTube",
                "role": "YouTube — 2ème moteur de recherche & streaming n°2",
                "why": "YouTube Shorts capte la publicité TikTok; Google Search reste incontournable.",
            },
        ],
        "backbone": [
            {
                "ticker": "VZ",
                "name": "Verizon",
                "role": "Infrastructure télécom 4G/5G — réseau voix & données",
                "why": "Le tuyau invisible sur lequel repose tout le digital mobile; dividende élevé et stable.",
            },
            {
                "ticker": "TTWO",
                "name": "Take-Two Interactive",
                "role": "Jeux vidéo AAA (GTA, NBA 2K, Civilization)",
                "why": "GTA VI = catalyseur massif; gaming = plus grand marché entertainment mondial.",
            },
            {
                "ticker": "AKAM",
                "name": "Akamai Technologies",
                "role": "CDN & edge security — livraison du contenu internet",
                "why": "Un tiers du trafic web mondial passe par Akamai; chaque streaming s'appuie sur un CDN.",
            },
        ],
    },

    "ConsumerStaples": {
        "label": "Consommation de Base",
        "etf": "XLP",
        "description": (
            "Valeur refuge par excellence, ce secteur offre une demande inélastique et des dividendes "
            "stables. Il surperforme en récession mais sous-performe en phase de risk-on. "
            "Le pricing power et la gestion des coûts sont les principaux leviers de marge."
        ),
        "drivers": [
            "Pricing power & inflation alimentaire",
            "Parts de marché emerging markets",
            "Marques mondiales vs private label",
            "Canaux digitaux & DTC (direct-to-consumer)",
        ],
        "leaders": [
            {
                "ticker": "PG",
                "name": "Procter & Gamble",
                "role": "Produits ménagers & hygiène (Tide, Gillette, Pampers)",
                "why": "65 marques >1Md$ chacune; dividende aristocrate 67 ans; pricing power exceptionnel.",
            },
            {
                "ticker": "KO",
                "name": "Coca-Cola",
                "role": "Boissons n°1 mondial — modèle franchise",
                "why": "Modèle capital-light (embouteilleurs franchisés); exposition à la croissance EM.",
            },
            {
                "ticker": "WMT",
                "name": "Walmart",
                "role": "Distribution alimentaire & généraliste n°1 US",
                "why": "Résilience anti-cyclique; Walmart+ et publicité retail = nouveaux relais de croissance.",
            },
        ],
        "backbone": [
            {
                "ticker": "SYY",
                "name": "Sysco",
                "role": "Distribution alimentaire aux restaurants & hôtels",
                "why": "Alimente ~600k restaurants; 30%+ de part de marché foodservice US. Invisible, indispensable.",
            },
            {
                "ticker": "CLX",
                "name": "Clorox",
                "role": "Produits nettoyants & désinfectants",
                "why": "Pricing power sur marques emblématiques; exposé à la demande de santé publique.",
            },
            {
                "ticker": "CHD",
                "name": "Church & Dwight",
                "role": "Hygiène & santé grand public (Arm & Hammer, OxiClean)",
                "why": "Sous le radar des grands indices; croissance régulière, M&A discipliné.",
            },
        ],
    },

    "RealEstate": {
        "label": "Immobilier (REITs)",
        "etf": "XLRE",
        "description": (
            "Les REITs offrent une exposition immobilière liquide avec obligation de distribuer 90% "
            "des revenus. Très sensibles aux taux longs (spread vs T-note), ils sous-performent "
            "en période de hausse de taux mais rebondissent fortement lors des pivots monétaires."
        ),
        "drivers": [
            "Taux longs & spread immobilier",
            "Data centers & tours télécoms (REITs tech)",
            "Logistique & e-commerce (entrepôts)",
            "Pénurie résidentielle structurelle",
        ],
        "leaders": [
            {
                "ticker": "AMT",
                "name": "American Tower",
                "role": "Tours télécom — infrastructure 5G mondiale",
                "why": "220k+ tours dans 25 pays; les opérateurs paient des baux 5-10 ans récurrents.",
            },
            {
                "ticker": "PLD",
                "name": "Prologis",
                "role": "Entrepôts logistiques e-commerce n°1 mondial",
                "why": "Locataires = Amazon, FedEx, DHL; demande entrepôts portée par e-commerce structurel.",
            },
            {
                "ticker": "EQIX",
                "name": "Equinix",
                "role": "Data centers & interconnexion cloud",
                "why": "Là où AWS, Azure, Google se connectent physiquement; churn <2% par an.",
            },
        ],
        "backbone": [
            {
                "ticker": "WELL",
                "name": "Welltower",
                "role": "Immobilier de santé (EHPAD, cliniques)",
                "why": "Vieillissement = demande structurelle; partnership avec les grands réseaux de santé.",
            },
            {
                "ticker": "AVB",
                "name": "AvalonBay Communities",
                "role": "Appartements résidentiels classe A (côtes US)",
                "why": "Pénurie logement + loyers en hausse dans les grandes métropoles américaines.",
            },
            {
                "ticker": "VICI",
                "name": "VICI Properties",
                "role": "Immobilier casino & entertainment (Vegas, regional)",
                "why": "Baux triple-net 35-42 ans avec Caesars et MGM; rendement +5% très prévisible.",
            },
        ],
    },
}
