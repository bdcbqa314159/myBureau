# Ton site, mode d'emploi

Tout ce qu'il faut savoir pour voir le site sur ton Mac, le modifier, et
le publier. Aucune connaissance technique supposée.

Tu n'as besoin de rien installer d'autre que ce qui est décrit ici, et
tu ne taperas qu'une seule commande dans ta vie — celle de l'étape 1.

---

## Les deux adresses

Garde-les sous la main — tout le reste du guide en dépend.

| | |
|---|---|
| **le site en ligne**, à regarder tout de suite | <https://bdcbqa314159.github.io/myBureau/> |
| **le dépôt**, d'où tu copieras le site sur ton Mac | <https://github.com/bdcbqa314159/myBureau> |

---

## Ce qu'il faut comprendre d'abord, en trois phrases

Le site **est** un dossier de fichiers. Les dossiers que tu vois sur ton
Mac deviennent les dossiers que les visiteurs voient à l'écran, et les
photos que tu y déposes deviennent les photos des pages.

Il y a donc deux copies : celle sur ton Mac, où tu travailles
tranquillement, et celle en ligne, que tout le monde voit. **Rien de ce
que tu fais sur ton Mac n'apparaît en ligne tant que tu ne l'as pas
publié**, et publier est un bouton.

Tu peux donc tout essayer sans aucun risque.

---

## Étape 1 — installer les deux outils (une seule fois)

### a. Homebrew

Homebrew sert à installer l'outil suivant. Ouvre **Terminal**
(⌘-espace, tape `terminal`, Entrée), colle cette ligne, Entrée, et
suis ce qu'il demande — il te demandera ton mot de passe de session,
c'est normal :

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Ça prend quelques minutes. C'est la seule commande de tout ce guide.

### b. GitHub Desktop

C'est l'application qui fait l'aller-retour entre ton Mac et GitHub,
sans ligne de commande.

1. va sur <https://desktop.github.com>, télécharge, installe
2. ouvre-la, **Sign in to GitHub.com**, connecte-toi avec ton compte
3. menu **File → Clone repository…**, onglet **URL**, et colle l'adresse
   du dépôt dans le premier champ :

```
https://github.com/bdcbqa314159/myBureau
```

4. **Clone**

> Elle te propose aussi la liste de tes dépôts : **myBureau n'y est
> pas**, parce qu'il est pour l'instant sous le compte de Bernardo et
> pas sous le tien. C'est pour ça qu'on passe par l'adresse. Rien
> d'anormal.

Elle te demande où le mettre. L'endroit par défaut (`Documents/GitHub/`)
est parfait. À la fin tu as un dossier `myBureau` dans
`Documents/GitHub/` : c'est le site.

---

## Étape 2 — voir le site

Ouvre le dossier `myBureau` dans le Finder et **double-clique sur
`preview.command`**.

Une fenêtre noire s'ouvre — c'est normal, laisse-la tranquille — puis ton
navigateur ouvre le site.

> **La première fois**, il installe Zola (le programme qui fabrique le
> site) et ça prend une minute. Les fois suivantes c'est immédiat.

> Si macOS dit que le fichier *ne peut pas être ouvert car il provient
> d'un développeur non identifié* : clic droit sur `preview.command` →
> **Ouvrir** → **Ouvrir**. C'est à faire une seule fois.

**Laisse la fenêtre noire ouverte pendant que tu travailles.** Chaque
fois que tu enregistres un fichier, la page se recharge toute seule.

Pour arrêter : clique dans la fenêtre noire et fais **Ctrl-C**, ou ferme
simplement la fenêtre.

---

## Étape 3 — modifier le site

Tout se passe dans `Documents/GitHub/myBureau/content/`. Il n'y a rien à
comprendre d'autre que ça.

### Avec quoi ouvrir les fichiers `.md`

**TextEdit**, qui est déjà sur ton Mac : clic droit sur le fichier →
**Ouvrir avec → TextEdit**. Aucune application à installer.

### Ajouter un projet

Le plus simple, et celui qui ne se trompe pas : **duplique un projet qui
existe déjà.** Dans le Finder, va dans `content/da/`, clic droit sur un
dossier de projet → **Dupliquer** (⌘-D), puis :

1. renomme le dossier (`mon-projet`, sans accent ni espace)
2. jette les images qui étaient dedans, dépose les tiennes
3. ouvre `index.md` **et** `index.en.md` — il y en a un par langue — et
   change le titre entre les guillemets dans les deux
4. dans les deux, change aussi les deux nombres `x` et `y` : le dossier
   dupliqué a gardé ceux de l'original, et sans ça la nouvelle icône se
   pose exactement sur celle que tu as dupliquée

C'est tout. Le projet apparaît sur le bureau et a sa page. Les images
s'affichent dans l'ordre de leur nom — `01.jpg`, `02.jpg`, `03.jpg`.

> **Pourquoi dupliquer plutôt que créer.** Un fichier créé de zéro dans
> TextEdit arrive en texte enrichi et s'enregistre en `index.md.txt` —
> dans les deux cas le dossier n'apparaît pas du tout sur le site, sans
> aucun message d'erreur. Le dossier dupliqué, lui, est déjà correct.
> Si tu y tiens, le contenu minimum d'un `index.md` est :

```
+++
title = "mon projet.jpg"
+++
```

> Le `.jpg` à la fin du titre n'est pas obligatoire, mais il décide de
> l'icône : `.jpg` donne une photo, `.mov` une pellicule, le reste un
> document.

### Écrire un texte de présentation

Sous le deuxième `+++`, écris ce que tu veux :

```
+++
title = "mon projet.jpg"
+++

Une série faite en une nuit, à la lumière des phares.
```

### Ajouter un dossier (un nouveau bureau)

Pareil, mais le fichier s'appelle **`_index.md`** (avec le tiret bas) et
contient une ligne de plus :

```
+++
title = "scénographie"
template = "section.html"
+++
```

Il apparaît sur le bureau **et** dans le bandeau du haut, tout seul.

### Décider où une icône se pose

Optionnel. Sans rien, elle se range sur une grille :

```
+++
title = "mon projet.jpg"

[extra]
x = 40
y = 60
+++
```

`x` et `y` sont des pourcentages : `x = 0` tout à gauche, `x = 100` tout
à droite.

### Décrire une photo pour les personnes qui ne la voient pas

Optionnel, et c'est à toi de l'écrire — personne d'autre ne peut décrire
ta photo :

```
+++
title = "mon projet.jpg"

[extra.alt]
"01.jpg" = "Deux silhouettes sur une plage, au crépuscule."
+++
```

### Changer les textes du site lui-même

Les mots qui ne sont pas les tiens — *contact*, *retour à*, les messages
du formulaire — sont tous dans `config.toml`, dans le bloc
`[translations]`. Une ligne par mot.

---

## Étape 4 — publier

> **Pas encore.** Tant que le dépôt est celui de Bernardo, **Push
> origin** sera refusé : tu n'as pas les droits d'écriture dessus, et
> c'est normal à ce stade. Pour l'instant tu travailles sur ta copie,
> tu regardes le résultat avec `preview.command`, et tu lui envoies tes
> remarques. Cette étape devient la tienne le jour où le dépôt est le
> tien — la suite est écrite pour ce jour-là.

Dans **GitHub Desktop** :

1. à gauche, la liste de ce que tu as changé — regarde-la, c'est ton
   dernier contrôle
2. en bas à gauche, écris une petite phrase (« nouveau projet janvier »)
3. **Commit to main**
4. en haut, **Push origin**

Attends une à deux minutes : le site en ligne se met à jour tout seul.

> Si tu veux vérifier que ça s'est bien passé : sur github.com, dans le
> dépôt, l'onglet **Actions** montre une coche verte quand c'est publié.
> Une croix rouge veut dire que quelque chose n'allait pas et que **rien
> n'a été publié** — le site en ligne est resté comme avant. Envoie une
> capture à Bernardo.

---

## Quand quelque chose ne va pas

### La fenêtre noire affiche des lignes et le navigateur ne s'ouvre pas

Elle dit `The site did not build` et montre le fichier en cause. Annule
ta dernière modification (⌘-Z dans ton éditeur, ou dans GitHub Desktop :
clic droit sur le fichier → **Discard changes**), et ça repart.

**Le site en ligne n'est pas touché.** Une erreur chez toi reste chez toi.

### La fenêtre noire dit « X thing(s) worth a look »

Ce ne sont **pas** des erreurs : le site fonctionne. Ce sont des lignes
de tes fichiers qui ne font rien. Chaque remarque nomme le fichier, puis
donne la correction sur la ligne `fix:`. Les trois courantes :

| ce qui est écrit | ce que ça veut dire |
|---|---|
| `there is no such file` | le nom d'une icône est mal orthographié |
| `no https://` | un lien vers l'extérieur sans `https://` au début |
| `is not shown on the site` | une image en `.tiff`, `.psd`… — réexporte en JPEG |
| `is not index.md` | le fichier texte du dossier n'est pas nommé exactement `index.md` — le dossier n'est pas sur le site |
| `the same title as` | deux projets portent le même nom, en général un dossier dupliqué dont un seul fichier de langue a été renommé |

### La fenêtre noire dit `Error when parsing front matter`

Ce sont presque toujours les guillemets. Les lignes entre les `+++`
veulent des guillemets droits `"`. Des guillemets courbes `“ ”` — ceux
que tu obtiens en collant un titre depuis un mail, Word ou Pages — et le
site ne se construit plus.

Réécris la ligne en tapant les guillemets toi-même. Si ton éditeur les
transforme en courbes pendant que tu tapes, cherche **Guillemets
typographiques** (*Smart quotes*) dans ses réglages et décoche-le.

### Un dossier que j'ai ajouté n'apparaît nulle part

Son fichier texte n'est pas nommé `index.md`. Affiche les extensions
dans le Finder (**Finder → Réglages → Avancé → Afficher tous les noms
d'extension de fichier**) et regarde : un `index.md.txt` ou un
`index.rtf` ne compte pas. Renomme-le en `index.md`.

### Une photo n'apparaît pas

Son format n'est probablement pas reconnu. Le site affiche `.jpg`,
`.jpeg`, `.png`, `.webp`, `.avif`, `.gif`. Un `.tiff` ou un `.psd` ne
s'affiche pas — réexporte en JPEG.

### J'ai tout cassé

Dans GitHub Desktop, menu **Branch → Discard all changes**. Tu retrouves
exactement l'état de la dernière publication. Rien n'est jamais perdu de
ce qui a été publié.

---

## Ce qu'il ne faut pas faire

- **ne mets jamais dans ce dossier** un document qu'un client t'a envoyé
  (brief, deck, maquette) : ce dépôt est public. Ces fichiers vont dans
  `_ref/`, qui n'est jamais publié.
- ne touche pas aux dossiers `templates/`, `src/`, `static/css/` et
  `tools/` — c'est la mécanique. Si quelque chose doit y changer, c'est
  pour Bernardo.

---

## En résumé

| | |
|---|---|
| voir le site en ligne | <https://bdcbqa314159.github.io/myBureau/> |
| voir le site sur ton Mac | double-clic sur `preview.command` |
| ajouter un projet | duplique un dossier de projet, remplace les images |
| écrire un texte | sous le deuxième `+++` |
| publier | GitHub Desktop → Commit → Push |
| tout annuler | GitHub Desktop → Branch → Discard all changes |
