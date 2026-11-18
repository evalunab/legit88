# 🌾 Legit88 — MVP

> Colle une annonce de travail agricole (Facebook, Gumtree, WhatsApp) ou une capture d'écran : en ~30 secondes, Legit88 dit si elle présente des signaux de risque et si le job comptera pour les 88 jours du Working Holiday Visa.

---

## 1. Comment ça marche (en une image)

```
 Annonce (texte ou capture)
          │
          ▼
 ① EXTRACTION  ─ l'IA (Gemini 2.5 Flash via OpenRouter) lit l'annonce
   extractor.py   et remplit une "fiche" : employeur, ABN, code postal, salaire, frais...
                  (sans clé IA : des règles simples prennent le relais)
          │
          ▼
 ② VÉRIFICATIONS (checks.py + abn.py)
   • ABN valide ? actif ? au bon nom ?      → registre officiel ABN Lookup
   • Code postal éligible aux 88 jours ?     → liste officielle (data/regional_postcodes.csv)
   • Salaire ≥ minimum légal agricole ?      → Horticulture Award (1er juillet 2026)
   • Signaux d'alerte : frais à l'avance, cash, "visa garanti", urgence, agence d'intérim…
          │
          ▼
 ③ VERDICT (verdict.py)   🔴 au moins 1 signal rouge
                          🟠 au moins 2 signaux orange
                          🟢 sinon
          │
          ▼
 ④ PAGE WEB (app.py, Streamlit) : verdict + explications + questions à poser à l'employeur
```

**Pourquoi c'est mieux que ChatGPT :** l'IA ne sert qu'à *lire* l'annonce. Le jugement repose sur des **données officielles** (registre des entreprises, liste des codes postaux, salaires minimum) et des règles transparentes, qu'on peut expliquer au jury.

---

## 2. Les fichiers, un par un

| Fichier | Rôle (en mots simples) |
|---|---|
| `app.py` | La page web. Chaque ligne `st.…` dessine un élément (titre, zone de texte, bouton). |
| `legit88/models.py` | Les "formulaires" partagés : `JobAd` (ce qu'on a lu), `Finding` (un résultat), `Report` (le verdict). |
| `legit88/extractor.py` | Lit l'annonce : avec l'IA si une clé existe, sinon avec des règles (expressions régulières). |
| `legit88/abn.py` | Vérifie l'ABN : formule officielle de contrôle (hors ligne) + registre ABN Lookup (en ligne). |
| `legit88/checks.py` | Toutes les vérifications : code postal, salaire, employeur, signaux d'alerte. |
| `legit88/verdict.py` | Combine les résultats en un verdict 🔴 🟠 🟢 et liste les questions à poser. |
| `legit88/config.py` | Lit les clés secrètes (jamais écrites dans le code). |
| `data/regional_postcodes.csv` | Les codes postaux "regional Australia" pour le travail agricole. |
| `tests/` | Tests automatiques + 3 annonces **fictives** d'exemple (pratiques pour la démo). |
| `requirements.txt` | La liste des bibliothèques Python à installer. |

---

## 3. Lancer l'app sur ton ordinateur (≈ 15 min)

**Prérequis :** Python 3.10 ou plus récent ([python.org](https://www.python.org/downloads/)) et un éditeur, par exemple VS Code.

Ouvre un terminal **dans le dossier `legit88`**, puis tape ces commandes une par une :

```bash
# 1. Créer un "environnement virtuel" : une boîte isolée pour les bibliothèques du projet
python -m venv .venv

# 2. L'activer
source .venv/bin/activate          # Mac / Linux
# .venv\Scripts\activate           # Windows

# 3. Installer les bibliothèques
pip install -r requirements.txt

# 4. Lancer les tests (tout doit être vert : "15 passed")
python -m pytest

# 5. Lancer l'app
streamlit run app.py
```

Ton navigateur s'ouvre sur `http://localhost:8501`. **Sans clé, l'app marche déjà** en "mode démo" (lecture par règles) : choisis une annonce d'exemple et clique sur *Check this ad*.

---

## 4. Ajouter les clés (pour la vraie version)

1. **Clé IA OpenRouter** : crée un compte sur [openrouter.ai](https://openrouter.ai), puis *Keys → Create key*. Utilise les crédits fournis par l'école (10 $/étudiant). Une analyse coûte environ 0,002 $, soit des milliers d'analyses.
2. **Clé ABN Lookup (gratuite)** : inscris-toi sur [abr.business.gov.au → Web services registration](https://abr.business.gov.au/Documentation/WebServiceRegistration). Tu reçois un "GUID" par email (compte quelques jours, **fais-le aujourd'hui**).
3. Copie `.streamlit/secrets.toml.example` en `.streamlit/secrets.toml` et colle tes deux clés dedans.
4. Relance `streamlit run app.py` : le bandeau "Demo mode" disparaît, et les captures d'écran fonctionnent.

> ⚠️ `secrets.toml` est dans `.gitignore` : il ne partira jamais sur GitHub. Ne colle jamais une clé directement dans le code.

---

## 5. Mettre l'app en ligne (lien à rendre le 25 novembre)

1. **GitHub** : crée un dépôt (repository), puis envoie le dossier :
   ```bash
   git init
   git add .
   git commit -m "Legit88 MVP"
   git branch -M main
   git remote add origin https://github.com/<ton-compte>/legit88.git
   git push -u origin main
   ```
2. **Streamlit Community Cloud** (gratuit) : va sur [share.streamlit.io](https://share.streamlit.io), connecte GitHub, clique *Create app*, choisis ton dépôt, la branche `main` et le fichier `app.py`.
3. Dans *Advanced settings → Secrets*, colle le **contenu** de ton `secrets.toml`.
4. *Deploy* : tu obtiens un lien public du type `https://legit88.streamlit.app`.

*(Alternative : Google Cloud Run avec les crédits GCP de l'école ; demande à Baptiste si tu préfères.)*

---

## 6. Données à vérifier avant la démo

| Donnée | Où dans le code | Source officielle |
|---|---|---|
| Salaire minimum : 25,74 A$/h (permanent), 32,18 A$/h (casual), à partir du 1er juillet 2026 | `checks.py`, en haut | [Fair Work — Pay and piece rates](https://horticulture.fairwork.gov.au/pay-and-piece-rates) |
| Codes postaux "regional Australia" | `data/regional_postcodes.csv` | [Home Affairs — specified work conditions](https://immi.homeaffairs.gov.au/what-we-do/whm-program/specified-work-conditions) (liste mise à jour le 5 avril 2025) |
| Registres des licences d'intérim (QLD, VIC, SA) | `checks.py` → `LABOUR_HIRE_REGISTERS` | Sites des États |

La liste NSW et les "tout l'État" (SA, TAS, NT) viennent directement des textes officiels. **Compare les lignes VIC, QLD et WA avec la page Home Affairs** avant la démo : c'est une liste à recopier telle quelle.

---

## 7. Limites connues (à dire honnêtement au jury) et prochaines étapes

- **Codes postaux** : seule la liste agricole "regional Australia" est chargée. Le tourisme/hôtellerie (Northern et remote Australia) est seulement signalé 🟠.
- **Licences d'intérim** : on renvoie vers le registre de l'État, mais on n'interroge pas encore les registres automatiquement.
- **Le rouge n'est pas une accusation** : l'app parle de *signaux de risque* ; c'est volontaire (risque juridique de diffamation).
- **Mesures de traction** : chaque analyse et chaque clic sur le bouton "88-day pass" (A$9,99, faux bouton pour tester l'envie de payer) sont enregistrés anonymement dans `data/events.csv`. Sur Streamlit Cloud, ce fichier s'efface quand l'app redémarre : note les chiffres régulièrement, ou branche une Google Sheet plus tard.
- **Prochaines étapes** : version française de l'interface, recherche dans les registres de licences, partage du rapport en PDF, extension WhatsApp.

---

## 8. Planning jusqu'au 25 novembre

| Jour | À faire |
|---|---|
| Mer. 18 | Lancer en local, demander le GUID ABN Lookup, créer la clé OpenRouter |
| Jeu. 19 | Dépôt GitHub + mise en ligne sur Streamlit Cloud (version démo) |
| Ven. 20 | Ajouter les clés en ligne, tester 5 vraies annonces trouvées sur Facebook / Gumtree |
| Sam. 21 – Dim. 22 | Vérifier les codes postaux, tester 15 annonces de plus, noter ce qui rate |
| Lun. 23 – Mar. 24 | Corriger, faire tester par 3 backpackers, préparer la revue de code |
| **Mer. 25** | **Rendre le lien en ligne + le dépôt GitHub** |
