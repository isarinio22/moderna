# Image prompt for the LinkedIn post

Paste into ChatGPT (or any image model). Written to match the palette of the
site and figures, so the post and the repo look like one thing.

Image models are unreliable with text, so these prompts deliberately ask for
**no words in the image**. Put the words in the post instead.

---

## Main prompt (16:9, best for a link preview)

> A clean flat vector editorial illustration on a very dark charcoal background,
> hex #0F1216. Wide 16:9 format. Three equal panels divided by thin, subtle
> vertical lines.
>
> Panel one: a single large rounded cell shape in muted grey, alone in empty
> space. Protruding from its surface on short thin stalks are six small bright
> vermillion-orange geometric tags, each a slightly different simple shape:
> triangle, square, pentagon, diamond. They look like tiny flags. Nothing else
> is in the panel.
>
> Panel two: the same grey cell with the same orange tags, now surrounded by six
> smaller blue circular cells arranged in a loose ring. Thin blue lines extend
> from each blue cell toward the orange tags, suggesting inspection. One blue
> cell is slightly larger and has a soft glow.
>
> Panel three: roughly twenty blue cells converging from every direction onto
> the grey tagged cell at the centre. The grey cell is beginning to break apart
> at its edges into small fragments.
>
> Style: minimal flat vector, bold simple shapes, generous negative space, thin
> 2px strokes, no gradients except one faint glow. The look of a high-end
> science magazine diagram. Strictly limited palette: dark charcoal background,
> muted grey cells, vermillion orange #D55E00 for the tags, strong blue #0072B2
> for the immune cells, a single small accent of green #009E73.
>
> Absolutely no text, no letters, no numbers, no labels anywhere in the image.
> No blood, no gore, no realistic anatomy, no syringes, no microscopes, no
> double helix, no human figures.

---

## Square version (1:1, better for a native post)

Same as above but one panel instead of three:

> A clean flat vector editorial illustration on a very dark charcoal background,
> hex #0F1216. Square 1:1 format, centred composition.
>
> A single large rounded cell in muted grey occupies the centre. Protruding from
> its surface on short thin stalks are eight small bright vermillion-orange
> geometric tags, each a different simple shape, like tiny flags. Around the
> outer edge of the image, a ring of small blue circular cells faces inward, with
> thin blue lines extending toward the orange tags.
>
> Style: minimal flat vector, bold simple shapes, lots of negative space, thin
> 2px strokes, no gradients. High-end science magazine diagram. Palette strictly
> limited to: charcoal background, muted grey cell, vermillion orange #D55E00,
> strong blue #0072B2.
>
> No text, no letters, no numbers, no labels. No blood, no gore, no realistic
> anatomy, no syringes, no human figures.

---

## What the picture is saying

Worth knowing so you can caption it, and so you can tell whether the model got
it right:

- **The orange tags are the mutations**, already on the cancer cell's surface
  from the start. The vaccine does not put them there.
- **Panel one is the problem.** The tags are up and nobody is looking.
- **Panel two is the vaccine.** A handful of immune cells learning the shapes.
- **Panel three is the result.** The learned immune cells multiplied and found
  the cell that was wearing those tags all along.

The tags being *different shapes* matters. It is the visual for "every tumour
has a different set, and every person can display a different subset."

## If the result is bad

Models usually fail here in one of three ways:

- **It adds text anyway.** Regenerate; adding "no text" twice sometimes helps.
- **It goes medical-realistic.** Add "icon-like, abstract, not anatomical,
  not photorealistic" to the style line.
- **The three panels blur together.** Ask for it as a single panel instead and
  use the square version.
