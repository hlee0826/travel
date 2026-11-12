from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


OUT_DIR = Path("deliverables")
OUT_DIR.mkdir(exist_ok=True)
OUT_PATH = OUT_DIR / "Their_Little_World_Website_Improvement_Plan.docx"

INK = "302E29"
MUTED = "686052"
ACCENT = "A6372B"
PALE = "F7F3E9"
PALE_ALT = "EEE8DA"
WHITE = "FFFFFF"
LINE = "D9D9D9"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=110, start=110, bottom=110, end=110):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color=LINE, size="6"):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = borders.find(qn(f"w:{edge}"))
        if tag is None:
            tag = OxmlElement(f"w:{edge}")
            borders.append(tag)
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), size)
        tag.set(qn("w:space"), "0")
        tag.set(qn("w:color"), color)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    cant_split.set(qn("w:val"), "true")
    tr_pr.append(cant_split)


def remove_paragraph_borders(paragraph):
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is not None:
        p_pr.remove(p_bdr)


def set_run_font(run, name="Aptos", size=None, bold=None, color=None, italic=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


def add_heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(18 if level == 1 else 12)
    p.paragraph_format.space_after = Pt(6)
    for run in p.runs:
        set_run_font(run, "Aptos Display", 17 if level == 1 else 13, bold=True, color="000000")
    return p


def add_body(doc, text="", *, bold_lead=None, italic=False, after=7, keep=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.12
    p.paragraph_format.keep_with_next = keep
    if bold_lead and text.startswith(bold_lead):
        lead = p.add_run(bold_lead)
        set_run_font(lead, size=10.5, bold=True, color=INK)
        rest = p.add_run(text[len(bold_lead):])
        set_run_font(rest, size=10.5, color=INK, italic=italic)
    else:
        run = p.add_run(text)
        set_run_font(run, size=10.5, color=INK, italic=italic)
    return p


def add_bullets(doc, items, level=0):
    for item in items:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.left_indent = Inches(0.24 + 0.22 * level)
        p.paragraph_format.first_line_indent = Inches(-0.16)
        p.paragraph_format.line_spacing = 1.08
        set_run_font(p.add_run("• "), size=10.25, color=INK)
        set_run_font(p.add_run(item), size=10.25, color=INK)


def add_numbered(doc, items):
    for number, item in enumerate(items, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.first_line_indent = Inches(-0.2)
        set_run_font(p.add_run(f"{number}. "), size=10.25, color=INK)
        set_run_font(p.add_run(item), size=10.25, color=INK)


def make_table(doc, headers, rows, widths, font_size=9.2):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for grid_col, width in zip(table._tbl.tblGrid.gridCol_lst, widths):
        grid_col.set(qn("w:w"), str(int(width * 1440)))
    set_table_borders(table)
    header = table.rows[0]
    set_repeat_table_header(header)
    prevent_row_split(header)
    for i, (label, width) in enumerate(zip(headers, widths)):
        cell = header.cells[i]
        cell.width = Inches(width)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_shading(cell, INK)
        set_cell_margins(cell, 120, 110, 120, 110)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(label)
        set_run_font(run, size=font_size, bold=True, color=WHITE)
    for r_idx, row in enumerate(rows):
        cells = table.add_row().cells
        prevent_row_split(table.rows[-1])
        fill = WHITE if r_idx % 2 == 0 else PALE
        for i, (value, width) in enumerate(zip(row, widths)):
            cell = cells[i]
            cell.width = Inches(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_shading(cell, fill)
            set_cell_margins(cell, 110, 110, 110, 110)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.04
            run = p.add_run(str(value))
            set_run_font(run, size=font_size, color=INK)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


doc = Document()
section = doc.sections[0]
section.page_width = Inches(8.5)
section.page_height = Inches(11)
section.top_margin = Inches(0.68)
section.bottom_margin = Inches(0.65)
section.left_margin = Inches(0.72)
section.right_margin = Inches(0.72)

normal = doc.styles["Normal"]
normal.font.name = "Aptos"
normal._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
normal.font.size = Pt(10.5)
normal.font.color.rgb = RGBColor.from_string(INK)

for style_name in ("Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3"):
    style = doc.styles[style_name]
    style.font.color.rgb = RGBColor(0, 0, 0)

title_style_ppr = doc.styles["Title"].element.get_or_add_pPr()
title_style_border = title_style_ppr.find(qn("w:pBdr"))
if title_style_border is not None:
    title_style_ppr.remove(title_style_border)

title = doc.add_paragraph(style="Title")
title.paragraph_format.space_after = Pt(6)
set_run_font(title.add_run("Website Improvement Recommendations and Task Plan"), "Aptos Display", 27, bold=True, color="000000")
remove_paragraph_borders(title)

subtitle = doc.add_paragraph()
subtitle.paragraph_format.space_after = Pt(4)
set_run_font(subtitle.add_run("Their Little World Minhwa Pet Portrait Studio"), "Aptos Display", 14, color=ACCENT)

meta = doc.add_paragraph()
meta.paragraph_format.space_after = Pt(18)
set_run_font(meta.add_run("Prepared for joint review  |  7 November 2026  |  Live site and creation flow"), size=9.2, color=MUTED)

add_body(
    doc,
    "The site should keep the portrait as the central decision and postpone the final product choice until the artwork has been approved. The current format cards are useful for explaining the available products, but their links create an invisible preselection and send every visitor to an upload page that looks the same. The strongest revision is to make the cards educational, keep one consistent portrait-creation flow, and remember any product interest only as a changeable preference.",
    after=10,
)

add_heading(doc, "Recommended direction", 1)
summary_rows = [
    ("P0", "Simplify the format-card routes", "Keep the cards as product education. Let each card reveal details or move to a comparison section, then use one clear Create your portrait action."),
    ("P0", "Align the photo requirements", "The live site requests one photo, while the portrait workflow requires face, full-body, and side or three-quarter references. The interface and production process need one shared requirement."),
    ("P0", "Remove the flower-and-bird Hanja label", "It identifies a flower-and-bird category that is narrower than the full portrait system. Removing it avoids a misleading cultural signal."),
    ("P1", "Expand to four coherent portrait worlds", "Add Guardian Pine and Plum Blossom to the existing Peony and Lotus choices. Each world should have one wish, one anchor, one support, and one movement motif."),
    ("P1", "Add visual proof and photo guidance", "Use before-and-after pairs to demonstrate likeness. Show clear use and avoid examples before customers upload, with a fuller guide below the form."),
]
make_table(doc, ["Priority", "Decision", "Reason"], summary_rows, [0.65, 2.0, 4.15], font_size=9.3)

add_heading(doc, "Purchase format flow", 1)
add_body(doc, "Finding. The Digital keepsake, Art print, and Framed art print cards all open the portrait creation page. The product preference is carried in the URL and can be used later, but the upload page does not acknowledge the choice. Customers therefore see three apparently different actions that produce the same immediate result.", bold_lead="Finding. ")
add_body(doc, "Recommendation. Keep the product choice after artwork approval. Change the three cards from purchase routes into comparison and education routes. A visitor can still enter the purchase journey from several places, but each route should have a distinct purpose.", bold_lead="Recommendation. ")

add_numbered(doc, [
    "Use the hero, navigation, process section, garden cards, and closing section as routes into one Create your portrait flow.",
    "Use the three format cards to explain what is included, available sizes, starting prices, and who each option suits.",
    "Let the card action expand details in place or jump to the existing product configurator. Avoid a modal.",
    "If a customer selects a format in the configurator, remember it as a soft preference and show: Interested in an art print. You can change this after approving your portrait.",
    "After portrait approval, return to the remembered option while keeping all three choices visible.",
])

add_heading(doc, "Suggested format copy", 2)
format_rows = [
    ("Section introduction", "One portrait, three ways to keep it close.", "Every commission begins with the artwork. After you approve the portrait, choose a digital file, art print, or framed print."),
    ("Digital card", "Digital keepsake", "High-resolution PNG and JPEG files for your screen or your own printer. Action: See what is included."),
    ("Print card", "Art print", "A museum-style paper print, ready for a frame you already love. Action: See print sizes."),
    ("Framed card", "Framed art print", "A finished piece with a natural frame, ready to display. Action: See frame options."),
    ("Shared action", "Create your portrait", "Use the same action after each expanded detail area and in the existing high-intent sections."),
]
make_table(doc, ["Location", "Heading or label", "Supporting copy"], format_rows, [1.25, 1.65, 3.9], font_size=9.15)

add_heading(doc, "Alternative if the existing links remain", 2)
add_body(doc, "If the three cards continue to link directly to upload, make the destination visibly contextual. Change the page heading to Create your digital keepsake, Create your art print, or Create your framed print, and add a short line that the choice is not final until the portrait is approved. Without that acknowledgement, the deep links should be removed.")

doc.add_page_break()
add_heading(doc, "Four portrait worlds", 1)
add_body(doc, "The website currently treats Peony and Lotus as background choices. The collection will be easier to expand if each choice is defined as a complete portrait world: a customer-facing wish, one anchor motif, one supporting element, one movement element, a palette, and a restraint rule. Meanings should be described as associations that depend on context and pairing, not as fixed translations.")

garden_rows = [
    ("Peonies and butterflies", "Prosperity, celebration, affection", "One peony branch; low ornamental rock; two butterflies", "Warm hanji, jade, peony red, mineral blue", "One main bloom cluster; flowers remain below the pet in detail and contrast"),
    ("Lotus garden", "Peace, healing, calm reflection", "Broad lotus leaves; one flower and seedpod; faint water bands; one pale butterfly", "Pale hanji, celadon, jade, lotus blush", "Keep the field quiet; no photorealistic pond"),
    ("Guardian pine", "Long life, steadfastness, protection, good news", "Gnarled pine; weathered rock; one magpie or sparse cloud", "Hanji ochre, deep pine, bark umber, mineral blue", "The pet carries the guardian role; bird stays small and high"),
    ("Plum blossom garden", "Renewal, resilience, new beginnings", "Dark angular branch; sparse blossoms; rock; low water band or one butterfly", "Shell white, blush, warm ink, muted green", "Preserve bare branch and open paper; do not fill every twig"),
]
make_table(doc, ["World", "Customer wish", "Motif recipe", "Palette", "Restraint"], garden_rows, [1.25, 1.35, 1.75, 1.2, 1.45], font_size=8.45)

add_heading(doc, "Why these two additions", 2)
add_bullets(doc, [
    "Guardian Pine adds a darker evergreen silhouette and a protective, enduring message. It is visually distinct from both flower gardens.",
    "Plum Blossom adds a sparse winter-to-spring composition with visible branch structure and more quiet paper. It broadens both season and mood.",
    "Together, the four choices cover abundance, calm, steadfastness, and renewal without mixing unrelated symbols.",
    "A reduced chaekgeori composition for Wisdom and Curiosity can become a later interior collection. It should not be forced into the garden category.",
])

add_heading(doc, "Collection presentation", 2)
add_body(doc, "Replace Two gardens. Their own story. with Choose their little world. Once all four are ready, use the supporting sentence: Each composition is built from a small, meaningful set of minhwa motifs. Your pet remains the focus.")
add_body(doc, "Each card should show the world name, the wish in one short phrase, a one-sentence motif description, and one reference portrait. The website should not let customers assemble individual motifs freely. The studio should curate the supporting elements so the composition stays coherent and the pet remains recognizable.")

doc.add_page_break()
add_heading(doc, "Remove the flower-and-bird Hanja label", 1)
add_body(doc, "Remove the red flower-and-bird Hanja characters from the garden section and leave the space open. Flower-and-bird painting is only one category within minhwa, while the product system also includes pine, rock, water, books, clouds, and other symbolic structures. A broad label would add little value, and another decorative Korean term could create the same problem later.")
add_body(doc, "Development note. Remove the garden-mark element from the homepage template, then remove its CSS rule if it is not used elsewhere. Check desktop and mobile spacing after removal so the section heading still balances the image grid.")

add_heading(doc, "Before and after examples", 1)
add_body(doc, "A before-and-after section would do more than add decoration. It would answer the customer’s largest question: Will the portrait still look like my pet? Place the section after How it works and before the configurator, where it can provide proof before the visitor chooses a garden or uploads a photo.")
add_body(doc, "Recommended first version. Use three static paired examples rather than a comparison slider. A side-by-side layout is easier to scan, works with keyboard and screen readers, avoids hiding part of either image, and is simpler on mobile. A slider can be tested later as an enhancement.")

add_bullets(doc, [
    "Show the original reference photo and final portrait at equal visual weight.",
    "Use labels that state Original photo and Finished portrait.",
    "Add the pet name, selected portrait world, and one short likeness note, such as Kept the wide ear angle, cream muzzle, and uneven chest marking.",
    "Choose examples with visibly different species, coat types, and markings. Do not use three similar pets.",
    "Obtain written permission for every customer photo and clarify whether the pet name may be shown.",
    "Use uncropped source images when the crop contains recognition information. Keep the final 4:5 artwork uncropped.",
])

add_heading(doc, "Suggested section copy", 2)
add_body(doc, "Heading: From their photo to their little world.")
add_body(doc, "Body: We protect the features that make them recognizable: face shape, ear position, markings, body proportions, and expression.")
add_body(doc, "Action: Create your pet’s portrait.")

add_heading(doc, "Photo upload guidance", 1)
add_body(doc, "The live upload page currently asks for one photo and gives a short text description. The portrait workflow requires a clear face view, a full-body or seated view, and a side or three-quarter view. Align the deployed interface with that requirement before designing the guide. The clearest customer experience is three labeled upload roles, with visual examples beside each one.")

photo_rows = [
    ("Face reference", "Eye-level, sharp eyes, visible ears and muzzle, natural light", "Filters, sunglasses or hands over the face, strong shadow, motion blur"),
    ("Full-body reference", "Ears to paws, tail visible, natural standing or seated posture", "Cropped paws or tail, heavy blanket or costume, extreme wide-angle distortion"),
    ("Side or three-quarter reference", "Shows muzzle length, ear carriage, coat direction, and body proportions", "Back view only, low resolution, conflicting age or grooming state without a note"),
    ("All references", "Same pet, current age and grooming, original high-resolution files", "Screenshots, social-media downloads, multiple pets with no clear subject, inconsistent markings"),
]
make_table(doc, ["Photo role", "Use", "Avoid"], photo_rows, [1.35, 2.7, 2.7], font_size=9.1)

add_heading(doc, "Recommended placement", 2)
add_bullets(doc, [
    "Above or beside each upload control, show one good example with a short reason. Customers need the guidance before choosing a file.",
    "Below the form, add a fuller Photos that help us recognize them section with paired Use and Avoid examples.",
    "After file selection, validate resolution and basic file quality, then give specific feedback such as This photo is too small or The face is hard to see.",
    "On mobile, stack the guide in the same order as the upload fields. Do not hide essential requirements in an accordion.",
])

add_heading(doc, "Implementation task plan", 1)
add_body(doc, "Suggested owner describes the type of work and can be replaced with a name. P0 items should be resolved before new visual content is added. P1 items build the planned customer experience. P2 items improve proof and polish after the core flow is stable.")

task_rows = [
    ("UX 01", "P0", "Joint", "Confirm that product format is chosen after artwork approval and that homepage cards are informational.", "One written flow decision covers cards, configurator, upload, approval, and product selection."),
    ("UX 02", "P0", "Web", "Change format card links to expand details or jump to the product configurator.", "Each card action has a distinct result; no three actions open an indistinguishable page."),
    ("UX 03", "P1", "Web", "Preserve a configurator choice as a changeable soft preference.", "Upload page acknowledges the interest; product page reopens that option and shows all alternatives."),
    ("COPY 01", "P1", "Studio", "Replace the format-section copy and card actions.", "Copy explains when the final product is chosen and does not imply an early commitment."),
    ("CULT 01", "P0", "Web", "Remove the flower-and-bird Hanja element and unused style rule.", "Characters are absent on desktop and mobile; heading and grid spacing remain balanced."),
    ("PHOTO 01", "P0", "Joint", "Align live upload requirements with the intake and production workflow.", "Face, full-body, and side or three-quarter roles are documented consistently in UI and production records."),
    ("PHOTO 02", "P1", "Studio", "Select or create approved Use and Avoid photo examples.", "Every example demonstrates one clear lesson and contains no unapproved customer content."),
    ("PHOTO 03", "P1", "Web", "Build the inline upload examples and the full guide below the form.", "Guide is readable before upload, responsive, keyboard accessible, and not hidden in an accordion."),
    ("PHOTO 04", "P1", "Web", "Add file-quality feedback for size, resolution, and unreadable images.", "Errors identify the specific photo and explain how to replace it."),
    ("GARDEN 01", "P0", "Studio", "Complete an artwork brief for each of the four portrait worlds.", "Each brief has wish, anchor, support, movement count, palette, layout, restraint, and exclusions."),
    ("GARDEN 02", "P1", "Studio", "Generate Guardian Pine identity study and final reference portrait.", "Identity gate and tradition gate pass; QA score is at least 82 out of 100."),
    ("GARDEN 03", "P1", "Studio", "Generate Plum Blossom identity study and final reference portrait.", "Identity gate and tradition gate pass; QA score is at least 82 out of 100."),
    ("GARDEN 04", "P1", "Studio", "Review Peony and Lotus against the same motif recipes and QA standard.", "All four samples use comparable pet scale, quiet space, material treatment, and motif hierarchy."),
    ("GARDEN 05", "P1", "Web", "Update the collection data, selector, homepage grid, and configurator from two to four choices.", "All routes preserve the selected world and every card has correct copy and alt text."),
    ("PROOF 01", "P1", "Joint", "Choose three representative before-and-after cases and secure display permission.", "Consent, pet-name preference, source photo, final art, and likeness notes are recorded for each case."),
    ("PROOF 02", "P2", "Design", "Design the responsive paired-example section.", "Desktop shows equal pairs; mobile preserves labels and full artwork without relying on hover or drag."),
    ("PROOF 03", "P2", "Web", "Build and place the section after How it works.", "Images lazy-load, dimensions are reserved to prevent layout shift, and captions remain readable."),
    ("QA 01", "P0", "Web", "Reconcile the live deployment with the current local source.", "Live and local versions use the same photo count, copy, collection list, and route behavior."),
    ("QA 02", "P1", "Joint", "Run end-to-end mobile and desktop tests.", "Every homepage route reaches the intended step; back navigation and saved preferences behave predictably."),
    ("QA 03", "P2", "Joint", "Run accessibility, content, and cultural review.", "Keyboard use, focus, labels, contrast, reduced motion, alt text, motif descriptions, and Korean terms pass review."),
]
make_table(doc, ["ID", "Pri", "Owner", "Task", "Done when"], task_rows, [0.62, 0.42, 0.72, 2.45, 2.55], font_size=8.25)

add_heading(doc, "Recommended order of work", 1)
add_numbered(doc, [
    "Resolve the purchase-flow decision, remove the flower-and-bird Hanja label, and reconcile the deployed upload requirements with the project workflow.",
    "Write and approve the four portrait-world briefs before generating new art. This prevents the reference images from becoming unrelated decorative variations.",
    "Generate and QA Guardian Pine and Plum Blossom, then review Peony and Lotus against the same standard.",
    "Update the selector and collection section, then add the visual upload guide.",
    "Add before-and-after proof once three approved cases and permissions are ready.",
    "Finish with end-to-end, accessibility, performance, and cultural review on the live deployment.",
])

add_heading(doc, "Decisions to make together", 1)
add_bullets(doc, [
    "Whether the homepage format cards should expand in place or jump to the existing configurator.",
    "Whether a product interest should be remembered automatically or only after the customer uses the configurator.",
    "Which pet and coat types will represent the four portrait-world reference images.",
    "Which three before-and-after cases have permission and show the strongest likeness proof.",
    "Whether the third side or three-quarter reference is required or strongly recommended in the customer interface. The production record should still collect it before final artwork begins.",
])

# Add simple page-number footers without a decorative rule.
for sec in doc.sections:
    footer = sec.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.space_before = Pt(4)
    r = p.add_run("Page ")
    set_run_font(r, size=8, color=MUTED)
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = "PAGE"
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    r._r.append(fld_char1)
    r._r.append(instr_text)
    r._r.append(fld_char2)

doc.core_properties.title = "Website Improvement Recommendations and Task Plan"
doc.core_properties.subject = "Their Little World website review and implementation backlog"
doc.core_properties.author = "Their Little World"
doc.core_properties.keywords = "minhwa, pet portrait, website, UX, task plan"

doc.save(OUT_PATH)
print(OUT_PATH.resolve())
