import fitz  # PyMuPDF


def split_and_reorganize_pdf(input_pdf, output_pdf, order=None):
    # Abre el PDF original
    doc = fitz.open(input_pdf)
    output = fitz.open()  # Crea un nuevo PDF
    split_pages = []  # Lista para almacenar las páginas recortadas

    # Recorre todas las páginas del documento y divide en tres partes verticales
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        rect = page.rect
        width = rect.width / 3

        # Agrega las tres partes recortadas a la lista
        split_pages.extend([(page_num, fitz.Rect(
            i * width, 0, (i + 1) * width, rect.height)) for i in range(3)])

    # Si no se proporciona un orden, usar el orden original
    if order is None:
        order = list(range(len(split_pages)))

    # Guardar las páginas reorganizadas en el archivo de salida
    for i in order:
        page_num, sub_rect = split_pages[i]
        page = doc.load_page(page_num)
        new_page = output.new_page(
            width=sub_rect.width, height=sub_rect.height)
        new_page.show_pdf_page(new_page.rect, doc, page_num, clip=sub_rect)

    output.save(output_pdf)
    output.close()


# Ejecutar la función
input_pdf = "test.pdf"  # Cambia esto por tu archivo de entrada
output_pdf = "output_split_vertical.pdf"  # Archivo de salida

order = [2, 3, 4, 5, 0, 1]

# Dividir y reorganizar
split_and_reorganize_pdf(input_pdf, output_pdf, order)
