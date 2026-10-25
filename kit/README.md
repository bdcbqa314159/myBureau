# The test kit

Files to drag into the panel. Every one is **generated** — by
`tools/kit.py`, with ffmpeg and a hand-written PDF writer — so nothing
here is anyone's photograph and nothing here is a licence to read. Delete
`kit/` and `python3 tools/kit.py` puts it back identically.

They are deliberately ugly. A gradient is not a portfolio photograph; it
is a shape of a known size, which is the only thing being tested. **Every
file name carries its real pixel size**, and the generator refuses to
write one whose name disagrees with its bytes.

Nothing in here reaches the site. `kit/` is outside `content/` and
`static/`, so zola never reads it, and the deploy only ever uploads
`public/`.

```
./preview.sh          # the panel on :1111, the site beside it
```

---

## photos/ — for a project, or the gallery

| file | why it is here |
|---|---|
| `01-landscape-1800x1200.jpg` | the **first** photograph opens a project page at full width |
| `02-portrait-1200x1800.jpg` | tall, in the pairs below the opener |
| `03-square-1400x1400.jpg` | a cover for a dossier |
| `04-panorama-2400x800.jpg` | very wide — does the row still hold |
| `05-very-tall-900x2400.jpg` | CSS bounds this one by its **height** rather than cropping it |
| `06-small-400x300.jpg` | smaller than the 360px icon thumbnail asks for |
| `07-busy-1600x1000.jpg` | detail, for judging a thumbnail that has to stay legible |
| `08-SHOUTING-1500x1000.JPG` | capitals, the way a camera writes them |
| `09-transparent-1200x1200.png` | a real alpha channel through the resize pipeline |

**Try:** drop several into one project. The first becomes the icon on the
desk *and* the opener on the page. Reorder them in the panel and watch the
icon change. Write a description under each — that is the `alt` text, and
without it a screen reader is told there was nothing there.

## wallpapers/

`wallpaper-calm-2000x1125.jpg` and `wallpaper-busy-1920x1080.jpg`.

**Try:** give a bureau the busy one and see whether the folder icons and
their labels still read over it. That is the question a wallpaper has to
answer.

## about/ — the portrait in `about me.txt`

`portrait-tall-1000x1400.jpg`, `portrait-wide-1600x1000.jpg`.

**Try:** choose **about me.txt** in the left column — it has a row of its
own — drop one in, and write the text underneath. Double-click its icon in
the page to see the window as a visitor will.

## documents/ — a dossier is shown, never downloaded

`brochure-4-pages.pdf` (four pages, so the frame has something to scroll)
and `one-pager.pdf`.

**Try:** make a project of kind **un dossier PDF**, drop the brochure in,
and open its page. Nothing on the site links to the file. Then drop
`03-square-1400x1400.jpg` in the same folder: the cover becomes the icon
and the dossier stays what the click opens.

Also worth trying: put a film **and** a dossier in one project. The panel
refuses, in both directions — a project holding a video opens the film
window, which never shows a dossier.

## films/

`clip-3s.mp4`, `clip-2s.webm`, and `affiche-1600x900.jpg` for the poster.

**Try:** a project of kind **un film**, the clip in *le film* and the
affiche in *l'affiche*. The affiche is what shows before anyone presses
play, and it never appears among the project's photographs.

## wrong/ — files that are lying about what they are

These all used to be accepted, and then killed the build on
`get_image_metadata` — a site that would not compile, from a drag that
said it had worked. The panel has to refuse them, in French, and say what
the file really is.

| file | expected |
|---|---|
| `actually-a-pdf.jpg` | refused: *"c'est un PDF — et ici le site attend une image"* |
| `actually-an-iphone-photo.jpg` | refused, with the export-to-JPEG advice |
| `actually-a-photograph.mov` | refused as a film |
| `actually-a-photograph.pdf` | refused as a dossier |
| `empty.jpg` | refused: *"ce fichier est vide"* |
| `a-png-named-jpg.jpg` | **accepted** — zola reads it and builds it, so refusing would be a refusal you cannot act on |

That last row is the point of the group: the rule is not *"do the bytes
match the extension"*, it is *"can the engine use these bytes for what
this file is for"*.

---

## A whole bureau, in one sitting

1. **Nouveau ▸ un dossier** on the home desk — it gets its own page, its
   own wallpaper and a place in the top bandeau
2. give it `wallpaper-busy-1920x1080.jpg`
3. **un projet de photos** inside it, with four or five from `photos/`
4. **un dossier PDF** with `brochure-4-pages.pdf` and a cover
5. **un film** with `clip-3s.mp4` and `affiche-1600x900.jpg`
6. a portrait and some words on **about me.txt**
7. press **Annuler** a few times and watch all of it come back

Then `zola build && python3 tools/prune.py` to see what the deploy would
actually weigh.
