from app.services.rag.ingest import extract_text_by_page, normalize_pages_text

pages = extract_text_by_page("/app/data/documents/Reglamento General de Modalidades de Graduacion.pdf")
pages = normalize_pages_text(pages)

for page in pages:
    print("=" * 80)
    print(f"PAGE {page['page_number']}")
    print("=" * 80)
    print(page["text"][:4000])
    print()