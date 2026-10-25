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

### Le panneau

Deux onglets s'ouvrent, pas un : ton site, et **le panneau**.

Au milieu du panneau, **c'est ton site** — la vraie page, pas un dessin.

> Dans le panneau, **un clic sert à modifier**, pas à ouvrir. Clique une
> icône : elle s'entoure de bleu et ses réglages apparaissent à droite.
> **Double-clique** pour entrer dedans. Attrape-la pour la déplacer.

Tu peux :

- **attraper une icône dans la page et la poser** où tu veux — sa place
  est enregistrée tout de suite, dans les deux langues
- **changer un nom ou un texte** dans la colonne de droite, une langue à
  la fois
- **changer le fond d'écran** d'un bureau : dépose une image sur le carré
  à droite
- **changer l'apparence** de n'importe quoi : dépose une image sur le
  petit carré « apparence ». C'est la seule façon de donner une tête à un
  dossier.
- **créer** un projet ou un dossier : en bas à gauche, choisis **dans
  quel dossier**, puis quoi (des photos, un film, un document, une page,
  un dossier), donne un nom, Créer. Le panneau te dit ce que ça va faire
  avant de le faire.

> **« un document »** ne veut pas dire que le site montrera ton PDF — il
> ne sait pas les afficher. Ça veut dire que l'icône aura l'air d'un
> document. Exporte les pages du PDF en JPEG et dépose-les : ce sont
> elles qu'on verra.

> **Un dossier ne fait pas la même chose partout.** Sur la page
> d'accueil, il a sa propre page et une place dans le bandeau. Rangé dans
> un autre dossier, il s'ouvre comme une fenêtre. Et tant qu'il est vide,
> il ouvre sa page — c'est normal, mets quelque chose dedans.
- **regarder** une chose plutôt que le bureau où elle est posée : le
  bouton « regarder » au-dessus de la page
- **ranger** : attrape une chose **dans la page** et lâche-la sur un
  dossier — il s'entoure de vert quand il peut la prendre. Ça marche
  aussi depuis la liste de gauche. Tout part avec — les deux langues, les photos, ce qu'il y a
  dedans. Son adresse change.
- **jeter** : le bouton rouge en bas à droite. Annuler la ramène.
- **un film** : dépose la vidéo sur « le film », et une image sur
  « l'affiche » — c'est l'image qu'on voit avant de lancer.

> Chaque case ne prend qu'une sorte de fichier. Si tu te trompes, le
> panneau te dit où il fallait la déposer. Et si le site ne sait pas
> montrer ton fichier — un PDF, un .psd — il te dit quoi faire à la
> place.
- **cliquer un projet** pour voir ses photos
- **déposer des photos** dessus : elles sont numérotées toutes seules.
  La première est l'icône du projet.
- **réordonner** les photos en les faisant glisser
- **Annuler** : reprend la dernière chose faite, même une photo jetée

Tout ce que fait le panneau, tu peux aussi le faire à la main dans les
fichiers — c'est le même dossier `content/`. Si tu modifies un fichier
dans TextEdit, le panneau s'en aperçoit et se met à jour.

> Le panneau ne marche que sur ton Mac, pendant que la fenêtre noire est
> ouverte. Il ne touche jamais au site en ligne.

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

> **L'ordre fait la mise en page.** La première image ouvre la page en
> grand, toute la largeur. Les suivantes se rangent deux par deux, avec
> de l'air autour. Pour changer laquelle ouvre la page, renomme-la :
> celle qui vient en premier dans l'ordre des noms gagne.
>
> Une image verticale n'est jamais coupée — elle est simplement limitée
> en hauteur pour qu'on voie la suite de la page sans faire défiler
> pendant dix secondes.

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

### L'icône d'un projet, c'est le projet

Tu n'as rien à faire : **l'icône d'un projet est sa première image.** Le
calendrier montre le calendrier, la brochure montre sa couverture. Le
bureau se remplit de ton travail et pas de petits dessins gris.

C'est `01.jpg` qui sert d'icône — celle qui est la première dans l'ordre
des noms. Pour en choisir une autre, mets dans le dossier un fichier
appelé **`icon`** :

```
mon-projet/
  icon.png        ← l'icône, et elle n'apparaît pas dans le projet
  01.jpg
  02.jpg
  index.md
```

Une image nommée `icon` sert d'icône et **n'est jamais montrée** parmi
les photos du projet. C'est aussi comme ça qu'on donne une texture à un
dossier — le léopard, le croco — en mettant un `icon.png` à côté de son
`_index.md`.

> S'il n'y a aucune image dans le dossier, c'est la fin du titre qui
> décide : `.jpg` donne une photo, `.mov` une pellicule, le reste un
> document.

### Ce qui se passe quand on clique

Une seule règle : **un clic montre la chose**, il ne t'emmène pas
ailleurs. Un aperçu s'ouvre sur le bureau, comme la barre d'espace sur un
Mac. Et dans le coin de la fenêtre, le bouton **⬜** ouvre la vraie page
du projet, en grand, si tu veux aller plus loin.

Deux exceptions, et elles tombent toutes seules :

- un dossier qui contient une **vidéo** est un film : il s'ouvre comme un
  film, avec ton texte à côté — sauf si tu demandes sa page, voir plus bas
- un dossier **sans aucune image** n'a rien à montrer en aperçu : il va
  directement à sa page

#### Si un projet mérite sa page tout de suite

Certains projets ne se regardent pas en petit. Une ligne le dit :

```
+++
title = "grocery list.png"

[extra]
opens = "page"
+++
```

Rien du tout, et c'est l'aperçu qui s'ouvre.

> Ça marche aussi pour une vidéo. `opens = "page"` sur un film l'envoie
> sur sa page, où la vidéo s'affiche en grand avec les photos en dessous
> — pratique pour un projet qui a beaucoup à raconter.

### Écrire un texte de présentation

Sous le deuxième `+++`, écris ce que tu veux :

```
+++
title = "mon projet.jpg"
+++

Une série faite en une nuit, à la lumière des phares.
```

### La page pellicules

Dans le panneau, choisis-la et tu vois toutes ses photos : tu peux les
réordonner, en jeter, en déposer de nouvelles. Elle n'a pas de fond
d'écran — c'est une galerie, pas un bureau — et on ne peut rien ranger
dedans à part des photos.


Celle-là n'est pas un bureau : c'est une galerie. Dépose tes photos à
côté de son `_index.md` et elles apparaissent, en cinq colonnes. Pas de
`index.md` à écrire, pas de dossier par photo.

Un clic sur une photo l'ouvre en grand dans une fenêtre. Échap la ferme.

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

> **Où tu le mets change ce qu'il fait.** Un dossier posé sur la page
> d'accueil ouvre **un nouveau bureau**, en plein écran, avec son propre
> fond d'écran — c'est le cas de `DA`, `graphic design` et `pellicules`.
> Un dossier rangé *à l'intérieur* d'un de ceux-là ouvre une **fenêtre**
> sur le bureau où il est posé, sans quitter la page.

### Changer le fond d'écran d'un bureau

Dépose une image appelée **`wallpaper.jpg`** à côté du `_index.md` du
bureau. C'est tout.

```
content/da/
    _index.md
    _index.en.md
    wallpaper.jpg     ← le fond de ce bureau
```

Rien à écrire, aucun chemin à taper. Elle sert **les deux langues**, et
les dossiers rangés à l'intérieur de ce bureau la reprennent aussi — sauf
si tu leur en donnes une à eux.

> Si tu remplaces une image par une autre et que tu vois encore
> l'ancienne : ton navigateur l'a gardée en mémoire. Recharge en appuyant
> sur **⌘-Maj-R**, ou attends quelques minutes.

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
