# Report template execution contract

Reference: C:/Users/Андрей/Downloads/Корнева Д.С. лаб1.docx
SHA256: 7D6BA07D8876F9C1759C862A66C29A9D78590165EA866526F61C8944B9B9E16D
Reference render: reference.pdf and reference-page-01 through 16.png. All 16 pages inspected.
One portrait A4 section: 11907 by 16840 twips; margins left 1361 right 567 top and bottom 1134. Header 720 footer 260. Different first page; PAGE footer, no page number on title page.

Typography: Times New Roman 14pt black. Cover centered single-spaced, metadata tab-separated signature blocks. Main headings centered bold 14pt with keepNext and keepLines. Body justified 1.5 line spacing, 708 twip first-line indent and 120 twip after. Bullets reuse source numId 1, 720 left and 360 hanging indents, 1.5 line spacing. Subheadings justified bold. Captions centered 14pt single spaced. Figures centered inline, aspect ratio retained.

Structure: cover, contents, goals, tasks, prototype with actual screen figures, conclusion. Reuse source patterns; allow cloned body, heading, bullet, caption and inline drawing nodes. Add page breaks at chapter and figure boundaries as in reference. Six figures: authentication pair, home, details, chats pair, profile, publication pair. Replace Meetly content completely with dorm marketplace description. No onboarding, voting, map, administrator or complaints.

Editable slots: word/document.xml body paragraphs; cover p20 subject, p28 student group and name, p32 reviewer placeholder; original p46/56/117/158 chapter headings; p47/159 body pattern; p48 bullet pattern; p57 subheading pattern; p121 caption pattern; inline drawing pattern. All source content after cover is replaced with report-specific clones. TOC replaced with native field and headings supplied with outline levels and bookmarks. Word refreshes TOC and page fields.

Known facts: Figma prototype exists; four transfer values work; mobile client planned in React Native; shared server database is planned, not deployed. Screens are real screenshots of existing prototype. Unknown student full name/group and reviewer left as blanks. University, course, department, city and year retained from sample.

Preservation: all original ZIP parts retained byte-for-byte except document.xml and its relationships; metadata author cleared through core.xml patch. Existing media retained; new cropped screenshots added as PNG parts. Existing styles, numbering, theme, fonts, footer, settings and customXML remain untouched. Source relationship entries retained and new image relationships appended. No external uploads, no source modifications.

Fidelity gates: same section geometry and footer; same source-derived font and spacing patterns; actual screenshots readable; captions sequential and referenced correctly; every final page inspected. Bundled LibreOffice unavailable on Windows: render_docx.py failed at missing soffice.exe. Fallback uses installed Microsoft Word PDF export and bundled Poppler PNG rendering.
