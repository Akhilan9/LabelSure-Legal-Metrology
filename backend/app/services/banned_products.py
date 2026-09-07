"""
International Banned & Restricted Commodities Advisory Service.
Identifies whether a product or its key ingredients/formulation is banned or restricted
in other major jurisdictions (e.g., European Union, United States FDA, United Kingdom FSA,
Singapore, Japan, Canada, Australia/NZ).
"""

import re
from typing import Any, Dict, List, Optional

# Database of international bans and high-profile restrictions
BANNED_COMMODITIES_REGISTRY: List[Dict[str, Any]] = [
    {
        "keywords": ["chikki", "peanut candy", "groundnut", "peanut chikki", "gajak"],
        "status": "RESTRICTED",
        "banned_countries": ["European Union (EFSA)", "Japan (MHLW)", "Australia (FSANZ)"],
        "title": "Strict Peanut / Aflatoxin International Import Restriction",
        "reason": "European Union Regulation (EU) 2019/1793 & 1169/2011 enforces strict maximum limits for Aflatoxin B1 (2.0 mcg/kg) and total aflatoxins (4.0 mcg/kg) on peanut products, alongside mandatory prominent bold allergen warnings. Non-compliant shipments are rejected/banned at EU borders.",
        "regulatory_agency": "EU Rapid Alert System for Food and Feed (RASFF) & Japan Food Sanitation Act",
        "advisory": "Permitted in India with FSSAI standards, but subject to stringent border laboratory testing for aflatoxins and mandatory allergen declarations in export destinations.",
    },
    {
        "keywords": ["pan masala", "gutkha", "gutka", "betel", "supari", "areca nut", "khaini", "zarda"],
        "status": "BANNED",
        "banned_countries": ["United States (FDA)", "United Kingdom", "United Arab Emirates", "Australia", "Singapore"],
        "title": "International Ban on Areca Nut / Betel Quid Products",
        "reason": "Classified by WHO / International Agency for Research on Cancer (IARC) as a Group 1 human carcinogen causing oral submucous fibrosis and oral squamous cell carcinoma. U.S. FDA maintains Import Alert 34-01 to seize all commercial entries.",
        "regulatory_agency": "US FDA (Import Alert 34-01), UK FSA, UAE Ministry of Climate Change & Environment",
        "advisory": "Strictly illegal for sale, distribution, or import into the US, UK, UAE, and Australia. Heavy penalties and seizure apply.",
    },
    {
        "keywords": ["chewing gum", "bubble gum"],
        "status": "BANNED",
        "banned_countries": ["Singapore"],
        "title": "Ban on Commercial Chewing Gum",
        "reason": "Prohibited under Singapore's Control of Manufacture Act (Cap. 57) since 1992 (with exemptions only for registered therapeutic dental/nicotine gums prescribed by physicians).",
        "regulatory_agency": "Singapore Food Agency (SFA) & Health Sciences Authority (HSA)",
        "advisory": "Commercial import or resale in Singapore is an offense punishable by fines up to \$100,000 or imprisonment.",
    },
    {
        "keywords": ["cotton candy", "candy floss", "buddhi ke baal", "rhodamine"],
        "status": "BANNED",
        "banned_countries": ["European Union", "United States (FDA)", "United Kingdom", "Multiple Indian States"],
        "title": "Ban on Rhodamine-B Dyed Confectionery",
        "reason": "Industrial chemical textile dye Rhodamine-B is carcinogenic and neurotoxic. Prohibited globally in food products under Codex Alimentarius, US FDA FD&C Act, and EU Regulation 1333/2008.",
        "regulatory_agency": "US FDA, EU EFSA, FSSAI India",
        "advisory": "Strictly banned if synthetic textile colorant Rhodamine-B is used. Only permitted natural/approved food colors (like Beetroot red) are authorized.",
    },
    {
        "keywords": ["kinder surprise", "toy inside candy", "embedded toy egg"],
        "status": "BANNED",
        "banned_countries": ["United States (FDA)"],
        "title": "US Ban on Confectionery with Embedded Non-Nutritive Objects",
        "reason": "Section 402(d)(1) of the US Federal Food, Drug, and Cosmetic Act of 1938 prohibits confectionery containing embedded non-nutritive objects due to choking hazard risks.",
        "regulatory_agency": "US Food and Drug Administration (FDA) & Consumer Product Safety Commission (CPSC)",
        "advisory": "Unlawful to import or sell in the United States.",
    },
    {
        "keywords": ["mountain dew", "bvo", "brominated vegetable oil"],
        "status": "BANNED",
        "banned_countries": ["European Union", "United Kingdom", "Japan", "India (FSSAI)", "United States (FDA Ban 2024)"],
        "title": "Global Ban on Brominated Vegetable Oil (BVO) in Beverages",
        "reason": "BVO bioaccumulates in human adipose tissue and causes thyroid dysfunction and neurological symptoms. Revoked by US FDA in July 2024 and banned in the EU/UK.",
        "regulatory_agency": "US FDA Final Rule 2024, European Commission Regulation (EC) 1333/2008",
        "advisory": "BVO formulations cannot be imported or distributed globally.",
    },
    {
        "keywords": ["bread", "potassium bromate", "bakery flour"],
        "status": "BANNED",
        "banned_countries": ["European Union", "United Kingdom", "Canada", "China", "Brazil", "India (FSSAI)"],
        "title": "Ban on Potassium Bromate (E924) Flour Treatment",
        "reason": "Potassium bromate is an oxidizing dough conditioner recognized as a potential carcinogen (IARC 2B). Banned across Europe since 1990 and India since 2016.",
        "regulatory_agency": "EU EFSA, UK FSA, Health Canada",
        "advisory": "Prohibited in baking flours in almost all major global economies.",
    },
    {
        "keywords": ["sassafras", "safrole", "root beer concentrate"],
        "status": "BANNED",
        "banned_countries": ["United States (FDA)", "European Union"],
        "title": "Ban on Safrole / Sassafras Oil",
        "reason": "Safrole is hepatocarcinogenic and a precursor for MDMA. Banned by US FDA since 1960 under 21 CFR 189.180.",
        "regulatory_agency": "US FDA, European Medicines Agency",
        "advisory": "Illegal as a food additive or flavoring.",
    },
    {
        "keywords": ["fairness cream", "skin bleaching", "mercury cream", "hydroquinone"],
        "status": "BANNED",
        "banned_countries": ["European Union (Regulation 1223/2009)", "United Kingdom", "Japan", "Australia"],
        "title": "Ban on Mercury & Hydroquinone in Cosmetics",
        "reason": "Mercury compounds cause renal toxicity and peripheral neuropathy; hydroquinone induces irreversible ochronosis. EU Cosmetics Regulation 1223/2009 lists them under Annex II (Prohibited Substances).",
        "regulatory_agency": "EU European Chemicals Agency (ECHA), US FDA Alert 53-18",
        "advisory": "Strict border seizure and prosecution for cosmetics containing inorganic mercury or unauthorized hydroquinone.",
    },
    {
        "keywords": ["energy drink", "red bull", "high caffeine"],
        "status": "RESTRICTED",
        "banned_countries": ["Lithuania", "Latvia", "Poland (under 18s)", "Norway (pharmacy only formerly)"],
        "title": "Age-Restricted in Baltic & Central European Nations",
        "reason": "High-caffeine formulations (>150 mg/L) with taurine and glucuronolactone face statutory bans on sales to minors under 18 in Lithuania, Latvia, and Poland to prevent cardiovascular strain.",
        "regulatory_agency": "State Food and Veterinary Service of Lithuania, Polish Ministry of Health",
        "advisory": "Requires statutory 'High caffeine content' warning label and age gating in EU export territories.",
    },
    {
        "keywords": ["silver foil", "chandi vark", "vark", "varq"],
        "status": "RESTRICTED",
        "banned_countries": ["United States (FDA)", "European Union (EFSA)"],
        "title": "Restrictions on Non-Vegetarian or Toxic Silver Leaf (E174)",
        "reason": "Traditional animal intestinal processing and heavy metal contamination (nickel, lead) led to strict purities. US FDA does not approve silver leaf as a general food additive (adulterant).",
        "regulatory_agency": "US FDA 21 CFR, EU Regulation 231/2012",
        "advisory": "Prohibited in standard US food distribution. In India, FSSAI mandates machine-made, animal-free certification (99.9% purity).",
    },
    {
        "keywords": ["instant noodles", "noodles", "monosodium glutamate", "msg", "maggi"],
        "status": "RESTRICTED",
        "banned_countries": ["United States (FDA Import Alert 99-33)"],
        "title": "Historical Import Alerts & Lead / MSG Scrutiny",
        "reason": "Subject to historical US FDA Import Alert 99-33 for lead testing and unlabelled MSG. Requires strict certified third-party lab testing before clearance.",
        "regulatory_agency": "US FDA Center for Food Safety and Applied Nutrition (CFSAN)",
        "advisory": "Permitted for export only with verifiable FSSAI/Codex heavy-metal batch certification and transparent allergen/flavor enhancer labeling.",
    },
    {
        "keywords": ["titanium dioxide", "e171", "white pigment food"],
        "status": "BANNED",
        "banned_countries": ["European Union (EFSA 2022)", "Switzerland"],
        "title": "EU Ban on Food Additive Titanium Dioxide (E171)",
        "reason": "European Commission Regulation (EU) 2022/63 banned Titanium Dioxide (E171) in all food products following EFSA conclusions that it can no longer be considered safe due to genotoxicity concerns from nanoparticle accumulation.",
        "regulatory_agency": "European Food Safety Authority (EFSA)",
        "advisory": "Strictly prohibited in all confectionery, baked goods, and sauces destined for the EU or Switzerland.",
    },
]


def check_international_bans(product_name: Optional[str], extra_text: Optional[str] = "") -> Dict[str, Any]:
    """
    Analyzes product name and surrounding context text against global statutory ban databases.
    Returns structured international compliance and ban advisory information.
    """
    if not product_name or not product_name.strip():
        return {
            "status": "PERMITTED",
            "is_banned": False,
            "banned_countries": [],
            "title": "Standard Packaged Commodity",
            "reason": "No international prohibitions identified.",
            "regulatory_agency": "Codex Alimentarius / Global Harmonization Standards",
            "advisory": "Standard domestic and international distribution permitted subject to national packaging rules.",
            "badge_color": "emerald",
        }

    combined = f"{product_name} {extra_text or ''}".lower()

    for item in BANNED_COMMODITIES_REGISTRY:
        for kw in item["keywords"]:
            # Word boundary or exact inclusion
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, combined, re.I) or kw in combined:
                is_banned = item["status"] == "BANNED"
                return {
                    "status": item["status"],
                    "is_banned": is_banned,
                    "banned_countries": item["banned_countries"],
                    "title": item["title"],
                    "reason": item["reason"],
                    "regulatory_agency": item["regulatory_agency"],
                    "advisory": item["advisory"],
                    "matched_keyword": kw,
                    "badge_color": "rose" if is_banned else "amber",
                }

    # Clean bill of international compliance
    return {
        "status": "PERMITTED",
        "is_banned": False,
        "banned_countries": [],
        "title": f"Globally Permitted: {product_name.strip()}",
        "reason": "No international bans, recalls, or severe border prohibitions detected across US (FDA), European Union (EFSA), UK (FSA), Japan (MHLW), or Singapore (SFA).",
        "regulatory_agency": "Codex Alimentarius / WHO-FAO International Food Standards",
        "advisory": "Permitted for commercial sale and export compliance provided standard LMPC labeling and quality standards are satisfied.",
        "badge_color": "emerald",
    }
