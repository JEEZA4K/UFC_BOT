# 🥊 UFC Pronos Bot — Guide d'installation

## Ce que fait le bot

- 🔍 **Récupère automatiquement** les combats du prochain événement UFC
- 🗳️ **Boutons cliquables** pour voter sur chaque combat
- 🥊 Choix du **gagnant**, de la **méthode** (KO/Soumission/Décision) et du **round**
- 🏆 **Classement** mis à jour automatiquement après chaque combat
- 📊 **Stats personnelles** pour chaque membre

## Système de points

| Prédiction | Points |
|---|---|
| ✅ Bon gagnant | +1 pt |
| ⚡ Bonne méthode | +1 pt |
| 🎯 Bon round | +2 pts |

Maximum **4 pts** par combat si tu vises tout juste !

---

## ÉTAPE 1 — Créer l'application Discord (5 min)

1. Va sur https://discord.com/developers/applications
2. Clique **"New Application"** → donne un nom (ex: "UFC Pronos")
3. Clique sur **"Bot"** dans le menu gauche
4. Clique **"Add Bot"** → confirme
5. Sous **"TOKEN"**, clique **"Copy"** → copie ce token (garde-le secret !)
6. Active ces options dans la section **"Privileged Gateway Intents"** :
   - ✅ SERVER MEMBERS INTENT
   - ✅ MESSAGE CONTENT INTENT
7. Va dans **"OAuth2" → "URL Generator"**
   - Coche **"bot"** et **"applications.commands"**
   - Dans "Bot Permissions", coche :
     - Send Messages
     - Embed Links
     - Use Slash Commands
   - Copie l'URL générée et ouvre-la pour inviter le bot sur ton serveur

---

## ÉTAPE 2 — Déployer sur Railway (10 min, GRATUIT)

1. Va sur https://railway.app et crée un compte (avec GitHub c'est plus simple)
2. Clique **"New Project" → "Deploy from GitHub repo"**
   - (Upload les fichiers du bot ou crée un repo GitHub avec)
3. Une fois le projet créé, clique sur ton service → **"Variables"**
4. Ajoute la variable :
   - `DISCORD_TOKEN` = ton token copié à l'étape 1
5. Railway va automatiquement détecter le `requirements.txt` et lancer le bot !

> 💡 **Alternative gratuite** : tu peux aussi utiliser **Render.com** (même principe)

---

## ÉTAPE 3 — Configurer le bot sur Discord

Une fois le bot en ligne sur ton serveur :

1. Dans le canal où tu veux les pronos, tape :
   ```
   /setup canal:#nom-du-canal
   ```

2. Pour charger automatiquement le prochain événement UFC :
   ```
   /charger_event
   ```

3. Pour poster les boutons de vote :
   ```
   /poster_pronos
   ```

C'est tout ! Tes amis peuvent maintenant cliquer sur les combats pour voter. 🎉

---

## Commandes disponibles

### Pour les admins
| Commande | Description |
|---|---|
| `/setup` | Définir le canal des pronos |
| `/charger_event` | Charger auto le prochain event UFC |
| `/creer_event` | Créer un event manuellement |
| `/ajouter_combat` | Ajouter un combat manuellement |
| `/poster_pronos` | Poster les boutons de vote |
| `/resultat` | Entrer le résultat d'un combat |
| `/liste_combats` | Voir les combats + leurs IDs |
| `/stats_combat` | Stats des votes pour un combat |

### Pour tout le monde
| Commande | Description |
|---|---|
| `/mon_prono` | Voir tous tes pronos de l'event |
| `/mon_score` | Voir tes stats personnelles |
| `/classement` | Voir le classement général |

---

## Workflow le jour d'un UFC

1. Vendredi/Samedi matin : `/charger_event` → `/poster_pronos`
2. Les gars votent avant le début
3. Au fur et à mesure des combats : `/resultat combat_id:X gagnant:NOM methode:KO/TKO round_fin:2`
4. Le bot poste les points automatiquement dans le canal
5. `/classement` pour voir qui mène !
